"""Actions for the Media Sync integration."""

from typing import cast

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.selector import ConfigEntrySelector
from homeassistant.helpers.service import async_register_admin_service

from .const import (
    ARG_ASSUME_YES,
    ARG_DRY_RUN,
    ARG_SCAN_ONLY,
    DIRECTION_ARGS,
    DIRECTION_BOTH,
    DOMAIN,
)
from .coordinator import MediaSyncConfigEntry

ATTR_CONFIG_ENTRY = "config_entry"
ATTR_DIRECTION = "direction"
ATTR_DRY_RUN = "dry_run"

SERVICE_SYNC = "sync"
SERVICE_SCAN_DELETIONS = "scan_deletions"
SERVICE_CONFIRM_DELETIONS = "confirm_deletions"
SERVICE_GET_PENDING_DELETIONS = "get_pending_deletions"

ENTRY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY): ConfigEntrySelector({"integration": DOMAIN}),
    }
)

SYNC_SCHEMA = ENTRY_SCHEMA.extend(
    {
        vol.Optional(ATTR_DIRECTION, default=DIRECTION_BOTH): vol.In(DIRECTION_ARGS),
        vol.Optional(ATTR_DRY_RUN, default=False): bool,
    }
)


def _async_get_entry(
    hass: HomeAssistant, call: ServiceCall
) -> MediaSyncConfigEntry:
    """Resolve the config entry an action was called on."""
    entry_id = call.data[ATTR_CONFIG_ENTRY]
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_found",
            translation_placeholders={"target": entry_id},
        )
    if entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_loaded",
            translation_placeholders={"target": entry.title},
        )
    return cast("MediaSyncConfigEntry", entry)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the Media Sync actions."""

    async def async_sync(call: ServiceCall) -> None:
        """Start a sync run."""
        entry = _async_get_entry(hass, call)
        args = list(DIRECTION_ARGS[call.data[ATTR_DIRECTION]])
        if call.data[ATTR_DRY_RUN]:
            args.append(ARG_DRY_RUN)
        await entry.runtime_data.async_start_sync(*args)

    async def async_scan_deletions(call: ServiceCall) -> None:
        """Look for deletion candidates without transferring anything."""
        entry = _async_get_entry(hass, call)
        await entry.runtime_data.async_start_sync(ARG_SCAN_ONLY)

    async def async_confirm_deletions(call: ServiceCall) -> None:
        """Apply the deletions the last run refused to make."""
        entry = _async_get_entry(hass, call)
        await entry.runtime_data.async_start_sync(ARG_ASSUME_YES)

    async def async_get_pending_deletions(call: ServiceCall) -> ServiceResponse:
        """Return the paths a confirmed deletion would remove."""
        entry = _async_get_entry(hass, call)
        pending = entry.runtime_data.data.pending
        return {"count": len(pending), "deletions": list(pending)}

    hass.services.async_register(DOMAIN, SERVICE_SYNC, async_sync, schema=SYNC_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_SCAN_DELETIONS, async_scan_deletions, schema=ENTRY_SCHEMA
    )
    # Deleting files is destructive and cannot be undone from Home Assistant.
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_CONFIRM_DELETIONS,
        async_confirm_deletions,
        schema=ENTRY_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PENDING_DELETIONS,
        async_get_pending_deletions,
        schema=ENTRY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
