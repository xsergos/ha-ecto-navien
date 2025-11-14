import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .ectocontrol_api import EctocontrolAPI

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)


class EctocontrolCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api: EctocontrolAPI):
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self):
        success = await self.api.get_state()
        if not success:
            raise UpdateFailed("Ошибка при получении данных с Ectocontrol API")

        return self.api.data
