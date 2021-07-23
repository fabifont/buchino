import mongoengine


class Region(mongoengine.Document):
  name = mongoengine.StringField(required=True)


class Cap(mongoengine.Document):
  number = mongoengine.StringField(required=True, min_length=5, max_length=5)
  region = mongoengine.ReferenceField(Region, required=True)


class Country(mongoengine.Document):
  name = mongoengine.StringField(required=True)
  region = mongoengine.ReferenceField(Region, required=True)
  postal_code = mongoengine.ReferenceField(Cap, required=True)
