import json
import logging

import aiohttp

from .const import (
    API_BASE_URL,
    API_LOGIN,
    DEVICE_INFO_MANUFACTURER,
    DEVICE_INFO_MODEL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def get_nested_value(data: dict, path: str):
    keys = path.split(".")
    value = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value


def get_device_info(object_id: str, data: dict) -> dict:
    return {
        "identifiers": {(DOMAIN, object_id)},
        "name": data.get("system_name", f"Ectocontrol Navien {object_id}"),
        "manufacturer": DEVICE_INFO_MANUFACTURER,
        "model": DEVICE_INFO_MODEL,
    }


class EctocontrolAPI:
    def __init__(self, username, password, object_id, session: aiohttp.ClientSession):
        self._username = username
        self._password = password
        self._object_id = object_id
        self._session = session
        self._token = None
        self.data = {}

    def set_token(self, token: str):
        self._token = token

    async def _send_multipart(self, url, payload):
        data = aiohttp.FormData()
        data.add_field("j", json.dumps(payload))

        headers = {"User-Agent": "HomeAssistant/Ectocontrol"}

        _LOGGER.debug("-------------------- API REQUEST --------------------")
        _LOGGER.debug("URL: %s", url)
        _LOGGER.debug("Headers: %s", headers)
        _LOGGER.debug("Payload (j): %s", json.dumps(payload))
        _LOGGER.debug("-----------------------------------------------------")

        try:
            async with self._session.post(url, data=data, headers=headers) as resp:
                status_code = resp.status
                response_text = await resp.text()

                _LOGGER.debug("--------------------- API RESPONSE --------------------")
                _LOGGER.debug("Status Code: %s", status_code)
                _LOGGER.debug("Content: %s", response_text)
                _LOGGER.debug("-------------------------------------------------------")

                resp.raise_for_status()

                response_json = json.loads(response_text)

                if url != API_LOGIN and response_json.get("success") is False:
                    _LOGGER.warning("API вернул 'success: false' в рабочем запросе.")
                    return "INVALID_TOKEN", None

                return "SUCCESS", response_json

        except aiohttp.ClientResponseError as e:
            _LOGGER.error("HTTP/Сетевая ошибка при выполнении запроса %s: %s", url, e)
            return "ERROR", None
        except Exception as e:
            _LOGGER.error("Непредвиденная ошибка при выполнении запроса %s: %s", url, e)
            return "ERROR", None

    async def login(self):
        payload = {"email": self._username, "password": self._password}
        _LOGGER.debug("Попытка входа в систему Ectocontrol...")

        status, response_json = await self._send_multipart(API_LOGIN, payload)

        if (
            status == "SUCCESS"
            and response_json
            and response_json.get("success")
            and response_json.get("token")
        ):
            self._token = response_json["token"]
            _LOGGER.info("Успешный вход в систему. Токен получен.")
            return True

        _LOGGER.error("Ошибка входа: %s", response_json)
        return False

    async def _ensure_authenticated(self):
        if self._token:
            return True
        return await self.login()

    async def _send_request(self, endpoint, data):
        if not await self._ensure_authenticated():
            return None

        data_with_token = {"token": self._token, "id_object": self._object_id, **data}
        status, response = await self._send_multipart(
            API_BASE_URL + endpoint, data_with_token
        )

        if status == "INVALID_TOKEN":
            _LOGGER.info("Повторная аутентификация...")
            if not await self.login():
                _LOGGER.error("Не удалось обновить токен. Запрос не выполнен.")
                return None

            data_with_new_token = {
                "token": self._token,
                "id_object": self._object_id,
                **data,
            }
            status_retry, response_retry = await self._send_multipart(
                API_BASE_URL + endpoint, data_with_new_token
            )

            if status_retry == "SUCCESS":
                return response_retry

            _LOGGER.error("Повторный запрос с новым токеном не удался.")
            return None

        return response

    async def get_state(self):
        if self._object_id is None:
            _LOGGER.error("Нельзя вызвать get_state без установленного ID объекта.")
            return False

        data = {}
        response = await self._send_request("objects/get_object", data)

        if response:
            self.data = response
            return True
        return False

    async def set_object_id(self, object_id):
        self._object_id = object_id

    async def set_heating_status(self, status: int):
        data = {"channel_1_status": status}
        _LOGGER.info(
            "Установка статуса отопления: %s", "ВКЛ" if status == 1 else "ВЫКЛ"
        )
        return await self._send_request("task/send_opentherm_program_3x_system", data)

    async def set_heating_temp(self, temperature: float):
        if temperature % 10 != 0:
            _LOGGER.error(
                "Ошибка валидации: Температура отопления (%s°C) должна быть кратна 10.",
                temperature,
            )
            return None

        if not await self.set_heating_status(1):
            _LOGGER.warning(
                "Не удалось включить отопление перед установкой температуры."
            )

        data = {"set_channel_1_temperature": str(int(temperature))}
        _LOGGER.info("Установка температуры отопления на %s°C", temperature)
        return await self._send_request("task/send_opentherm_program_3x_system", data)

    async def set_dwh_temp(self, temperature: float):
        data = {"set_heat_water_temperature": str(int(temperature))}
        return await self._send_request("task/send_opentherm_program_3x_system", data)
