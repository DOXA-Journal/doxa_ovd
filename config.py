import json

class ConfigurationWrapper:
    def __init__(self, data):
        self._data = data


    def __getattr__(self, attr):
        return self._data[attr]


try:
    with open("/run/secrets/doxa_bot_config") as config_file:
        data = ConfigurationWrapper(json.load(config_file))
except FileNotFoundError:
    with open("/run/secrets/doxa_ovd_config") as config_file:
        data = ConfigurationWrapper(json.load(config_file))
