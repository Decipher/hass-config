import logging
import requests
import urllib
import voluptuous as vol

from homeassistant.components.climate import ClimateDevice, PLATFORM_SCHEMA
from homeassistant.const import (
    TEMP_CELSIUS, ATTR_TEMPERATURE, CONF_PORT, CONF_NAME, CONF_ID)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_IPADDRESS = 'ipaddress'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IPADDRESS): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([
        DaikinClimate(config.get(CONF_IPADDRESS)),
    ])


class DaikinClimate(ClimateDevice):
    """Representation of a demo climate device."""

    def __init__(self, ipaddress):
        """Initialize the climate device."""
        self.daikin = DaikinAPI(ipaddress);

        self._fan_list = {'A': "Automatic", 'B': "Indoor unit quiet", 3: "1", 4: "2", 5: "3", 6: "4", 7: "5"}
        self._operation_list = {1: "Auto", 3: "Cooling", 4: "Heating", 6: "Fan", 2: "Dry", 0: "Off"}
        self._swing_list = {0: "Off", 1: "Up-down swing", 2: "Left-right swing", 3: "3D swing"}

        self._away = None
        self._aux = None
        self._current_humidity = None
        self._target_humidity = None
        self._target_temperature_low = None
        self._target_temperature_high = None

        self.update()

    def update(self):
        sensor_info = self.daikin.get_request('/aircon/get_sensor_info')
        self._current_temperature = float(sensor_info['htemp'])

        control_info = self.daikin.get_request('/aircon/get_control_info')
        if int(control_info['pow']) == 0:
            self._current_operation = "Off"
        else:
            mode = int(control_info['mode'])
            mode = mode == 0 and 1 or mode
            self._current_operation = self._operation_list[mode]

        self._current_fan_mode = self._fan_list[control_info['f_rate']]
        self._current_swing_mode = self._swing_list[int(control_info['f_dir'])]
        self._target_temperature = control_info['stemp']

    @property
    def name(self):
        """Return the name of the climate device."""
        return self.daikin.name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        if self._current_operation in ['Auto', 'Cooling', 'Heating']:
            return self._target_temperature
        return None

    @property
    def current_operation(self):
        """Return current operation."""
        return self._current_operation

    @property
    def operation_list(self):
        """List of available operation modes."""
        return list(self._operation_list.values())

    @property
    def current_fan_mode(self):
        """Return the fan setting."""
        if self._current_operation == 'Off':
            return None
        return self._current_fan_mode

    @property
    def fan_list(self):
        """List of available fan modes."""
        return list(self._fan_list.values())

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return 18

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return 30

    def set_temperature(self, **kwargs):
        """Set new target temperatures."""
        data = {'stemp': kwargs.get(ATTR_TEMPERATURE)}
        self.daikin.post_request(data)

        self._target_temperature = data['stemp']
        self.update_ha_state()

    def set_swing_mode(self, swing_mode):
        """Set new target temperature."""
        data = {}
        for key in self._swing_list:
            if self._swing_list[key] == swing_mode:
                data['f_dir'] = key
                break
        self.daikin.post_request(data)

        self._current_swing_mode = swing_mode
        self.update_ha_state()

    def set_fan_mode(self, fan):
        """Set new target temperature."""
        data = {}
        for key in self._fan_list:
            if self._fan_list[key] == fan:
                data['f_rate'] = key
                break
        self.daikin.post_request(data)

        self._current_fan_mode = fan
        self.update_ha_state()

    def set_operation_mode(self, operation_mode):
        """Set new operation."""
        data = {}
        for key in self._operation_list:
            if self._operation_list[key] == operation_mode:
                if (key == 0):
                    data['pow'] = 0
                else:
                    data['pow'] = 1
                    data['mode'] = key
                break
        self.daikin.post_request(data)

        self._current_operation = operation_mode
        self.update_ha_state()

    @property
    def current_swing_mode(self):
        """Return the swing setting."""
        if self._current_operation == 'Off':
            return None
        return self._current_swing_mode

    @property
    def swing_list(self):
        """List of available swing modes."""
        return list(self._swing_list.values())



class DaikinAPI(object):
    def __init__(self, ip):
        self.ip = ip
        self.url = "http://" + self.ip

        try:
            basic_info = self.get_request('/common/basic_info')
        except requests.exceptions.ConnectionError as ex:
            logging.error("Unable to connect to Daikin: %s", str(self.ip))
            return False

        self.name = urllib.parse.unquote(basic_info['name'])

    def get_request_item(self, endpoint, item):
        try:
            data = self.get_request(endpoint)
        except requests.exceptions.ConnectionError as ex:
            return False

        if item in data:
            return data[item]
        return False

    def get_request(self, endpoint):
        response = requests.get(self.url + endpoint).text
        data = dict(item.split("=") for item in response.split(","))
        return data

    def post_request(self, data):
        post_data = self.prepare_post_data(data)
        params = urllib.parse.urlencode(post_data)

        response = requests.get(self.url + '/aircon/set_control_info?' + params).text
        data = dict(item.split("=") for item in response.split(","))
        return data

    def prepare_post_data(self, data):
        post_data = {}
        response_data = self.get_request('/aircon/get_control_info')

        post_data['pow'] = response_data['pow']
        post_data['mode'] = response_data['mode']
        post_data['stemp'] = response_data['stemp']
        post_data['shum'] = response_data['shum']
        post_data['f_rate'] = response_data['f_rate']
        post_data['f_dir'] = response_data['f_dir']

        post_data = {**post_data, **data}

        return post_data
