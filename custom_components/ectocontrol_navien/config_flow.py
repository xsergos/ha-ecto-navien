import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_OBJECT_ID, CONF_PASSWORD, CONF_USERNAME, DOMAIN
from .ectocontrol_api import EctocontrolAPI

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

            if await api.login():
                _LOGGER.info(
                    "Успешная аутентификация в Ectocontrol. Переход к вводу ID объекта."
                )
                self._auth_info = user_input
                self._api_client = api
                return await self.async_step_object_id()
            else:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA_AUTH, errors=errors
        )

    async def async_step_object_id(self, user_input=None):
        errors = {}

        if not self._api_client or not self._auth_info:
            return self.async_abort(reason="reauth_failed")

        if user_input is not None:
            object_id = user_input[CONF_OBJECT_ID]

            await self._api_client.set_object_id(object_id)

            if await self._api_client.get_state():
                return self.async_create_entry(
                    title=f"Ectocontrol Navien ({object_id})",
                    data={**self._auth_info, **user_input},
                )
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="object_id", data_schema=DATA_SCHEMA_OBJECT, errors=errors
        )
