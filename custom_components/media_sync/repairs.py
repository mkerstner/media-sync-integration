"""Repairs for the Media Sync integration."""

from typing import TYPE_CHECKING, cast, override

import voluptuous as vol

from homeassistant.components.repairs import RepairsFlow, RepairsFlowResult
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .client import SyncState
from .const import ARG_ASSUME_YES, DOMAIN, ISSUE_PENDING_DELETIONS, MAX_LISTED_DELETIONS

if TYPE_CHECKING:
    from .coordinator import MediaSyncConfigEntry


def _issue_id(entry: ConfigEntry) -> str:
    """Return the issue id used for an entry's pending deletions."""
    return f"{ISSUE_PENDING_DELETIONS}_{entry.entry_id}"


def _format_deletions(pending: list[str]) -> str:
    """Render the pending deletions as a markdown list."""
    listed = [f"- `{path}`" for path in pending[:MAX_LISTED_DELETIONS]]
    if len(pending) > MAX_LISTED_DELETIONS:
        listed.append(f"- … and {len(pending) - MAX_LISTED_DELETIONS} more")
    return "\n".join(listed)


def async_manage_pending_deletions_issue(
    hass: HomeAssistant, entry: ConfigEntry, state: SyncState
) -> None:
    """Raise or clear the repair issue that confirms pending deletions."""
    if not state.pending:
        ir.async_delete_issue(hass, DOMAIN, _issue_id(entry))
        return

    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id(entry),
        is_fixable=True,
        issue_domain=DOMAIN,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_PENDING_DELETIONS,
        translation_placeholders={
            "title": entry.title,
            "count": str(len(state.pending)),
            "deletions": _format_deletions(state.pending),
        },
        data={"entry_id": entry.entry_id},
    )


class PendingDeletionsRepairFlow(RepairsFlow):
    """Let the user confirm the deletions the last sync refused to apply."""

    def __init__(self, entry: MediaSyncConfigEntry) -> None:
        """Initialize the flow."""
        self.entry = entry

    @override
    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        """Handle the first step of the flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        """Ask for confirmation and apply the deletions when given."""
        coordinator = self.entry.runtime_data
        if user_input is not None:
            await coordinator.async_start_sync(ARG_ASSUME_YES)
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "count": str(len(coordinator.data.pending)),
                "deletions": _format_deletions(coordinator.data.pending),
            },
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create a flow to fix a Media Sync issue."""
    assert data is not None
    entry = hass.config_entries.async_get_entry(str(data["entry_id"]))
    assert entry is not None
    return PendingDeletionsRepairFlow(cast("MediaSyncConfigEntry", entry))
