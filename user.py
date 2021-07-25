import mongoengine
from place import Region, Country, Cap


class User(mongoengine.Document):
  _id = mongoengine.StringField(primary_key=True, required=True)
  health_card = mongoengine.StringField(required=True)
  fiscal_code = mongoengine.StringField(required=True)
  region = mongoengine.ReferenceField(Region, required=True)
  country = mongoengine.ReferenceField(Country, required=True)
  postal_code = mongoengine.ReferenceField(Cap, required=True)
  date = mongoengine.StringField(required=True)
  phone = mongoengine.StringField(required=True)
  is_vaccinated = mongoengine.BooleanField(default=False)
  appointments_by_distance = mongoengine.ListField(mongoengine.DictField(), default=[])
  appointments_by_date = mongoengine.ListField(mongoengine.DictField(), default=[])
  last_fetch = mongoengine.StringField(default="")
  is_booking = mongoengine.BooleanField(default=False)
