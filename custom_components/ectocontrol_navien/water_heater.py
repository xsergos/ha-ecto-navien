import logging

from homeassistant.components.water_heater import (
    STATE_ELECTRIC,
    STATE_OFF,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .ectocontrol_api import get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EctocontrolDWH(coordinator)], True)


class EctocontrolDWH(CoordinatorEntity, WaterHeaterEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Горячая вода (ГВС)"
        self._attr_unique_id = f"{coordinator.api._object_id}_dhw"
        self._attr_supported_features = WaterHeaterEntityFeature.TARGET_TEMPERATURE

    @property
    def device_info(self) -> dict:
        return get_device_info(self.coordinator.api._object_id, self.coordinator.data)

    @property
    def temperature_unit(self):
        return "°C"

    @property
    def current_temperature(self):
        temp = self.coordinator.data.get("state", {}).get(
            "hot_water_supply_temperature"
        )
        return float(temp) if temp is not None else None

    @property
    def target_temperature(self):
        temp = self.coordinator.data.get("config", {}).get("set_heat_water_temperature")
        return float(temp) if temp is not None else None

    @property
    def min_temp(self):
        temp = self.coordinator.data.get("config", {}).get("heat_water_min_temperature")
        return float(temp) if temp is not None else 35.0

    @property
    def max_temp(self):
        temp = self.coordinator.data.get("config", {}).get("heat_water_max_temperature")
        return float(temp) if temp is not None else 45.0

    @property
    def current_operation_mode(self):
        status = self.coordinator.data.get("state", {}).get("heat_water")
        if status == 1:
            return STATE_ELECTRIC

        return STATE_OFF

    @property
    def operation_list(self):
        return [STATE_OFF, STATE_ELECTRIC]

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get("temperature")
        if temperature is None:
            return

        success = await self.coordinator.api.set_dwh_temp(temperature)
        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Не удалось установить целевую температуру ГВС.")
