"""Read and drive the state the Media Sync app records."""

from dataclasses import dataclass, field, replace
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Final, Self

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    DECISIONS_PATH,
    LOGGER,
    MAX_EXAMPLES,
    REQUEST_PATH,
    ROOT_GROUP,
    STATE_PATH,
)

STATUS_IDLE: Final = "idle"
STATUS_RUNNING: Final = "running"
STATUS_OK: Final = "ok"
STATUS_FAILED: Final = "failed"

STATUSES: Final = [STATUS_IDLE, STATUS_RUNNING, STATUS_OK, STATUS_FAILED]


class MediaSyncError(Exception):
    """Raised when the app's state cannot be read or a run cannot be queued."""


@dataclass(frozen=True, kw_only=True)
class PendingGroup:
    """A folder holding items the last sync found on one side only.

    The app groups candidates because a run can turn up thousands of them and
    nobody reviews that one by one. Deciding on a group acts on the recorded
    candidates inside it, never on the folder as a whole.
    """

    label: str
    side: str
    folder: str
    count: int
    # A few real paths, relative to the folder above. A folder name says
    # nothing when it stands for a single file. Empty when the app predates
    # 1.6.0, in which case the integration derives them from the flat list.
    examples: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        """Return the value identifying this group in a form.

        A tab separates the two halves because the app already exchanges these
        as TSV, so neither a pair label nor a folder can contain one.
        """
        return f"{self.label}\t{self.folder}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self | None:
        """Parse one group, or return None when it is not usable."""
        label = str(data.get("label", ""))
        folder = str(data.get("folder", ""))
        if not label or not folder:
            return None
        try:
            count = int(data.get("count", 0))
        except (TypeError, ValueError):
            count = 0
        raw = data.get("examples") or []
        return cls(
            label=label,
            side=str(data.get("side", "")),
            folder=folder,
            count=count,
            examples=[str(item) for item in raw][:MAX_EXAMPLES],
        )


@dataclass(frozen=True, kw_only=True)
class SyncState:
    """Result of the most recent run of the sync script."""

    status: str
    mode: str | None = None
    direction: str | None = None
    started: datetime | None = None
    finished: datetime | None = None
    last_success: datetime | None = None
    pending: list[str]
    groups: list[PendingGroup] = field(default_factory=list)
    # The app caps the flat list it writes, so this is the only trustworthy
    # total once a run turns up more candidates than the cap.
    pending_count: int = 0
    error: str | None = None

    @property
    def running(self) -> bool:
        """Return whether a run is currently in progress."""
        return self.status == STATUS_RUNNING

    @classmethod
    def unknown(cls) -> Self:
        """Return the state used before the app has ever run."""
        return cls(status=STATUS_IDLE, pending=[])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Parse the JSON state file written by the sync script."""
        status = data.get("status") or STATUS_IDLE
        # An app older than 1.5.0 writes no groups at all. The flat list still
        # drives the count and the notification, so the integration keeps
        # working and only the folder-by-folder review is unavailable.
        raw_groups = data.get("pending_groups") or []
        groups = [
            group
            for item in raw_groups
            if isinstance(item, dict) and (group := PendingGroup.from_dict(item))
        ]
        pending = [str(item) for item in data.get("pending", [])]
        try:
            count = int(data.get("pending_count", len(pending)))
        except (TypeError, ValueError):
            count = len(pending)
        return cls(
            status=status if status in STATUSES else STATUS_IDLE,
            mode=data.get("mode") or None,
            direction=data.get("direction") or None,
            started=_parse_timestamp(data.get("started")),
            finished=_parse_timestamp(data.get("finished")),
            last_success=_parse_timestamp(data.get("last_success")),
            pending=pending,
            groups=_with_derived_examples(groups, pending),
            pending_count=count,
            error=data.get("error") or None,
        )


def _relative(folder: str, path: str) -> str | None:
    """Return path relative to folder, or None when it is not inside it."""
    if folder == ROOT_GROUP:
        return path if "/" not in path else None
    prefix = f"{folder}/"
    return path[len(prefix) :] if path.startswith(prefix) else None


def _with_derived_examples(
    groups: list[PendingGroup], pending: list[str]
) -> list[PendingGroup]:
    """Fill in examples from the flat list, for an app older than 1.6.0.

    The flat list is capped by the app, so a group beyond the cap simply keeps
    none and falls back to showing its count. Once the app supplies examples
    itself this does nothing.
    """
    if not groups or all(group.examples for group in groups):
        return groups

    by_label: dict[str, list[str]] = {}
    for entry in pending:
        label, separator, path = entry.partition(": ")
        if separator:
            by_label.setdefault(label, []).append(path)

    filled: list[PendingGroup] = []
    for group in groups:
        if group.examples:
            filled.append(group)
            continue
        found: list[str] = []
        for path in by_label.get(group.label, []):
            relative = _relative(group.folder, path)
            if relative is not None:
                found.append(relative)
                if len(found) >= MAX_EXAMPLES:
                    break
        filled.append(replace(group, examples=found))
    return filled


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse a timestamp written by the sync script."""
    if not isinstance(value, str) or not value:
        return None
    return dt_util.parse_datetime(value)


