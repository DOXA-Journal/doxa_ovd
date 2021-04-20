import json

class ConfigurationWrapper:
    def __init__(self, data):
        self._data = data


    def __getattr__(self, attr):
        return self._data[attr]


with open("config.json") as config_file:
    data = ConfigurationWrapper(json.load(config_file))
