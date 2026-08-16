"""Config flow for the Media Sync integration."""

import asyncio
from typing import Any, override

import voluptuous as vol

from homeassistant.components.hassio import AddonError, AddonState, SupervisorError
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .addon import async_discover_store_slug, get_addon_manager
from .const import ADDON_NAME, CONF_ADDON_SLUG, DOMAIN, LOGGER


class MediaSyncConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Media Sync config flow."""

    def __init__(self) -> None:
        """Initialize the flow."""
        self.slug: str | None = None
        self.install_task: asyncio.Task | None = None

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Find the app, offering to install it when it is only in the store."""
        try:
            slug = await async_discover_store_slug(self.hass)
        except SupervisorError:
            return self.async_abort(reason="addon_info_failed")

        if slug is None:
            return self.async_abort(reason="repository_not_added")

        self.slug = slug

        try:
            addon_info = await get_addon_manager(
                self.hass, slug
            ).async_get_addon_info()
        except AddonError:
            return self.async_abort(reason="addon_info_failed")

        if addon_info.state is AddonState.NOT_INSTALLED:
            return await self.async_step_install_addon()

        return await self.async_step_confirm()

    async def async_step_install_addon(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Install the app."""
        if not self.install_task:
            self.install_task = self.hass.async_create_task(self._async_install_addon())

        if not self.install_task.done():
            return self.async_show_progress(
                step_id="install_addon",
                progress_action="install_addon",
                progress_task=self.install_task,
            )

        try:
            await self.install_task
        except AddonError as err:
            LOGGER.error("Failed to install the %s app: %s", ADDON_NAME, err)
            return self.async_show_progress_done(next_step_id="install_failed")
        finally:
            self.install_task = None

        # A freshly installed app still has placeholder settings, so there is
        # no point starting it here.
        return self.async_show_progress_done(next_step_id="configure_app")

    async def _async_install_addon(self) -> None:
        """Install the app through the Supervisor."""
        assert self.slug is not None
        await get_addon_manager(self.hass, self.slug).async_schedule_install_addon()

    async def async_step_install_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Report that installing the app failed."""
        return self.async_abort(reason="addon_install_failed")

    async def async_step_configure_app(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Point the user at the app's settings after installing it."""
        if user_input is None:
            return self.async_show_form(
                step_id="configure_app", data_schema=vol.Schema({})
            )
        return self._create_entry()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm setup for an app that is already installed."""
        if user_input is None:
            return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}))
        return self._create_entry()

    def _create_entry(self) -> ConfigFlowResult:
        """Create the config entry for the discovered app."""
        return self.async_create_entry(
            title=ADDON_NAME, data={CONF_ADDON_SLUG: self.slug}
        )