class MediaSyncClient:
    """Exchange files with the app through the shared config folder."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the client."""
        self._hass = hass
        self._state_file = Path(hass.config.path(STATE_PATH))
        self._request_file = Path(hass.config.path(REQUEST_PATH))
        self._decisions_file = Path(hass.config.path(DECISIONS_PATH))

    async def async_get_state(self) -> SyncState:
        """Return the result the app recorded for its last run."""
        return await self._hass.async_add_executor_job(self._read_state)

    def _read_state(self) -> SyncState:
        """Read and parse the state file."""
        try:
            raw = self._state_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return SyncState.unknown()
        except OSError as err:
            raise MediaSyncError(str(err)) from err

        try:
            data = json.loads(raw)
        except ValueError:
            LOGGER.debug("Ignoring malformed state file contents: %s", raw)
            return SyncState.unknown()
        return SyncState.from_dict(data)

    async def async_write_request(self, args: tuple[str, ...]) -> None:
        """Leave the arguments for the next run where the app will find them."""
        await self._hass.async_add_executor_job(self._write_request, args)

    async def async_clear_request(self) -> None:
        """Withdraw a queued request so a later run cannot pick it up."""
        await self._hass.async_add_executor_job(self._clear_request)

    async def async_write_decisions(
        self, decisions: list[tuple[str, str, str]]
    ) -> None:
        """Record keep/delete choices for the app's next resolve run."""
        await self._hass.async_add_executor_job(self._write_decisions, decisions)

    def _write_decisions(self, decisions: list[tuple[str, str, str]]) -> None:
        """Write the decisions file as the TSV the app reads."""
        lines = "".join(
            f"{action}\t{label}\t{folder}\n" for action, label, folder in decisions
        )
        try:
            self._decisions_file.parent.mkdir(parents=True, exist_ok=True)
            self._decisions_file.write_text(lines, encoding="utf-8")
        except OSError as err:
            raise MediaSyncError(str(err)) from err

    def _clear_request(self) -> None:
        """Remove the request file, ignoring one that is already gone."""
        try:
            self._request_file.unlink(missing_ok=True)
        except OSError as err:
            LOGGER.warning("Could not remove %s: %s", self._request_file, err)

    def _write_request(self, args: tuple[str, ...]) -> None:
        """Write the request file."""
        try:
            self._request_file.parent.mkdir(parents=True, exist_ok=True)
            self._request_file.write_text(
                json.dumps({"args": list(args)}), encoding="utf-8"
            )
        except OSError as err:
            raise MediaSyncError(str(err)) from err
