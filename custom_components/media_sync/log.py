"""Shared activity log, written by both the integration and the app."""

from pathlib import Path

from homeassistant.core import Context, HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    ARG_ASSUME_YES,
    ARG_DRY_RUN,
    ARG_PULL_ONLY,
    ARG_PUSH_ONLY,
    ARG_SCAN_ONLY,
    LOG_PATH,
    LOGGER,
)


def describe_run(args: tuple[str, ...]) -> str:
    """Describe a run in the same words the user sees in the interface."""
    if ARG_SCAN_ONLY in args:
        what = "deletion scan"
    elif ARG_DRY_RUN in args:
        what = "dry run"
    elif ARG_ASSUME_YES in args:
        what = "sync with deletions confirmed"
    else:
        what = "sync"

    if ARG_PULL_ONLY in args:
        return f"{what} (remote server to Home Assistant)"
    if ARG_PUSH_ONLY in args:
        return f"{what} (Home Assistant to remote server)"
    return f"{what} (both directions)"


async def async_describe_context(
    hass: HomeAssistant, context: Context | None
) -> str | None:
    """Name whoever is behind a call, as far as the context reveals it."""
    if context is None:
        return None
    if context.user_id and (user := await hass.auth.async_get_user(context.user_id)):
        return user.name or user.id
    if context.parent_id:
        return "an automation or script"
    return None


async def async_log(hass: HomeAssistant, category: str, message: str) -> None:
    """Append one line to the shared log."""
    line = (
        f"{dt_util.now().strftime('%Y-%m-%d %H:%M:%S')}  {category:<7} {message}"
    )
    await hass.async_add_executor_job(_append, Path(hass.config.path(LOG_PATH)), line)


async def async_log_run_requested(
    hass: HomeAssistant,
    args: tuple[str, ...],
    *,
    context: Context | None = None,
    requested_by: str | None = None,
) -> None:
    """Record that a run was asked for, and by whom."""
    message = describe_run(args)
    if who := requested_by or await async_describe_context(hass, context):
        message = f"{message} requested by {who}"
    await async_log(hass, "action", message)


def _append(path: Path, line: str) -> None:
    """Append a line, never letting a logging problem break the action."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(f"{line}\n")
    except OSError as err:
        LOGGER.warning("Could not write to %s: %s", path, err)
