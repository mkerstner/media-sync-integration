"""The Media Sync integration."""

from datetime import datetime, timedelta

from homeassistant.components.hassio import SupervisorError
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import (
    ConfigEntryError,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .addon import async_discover_slug, get_addon_manager
from .client import MediaSyncClient
from .const import (
    CONF_ADDON_SLUG,
    CONF_CHECK_DIRECTION,
    CONF_CHECK_INTERVAL,
    DEFAULT_CHECK_DIRECTION,
    DEFAULT_CHECK_INTERVAL,
    DIRECTION_ARGS,
    DOMAIN,
    LOGGER,
)
from .coordinator import MediaSyncConfigEntry, MediaSyncCoordinator
from .services import async_setup_services

PLATFORMS = [Platform.BUTTON, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Media Sync integration."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MediaSyncConfigEntry) -> bool:
    """Set up Media Sync from a config entry."""
    try:
        slug = await async_discover_slug(hass)
    except SupervisorError as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="addon_info_failed",
            translation_placeholders={"error": str(err)},
        ) from err

    if slug is None:
        raise ConfigEntryError(
            translation_domain=DOMAIN, translation_key="addon_not_installed"
        )

    # The slug changes if the app is reinstalled from a different repository.
    if slug != entry.data.get(CONF_ADDON_SLUG):
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_ADDON_SLUG: slug}
        )

    coordinator = MediaSyncCoordinator(
        hass, entry, MediaSyncClient(hass), get_addon_manager(hass, slug)
    )
    entry.runtime_data = coordinator
    await coordinator.async_config_entry_first_refresh()

    _async_schedule_checks(hass, entry, coordinator)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MediaSyncConfigEntry) -> bool:
    """Unload a Media Sync config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


@callback
def _async_schedule_checks(
    hass: HomeAssistant,
    entry: MediaSyncConfigEntry,
    coordinator: MediaSyncCoordinator,
) -> None:
    """Run a check on a fixed interval, when one is configured."""
    minutes = entry.options.get(CONF_CHECK_INTERVAL, DEFAULT_CHECK_INTERVAL)
    if not minutes:
        coordinator.next_check = None
        return

    direction = entry.options.get(CONF_CHECK_DIRECTION, DEFAULT_CHECK_DIRECTION)
    interval = timedelta(minutes=minutes)

    async def _run_scheduled_check(now: datetime) -> None:
        """Start a check, unless one is already under way."""
        coordinator.next_check = dt_util.utcnow() + interval
        try:
            await coordinator.async_start_sync(
                *DIRECTION_ARGS[direction], requested_by="the schedule"
            )
        except HomeAssistantError as err:
            # A scheduled run is nobody's service call, so it must never raise.
            LOGGER.debug("Skipped the scheduled check: %s", err)

    coordinator.next_check = dt_util.utcnow() + interval
    entry.async_on_unload(
        async_track_time_interval(hass, _run_scheduled_check, interval)
    )


async def _async_options_updated(
    hass: HomeAssistant, entry: MediaSyncConfigEntry
) -> None:
    """Reload so a changed interval takes effect."""
    await hass.config_entries.async_reload(entry.entry_id)
