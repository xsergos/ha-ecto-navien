import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .ectocontrol_api import get_device_info, get_nested_value

_LOGGER = logging.getLogger(__name__)

SENTINEL_TEMP_VALUE = 3276.7
SENSOR_TYPES = {
    "coolant_temperature": (
        "Температура теплоносителя",
        "state",
        "coolant_temperature",
        "°C",
        SensorDeviceClass.TEMPERATURE,
    ),
    "dwh_temperature": (
        "Температура ГВС",
        "state",
        "hot_water_supply_temperature",
        "°C",
        SensorDeviceClass.TEMPERATURE,
    ),
    "set_heating_temp": (
        "Целевая температура теплоносителя",
        "config",
        "set_channel_1_temperature",
        "°C",
        SensorDeviceClass.TEMPERATURE,
    ),
    "set_dwh_temp": (
        "Целевая температура ГВС",
        "config",
        "set_heat_water_temperature",
        "°C",
        SensorDeviceClass.TEMPERATURE,
    ),
    "error_code": ("Ошибка котла", "state", "error_code", None, None),
    "system_state_name": ("Статус котла", "state", "lk.state_name", None, None),
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for key, data in SENSOR_TYPES.items():
        entities.append(EctocontrolSensor(coordinator, key, *data))

    async_add_entities(entities, True)


class EctocontrolSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self, coordinator, key, name, path_section, path_key, unit, device_class=None
    ):
        super().__init__(coordinator)
        self._key = key
        self._path_section = path_section
        self._path_key = path_key

        self._attr_name = name
        self._attr_unique_id = f"{coordinator.api._object_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class

    @property
    def device_info(self) -> dict:
        return get_device_info(self.coordinator.api._object_id, self.coordinator.data)

    @property
    def native_value(self):
        data_section = self.coordinator.data.get(self._path_section, {})

        value = get_nested_value(data_section, self._path_key)

        if (
            value is not None
            and self._attr_device_class == SensorDeviceClass.TEMPERATURE
        ):
            try:
                float_value = float(value)

                if (
                    self._path_section == "config"
                    and float_value == SENTINEL_TEMP_VALUE
                ):
                    return None

                return float_value
            except ValueError:
                return value

        return value
