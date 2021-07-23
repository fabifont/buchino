import configparser

config = configparser.ConfigParser()
config.read("config.ini")


def get_value(key):
  return config.get("Telegram", key)
