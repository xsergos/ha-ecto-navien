import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_OBJECT_ID, DOMAIN
from .ectocontrol_api import EctocontrolAPI, EctocontrolAuthError

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA_AUTH = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

DATA_SCHEMA_OBJECT = vol.Schema(
    {vol.Required(CONF_OBJECT_ID): str}
)


class EctocontrolConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    _auth_info = None
    _api_client: EctocontrolAPI = None

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            session = async_get_clientsession(self.hass)

            api = EctocontrolAPI(username, password, None, session)

            try:
                logged_in = await api.login()
            except EctocontrolAuthError:
                errors["base"] = "invalid_auth"
            else:
                if logged_in:
                    _LOGGER.info(
                        "Успешная аутентификация в Ectocontrol. Переход к вводу ID объекта."
                    )
                    self._auth_info = user_input
                    self._api_client = api
                    return await self.async_step_object_id()
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA_AUTH, errors=errors
        )

    async def async_step_object_id(self, user_input=None):
        errors = {}

        if not self._api_client or not self._auth_info:
            return self.async_abort(reason="reauth_failed")

        if user_input is not None:
            object_id = user_input[CONF_OBJECT_ID]

            await self.async_set_unique_id(object_id)
            self._abort_if_unique_id_configured()

            await self._api_client.set_object_id(object_id)

            try:
                got_state = await self._api_client.get_state()
            except EctocontrolAuthError:
                errors["base"] = "invalid_auth"
            else:
                if got_state:
                    return self.async_create_entry(
                        title=f"Ectocontrol Navien ({object_id})",
                        data={**self._auth_info, **user_input},
                    )
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="object_id", data_schema=DATA_SCHEMA_OBJECT, errors=errors
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        errors = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            api = EctocontrolAPI(
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                entry.data.get(CONF_OBJECT_ID),
                async_get_clientsession(self.hass),
            )
            try:
                logged_in = await api.login()
            except EctocontrolAuthError:
                errors["base"] = "invalid_auth"
            else:
                if logged_in:
                    return self.async_update_reload_and_abort(
                        entry, data_updates=user_input
                    )
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                DATA_SCHEMA_AUTH, {CONF_USERNAME: entry.data.get(CONF_USERNAME)}
            ),
            errors=errors,
        )
