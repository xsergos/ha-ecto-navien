DOMAIN = "ectocontrol_navien"
PLATFORMS = ["climate", "sensor", "water_heater"]

API_BASE_URL = "https://my.ectostroy.ru/api/"
API_LOGIN = API_BASE_URL + "user/login"
API_GET_OBJECT = API_BASE_URL + "objects/get_object"
API_SEND_PROGRAM = API_BASE_URL + "task/send_opentherm_program_3x_system"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_OBJECT_ID = "object_id"

DEVICE_INFO_MANUFACTURER = "Ectocontrol"
DEVICE_INFO_MODEL = "Navien Adapter"
