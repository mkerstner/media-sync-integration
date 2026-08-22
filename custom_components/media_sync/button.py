"""Buttons for the Media Sync integration."""

from dataclasses import dataclass
from typing import override

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ARG_DRY_RUN, ARG_SCAN_ONLY
from .coordinator import MediaSyncConfigEntry
from .entity import MediaSyncEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class MediaSyncButtonEntityDescription(ButtonEntityDescription):
    """Describes a Media Sync button entity."""

    args: tuple[str, ...] = ()


BUTTONS: tuple[MediaSyncButtonEntityDescription, ...] = (
    MediaSyncButtonEntityDescription(
        key="sync_now",
        translation_key="sync_now",
    ),
    MediaSyncButtonEntityDescription(
        key="dry_run",
        translation_key="dry_run",
        entity_category=EntityCategory.DIAGNOSTIC,
        args=(ARG_DRY_RUN,),
    ),
    MediaSyncButtonEntityDescription(
        key="scan_deletions",
        translation_key="scan_deletions",
        entity_category=EntityCategory.DIAGNOSTIC,
        args=(ARG_SCAN_ONLY,),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MediaSyncConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Media Sync buttons."""
    async_add_entities(
        MediaSyncButton(entry.runtime_data, description)
        for description in BUTTONS
    )


class MediaSyncButton(MediaSyncEntity, ButtonEntity):
    """Starts a run of the sync script."""

    entity_description: MediaSyncButtonEntityDescription

    @property
    @override
    def available(self) -> bool:
        """Only offer the button when a run could actually start."""
        return super().available and not self.coordinator.data.running

    @override
    async def async_press(self) -> None:
        """Press the button."""
        # The entity platform sets the calling context before this runs, which
        # is what lets the activity log name who pressed the button.
        await self.coordinator.async_start_sync(
            *self.entity_description.args, context=self._context
        )
