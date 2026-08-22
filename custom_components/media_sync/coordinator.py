"""Coordinator for the Media Sync integration."""

from dataclasses import replace
from datetime import datetime
from typing import override

from homeassistant.components.hassio import AddonError, AddonManager, AddonState
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import (
    STATUS_FAILED,
    STATUS_RUNNING,
    MediaSyncClient,
    MediaSyncError,
    SyncState,
)
from .const import (
    DOMAIN,
    LOGGER,
    UPDATE_INTERVAL_IDLE,
    UPDATE_INTERVAL_RUNNING,
)
from .log import async_log, async_log_run_requested
from .repairs import async_manage_pending_deletions_issue

type MediaSyncConfigEntry = ConfigEntry[MediaSyncCoordinator]


class MediaSyncCoordinator(DataUpdateCoordinator[SyncState]):
    """Track what the app recorded, and ask it to run again."""

    config_entry: MediaSyncConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: MediaSyncConfigEntry,
        client: MediaSyncClient,
        addon_manager: AddonManager,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=LOGGER,
            config_entry=config_entry,
            name=config_entry.title,
            update_interval=UPDATE_INTERVAL_IDLE,
        )
        self.client = client
        self.addon_manager = addon_manager
        self.next_check: datetime | None = None

    @override
    async def _async_update_data(self) -> SyncState:
        """Combine the recorded result with whether the app is running."""
        try:
            addon_info = await self.addon_manager.async_get_addon_info()
        except AddonError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="addon_info_failed",
                translation_placeholders={"error": str(err)},
            ) from err

        try:
            state = await self.client.async_get_state()
        except MediaSyncError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="state_read_error",
                translation_placeholders={"error": str(err)},
            ) from err

        running = addon_info.state is AddonState.RUNNING
        if running:
            state = replace(state, status=STATUS_RUNNING)
        elif state.running:
            # The container is gone but no result was recorded, so it was killed
            # before its own cleanup could run.
            state = replace(state, status=STATUS_FAILED)

        self.update_interval = (
            UPDATE_INTERVAL_RUNNING if running else UPDATE_INTERVAL_IDLE
        )
        async_manage_pending_deletions_issue(self.hass, self.config_entry, state)
        return state

    async def async_start_sync(
        self,
        *args: str,
        context: Context | None = None,
        requested_by: str | None = None,
    ) -> None:
        """Queue the arguments for the next run and start the app."""
        if self.data.running:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="already_running"
            )

        await async_log_run_requested(
            self.hass, args, context=context, requested_by=requested_by
        )

        try:
            await self.client.async_write_request(args)
        except MediaSyncError as err:
            await async_log(self.hass, "action", f"could not be queued: {err}")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="request_failed",
                translation_placeholders={"error": str(err)},
            ) from err

        try:
            await self.addon_manager.async_start_addon()
        except AddonError as err:
            await async_log(self.hass, "action", f"app would not start: {err}")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="start_failed",
                translation_placeholders={"error": str(err)},
            ) from err

        await self.async_request_refresh()
