"""Find and manage the Media Sync app."""

from collections.abc import Iterable

from homeassistant.components.hassio import AddonManager, get_supervisor_client
from homeassistant.core import HomeAssistant, callback
from homeassistant.util.hass_dict import HassKey

from .const import ADDON_NAME, ADDON_SLUG_SUFFIX, DOMAIN, LOGGER

DATA_ADDON_MANAGERS: HassKey[dict[str, AddonManager]] = HassKey(
    f"{DOMAIN}_addon_managers"
)


def _match_slug(slugs: Iterable[str]) -> str | None:
    """Return the first slug that belongs to this app."""
    return next(
        (
            slug
            for slug in slugs
            if slug == ADDON_SLUG_SUFFIX or slug.endswith(f"_{ADDON_SLUG_SUFFIX}")
        ),
        None,
    )


async def async_discover_slug(hass: HomeAssistant) -> str | None:
    """Return the slug of the installed app, or None if it is not installed.

    Raises SupervisorError if the Supervisor cannot be reached.
    """
    installed = await get_supervisor_client(hass).addons.list()
    return _match_slug(addon.slug for addon in installed)


async def async_discover_store_slug(hass: HomeAssistant) -> str | None:
    """Return the slug the store knows the app by, installed or not.

    Returns None when no configured repository offers the app.
    Raises SupervisorError if the Supervisor cannot be reached.
    """
    store = await get_supervisor_client(hass).store.info()
    return _match_slug(addon.slug for addon in store.addons)


@callback
def get_addon_manager(hass: HomeAssistant, slug: str) -> AddonManager:
    """Get the app manager for a slug.

    AddonManager tracks in-flight tasks per app, so there must be at most one
    instance for any given slug.
    """
    managers = hass.data.setdefault(DATA_ADDON_MANAGERS, {})
    if slug not in managers:
        managers[slug] = AddonManager(hass, LOGGER, ADDON_NAME, slug)
    return managers[slug]
