import json
import os
bot_name = os.environ['BOT_NAME']


class ConfigurationWrapper:
    def __init__(self, data):
        self._data = data


    def __getattr__(self, attr):
        return self._data[attr]


with open("/run/secrets/{}_config".format(bot_name)) as config_file:
    data = ConfigurationWrapper(json.load(config_file))
