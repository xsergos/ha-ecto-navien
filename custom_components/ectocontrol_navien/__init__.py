import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_OBJECT_ID, CONF_PASSWORD, CONF_USERNAME, DOMAIN, PLATFORMS
from .coordinator import EctocontrolCoordinator
from .ectocontrol_api import EctocontrolAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    object_id = entry.data.get(CONF_OBJECT_ID)

    session = async_get_clientsession(hass)

    api = EctocontrolAPI(username, password, object_id, session)

    coordinator = EctocontrolCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
