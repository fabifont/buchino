import mongoengine


# Region document
class Region(mongoengine.Document):
  name = mongoengine.StringField(required=True)  # region name


# CAP document
class Cap(mongoengine.Document):
  number = mongoengine.StringField(required=True, min_length=5, max_length=5)  # CAP number
  region = mongoengine.ReferenceField(Region, required=True)  # referred region


# Country document
class Country(mongoengine.Document):
  name = mongoengine.StringField(required=True)  # country name
  region = mongoengine.ReferenceField(Region, required=True)  # referred region
  postal_code = mongoengine.ReferenceField(Cap, required=True)  # referred CAP
