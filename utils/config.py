import configparser

# config parser
config = configparser.ConfigParser()
# read config file
config.read("config.ini")


def get_value(key):
  """Return value from 'Telegram' section

  Args:
      key (string): key of the wanted value

  Returns:
      ? : the value corresponding to the key
  """
  return config.get("Telegram", key)
