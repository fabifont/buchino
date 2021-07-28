import mongoengine
from place import Region, Country, Cap


# User document
class User(mongoengine.Document):
  _id = mongoengine.StringField(primary_key=True, required=True)  # telegram chat id
  health_card = mongoengine.StringField(required=True)  # health card number
  fiscal_code = mongoengine.StringField(required=True)  # fiscal code
  region = mongoengine.ReferenceField(Region, required=True)  # referred region
  country = mongoengine.ReferenceField(Country, required=True)  # referred country
  postal_code = mongoengine.ReferenceField(Cap, required=True)  # referred CAP
  date = mongoengine.StringField(required=True)  # birthdate
  phone = mongoengine.StringField(required=True)  # phone number
  is_vaccinated = mongoengine.BooleanField(default=False)  # is vaccinated flag
  appointments_by_distance = mongoengine.ListField(mongoengine.DictField(), default=[])  # appoinments list by distance
  appointments_by_date = mongoengine.ListField(mongoengine.DictField(), default=[])  # appointments list by date
  last_fetch = mongoengine.StringField(default="")  # last time appointments were fetched
  is_booking = mongoengine.BooleanField(default=False)  # is booking flag
  is_new = mongoengine.BooleanField(default=True)  # is new flag
