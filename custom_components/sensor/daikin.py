"""
Daikin sensors
"""
import urllib
import requests
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv

CONF_IPADDRESS = 'ipaddress'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IPADDRESS): cv.string,
})


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Demo sensors."""
    add_devices([
        DaikinSensor(config.get(CONF_IPADDRESS), 'htemp'),
        DaikinSensor(config.get(CONF_IPADDRESS), 'otemp'),
    ])


class DaikinSensor(Entity):
    """Representation of a Demo sensor."""

    def __init__(self, ipaddress, id):
        """Initialize the sensor."""
        self.ipaddress = ipaddress
        self.id = id

        response = requests.get('http://' + self.ipaddress + '/common/basic_info', timeout=10).text
        basic_info = dict(item.split("=") for item in response.split(","))
        self._name = urllib.parse.unquote(basic_info['name']) + " " + self.id
        self._unit_of_measurement = TEMP_CELSIUS
        self._battery = None
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self._unit_of_measurement

    def update(self):
        """Get the latest data and updates the states."""
        response = requests.get('http://' + self.ipaddress + '/aircon/get_sensor_info', timeout=10).text
        sensor_info = dict(item.split("=") for item in response.split(","))
        self._state = float(sensor_info[self.id])
