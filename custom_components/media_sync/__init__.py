"""The Media Sync integration."""

from homeassistant.components.hassio import SupervisorError
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .addon import async_discover_slug, get_addon_manager
from .client import MediaSyncClient
from .const import CONF_ADDON_SLUG, DOMAIN
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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MediaSyncConfigEntry) -> bool:
    """Unload a Media Sync config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
