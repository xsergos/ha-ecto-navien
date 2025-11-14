import logging
from typing import Any

from homeassistant.components.water_heater import (
    PRECISION_WHOLE,
    STATE_GAS,
    STATE_OFF,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .ectocontrol_api import get_device_info

_LOGGER = logging.getLogger(__name__)

TEMP_STEP = 1.0


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EctocontrolDWH(coordinator)], True)


class EctocontrolDWH(CoordinatorEntity, WaterHeaterEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Горячая вода (ГВС)"
        self._attr_unique_id = f"{coordinator.api._object_id}_dhw"
        self._attr_operation_list = [STATE_GAS, STATE_OFF]
        self._attr_target_temperature_step = 1.0
        self._attr_supported_features = WaterHeaterEntityFeature.TARGET_TEMPERATURE

    @property
    def state(self):
        return self.current_operation_mode

    @property
    def device_info(self) -> dict:
        return get_device_info(self.coordinator.api._object_id, self.coordinator.data)

    @property
    def temperature_unit(self):
        return "°C"

    @property
    def precision(self):
        return PRECISION_WHOLE

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
        return float(temp) if temp is not None else 50.0

    @property
    def current_operation_mode(self):
        status = self.coordinator.data.get("config", {}).get("heat_water")

        try:
            status = int(status)
        except (ValueError, TypeError):
            status = 0

        if status == 1:
            return STATE_GAS

        return STATE_OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)

        if temperature is None:
            return

        if temperature % TEMP_STEP != 0:
            rounded_temp = round(temperature / TEMP_STEP) * TEMP_STEP
            _LOGGER.warning(
                "Температура %s°C не кратна %s. Округлено до %s°C.",
                temperature,
                TEMP_STEP,
                rounded_temp,
            )
            temperature = rounded_temp

        if temperature < self.min_temp or temperature > self.max_temp:
            _LOGGER.error(
                "Установленная температура %s°C вне допустимого диапазона [%s, %s]",
                temperature,
                self.min_temp,
                self.max_temp,
            )
            return

        if await self.coordinator.api.set_dwh_temp(int(temperature)):
            _LOGGER.info("Установлена целевая температура ГВС: %s°C", temperature)
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "Не удалось установить целевую температуру ГВС: %s°C", temperature
            )
