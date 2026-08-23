"""Repairs for the Media Sync integration."""

from typing import TYPE_CHECKING, Any, cast, override

import voluptuous as vol

from homeassistant.components.repairs import RepairsFlow, RepairsFlowResult
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .client import PendingGroup, SyncState
from .const import (
    ACTION_DELETE,
    ACTION_KEEP,
    ARG_ASSUME_YES,
    CONF_KEEP,
    DOMAIN,
    ISSUE_PENDING_DELETIONS,
    MAX_LISTED_DELETIONS,
    ROOT_GROUP,
    SIDE_LOCAL,
    SIDE_REMOTE,
)

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


def _format_groups(groups: list[PendingGroup]) -> str:
    """Render reviewed folders as a markdown list."""
    if not groups:
        return "- nothing"
    listed = [
        f"- `{group.label}` — {group.folder}"
        for group in groups[:MAX_LISTED_DELETIONS]
    ]
    if len(groups) > MAX_LISTED_DELETIONS:
        listed.append(f"- … and {len(groups) - MAX_LISTED_DELETIONS} more")
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
            "count": str(state.pending_count),
            "deletions": _format_deletions(state.pending),
        },
        data={"entry_id": entry.entry_id},
    )


def _side_phrase(side: str) -> str:
    """Say where a group's files actually are."""
    if side == SIDE_LOCAL:
        return "on Home Assistant only"
    if side == SIDE_REMOTE:
        return "on the server only"
    return "on one side only"


def _group_label(group: PendingGroup) -> str:
    """Render one reviewable row."""
    folder = "files at the top level" if group.folder == ROOT_GROUP else group.folder
    files = "file" if group.count == 1 else "files"
    where = _side_phrase(group.side)
    return f"{group.label} — {folder} ({group.count} {files}, {where})"


class PendingDeletionsRepairFlow(RepairsFlow):
    """Let the user decide, folder by folder, what to keep and what to delete."""

    def __init__(self, entry: MediaSyncConfigEntry) -> None:
        """Initialize the flow."""
        self.entry = entry
        self._keep: list[PendingGroup] = []
        self._delete: list[PendingGroup] = []

    @override
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> RepairsFlowResult:
        """Handle the first step of the flow."""
        groups = self.entry.runtime_data.data.groups
        # An app older than 1.5.0 reports no groups, so there is nothing to
        # review folder by folder. Fall back to the all-or-nothing question
        # rather than showing an empty form.
        if not groups:
            return await self.async_step_confirm()
        return await self.async_step_review()

    async def async_step_review(
        self, user_input: dict[str, Any] | None = None
    ) -> RepairsFlowResult:
        """Ask which folders to keep. Everything else is up for deletion."""
        coordinator = self.entry.runtime_data
        groups = coordinator.data.groups

        if user_input is not None:
            chosen = set(user_input.get(CONF_KEEP, []))
            self._keep = [group for group in groups if group.key in chosen]
            self._delete = [group for group in groups if group.key not in chosen]
            return await self.async_step_apply()

        # Everything starts checked, so confirming without reading deletes
        # nothing. Unchecking is the deliberate act.
        return self.async_show_form(
            step_id="review",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_KEEP, default=[group.key for group in groups]
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    value=group.key, label=_group_label(group)
                                )
                                for group in groups
                            ],
                            multiple=True,
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
            description_placeholders={"count": str(coordinator.data.pending_count)},
        )

    async def async_step_apply(
        self, user_input: dict[str, Any] | None = None
    ) -> RepairsFlowResult:
        """Show what each choice costs, then carry it out."""
        if user_input is not None:
            decisions = [
                (ACTION_KEEP, group.label, group.folder) for group in self._keep
            ] + [(ACTION_DELETE, group.label, group.folder) for group in self._delete]
            await self.entry.runtime_data.async_resolve(
                decisions, requested_by="the review"
            )
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="apply",
            data_schema=vol.Schema({}),
            description_placeholders={
                "keep_count": str(sum(group.count for group in self._keep)),
                "delete_count": str(sum(group.count for group in self._delete)),
                "delete_list": _format_groups(self._delete),
            },
        )

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        """Ask the all-or-nothing question, for an app too old to group."""
        coordinator = self.entry.runtime_data
        if user_input is not None:
            await coordinator.async_start_sync(
                ARG_ASSUME_YES, requested_by="the repair notification"
            )
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "count": str(coordinator.data.pending_count),
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
