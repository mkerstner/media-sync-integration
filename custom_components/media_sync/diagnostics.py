"""Diagnostics support for the Media Sync integration."""

from dataclasses import asdict
from typing import Any

from homeassistant.components.hassio import AddonError
from homeassistant.core import HomeAssistant

from .coordinator import MediaSyncConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MediaSyncConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    try:
        addon_info = await coordinator.addon_manager.async_get_addon_info()
    except AddonError as err:
        app: dict[str, Any] = {"error": str(err)}
    else:
        app = {
            "state": addon_info.state.value,
            "version": addon_info.version,
            "update_available": addon_info.update_available,
            "options": addon_info.options,
        }
    app["slug"] = coordinator.addon_manager.addon_slug

    return {"app": app, "state": asdict(coordinator.data)}
