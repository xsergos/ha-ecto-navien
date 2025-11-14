import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    UnitOfTemperature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EctocontrolCoordinator
from .ectocontrol_api import get_device_info

_LOGGER = logging.getLogger(__name__)

TEMP_STEP = 10.0
SENTINEL_TEMP_VALUE = 3276.7

HVAC_MODE_HEAT = HVACMode.HEAT
HVAC_MODE_OFF = HVACMode.OFF

SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.TURN_OFF
    | ClimateEntityFeature.TURN_ON
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EctocontrolCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities([EctocontrolNavienClimate(coordinator)], True)


class EctocontrolNavienClimate(
    CoordinatorEntity[EctocontrolCoordinator], ClimateEntity
):
    _attr_temperature_unit = "°C"
    _attr_has_entity_name = True
    _attr_name = "Отопление"

    def __init__(self, coordinator: EctocontrolCoordinator) -> None:
        super().__init__(coordinator)
        object_id = self.coordinator.api._object_id
        self._attr_unique_id = f"{object_id}_heating_climate"
        self._attr_supported_features = SUPPORT_FLAGS

    @property
    def device_info(self) -> dict:
        return get_device_info(self.coordinator.api._object_id, self.coordinator.data)

    @property
    def target_temperature_step(self) -> float:
        return TEMP_STEP

    @property
    def hvac_mode(self) -> HVACMode:
        status = self.coordinator.data.get("config", {}).get("channel_1_status")
        return HVAC_MODE_HEAT if status == 1 else HVAC_MODE_OFF

    @property
    def hvac_modes(self) -> list[HVACMode]:
        return [HVAC_MODE_HEAT, HVAC_MODE_OFF]

    @property
    def current_temperature(self) -> float | None:
        temp = self.coordinator.data.get("state", {}).get("coolant_temperature")
        return float(temp) if temp is not None else None

    @property
    def target_temperature(self) -> float | None:
        temp_str = self.coordinator.data.get("config", {}).get(
            "set_channel_1_temperature"
        )
        if temp_str is not None:
            try:
                temp = float(temp_str)
                if temp == SENTINEL_TEMP_VALUE:
                    return None
                return temp
            except ValueError:
                _LOGGER.error(
                    "Не удалось преобразовать целевую температуру '%s' в число.",
                    temp_str,
                )
                return None
        return None

    @property
    def min_temp(self) -> float:
        min_temp = self.coordinator.data.get("config", {}).get(
            "channel_1_min_temperature", 40.0
        )
        return float(min_temp)

    @property
    def max_temp(self) -> float:
        max_temp = self.coordinator.data.get("config", {}).get(
            "channel_1_max_temperature", 70.0
        )
        return float(max_temp)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        status = 1 if hvac_mode == HVAC_MODE_HEAT else 0

        if await self.coordinator.api.set_heating_status(status):
            _LOGGER.info("Установлен режим работы: %s", hvac_mode.value)
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Не удалось установить режим работы: %s", hvac_mode.value)

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

        if await self.coordinator.api.set_heating_temp(temperature):
            _LOGGER.info("Установлена целевая температура отопления: %s°C", temperature)
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Не удалось установить целевую температуру.")
