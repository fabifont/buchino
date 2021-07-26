import mongoengine
import data
from place import Region, Country, Cap


def init_places():
  """Insert static data into the database (e.g. regions, countries, postal codes)
  """
  mongoengine.connect(host="mongodb://127.0.0.1:27017/buchino")
  regions = data.get_regions()
  for region in regions:
    mongo_region = Region(name=region).save()
    postal_codes = data.get_postal_codes(region)
    for postal_code in postal_codes:
      mongo_postal_code = Cap(number=postal_code, region=mongo_region).save()
      countries = data.get_countries(region, postal_code)
      for country in countries:
        Country(name=country, region=mongo_region, postal_code=mongo_postal_code).save()
  mongoengine.disconnect()
