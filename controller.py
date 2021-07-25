from place import Region, Country, Cap
from user import User


async def get_regions():
  return Region.objects.order_by("name")


async def get_postal_codes(region_name):
  region = Region.objects(name=region_name).first()
  return Cap.objects(region=region).order_by("number")


async def get_countries(region_name, postal_code_number):
  region = Region.objects(name=region_name).first()
  postal_code = Cap.objects(number=postal_code_number).first()
  return Country.objects(region=region, postal_code=postal_code).order_by("name")


async def is_booking(_id):
  return User.objects.get(_id=str(_id)).is_booking


async def is_vaccinated(_id):
  return User.objects.get(_id=str(_id)).is_vaccinated


async def get_last_fetch(_id):
  return User.objects.get(_id=str(_id)).last_fetch


async def change_booking_state(_id, is_booking):
  User.objects(_id=str(_id)).update(
      set__is_booking=is_booking
  )


async def check_user(_id):
  return len(User.objects(_id=str(_id))) > 0


async def add_user(user):
  User(
      _id=str(user["_id"]),
      health_card=user["health_card"],
      fiscal_code=user["fiscal_code"],
      date=user["date"],
      region=Region.objects(name=user["region"]).first(),
      country=Country.objects(name=user["country"]).first(),
      postal_code=Cap.objects(number=user["postal_code"]).first(),
      phone=user["phone"]).save()


async def delete_user(_id):
  User.objects(_id=str(_id)).delete()


async def get_appointments(_id):
  user = User.objects.get(_id=str(_id))
  unique_appointments = user.appointments_by_distance + \
      [appointment for appointment in user.appointments_by_date if appointment not in user.appointments_by_distance]
  return [{"info": f"{appointment['date'][:5]} {appointment['date'][11:16]} {appointment['place'].replace('CENTRO VACCINALE: ', '')}"} for appointment in unique_appointments]


def is_same_appointment(_id, input_appointment):
  user = User.objects.get(_id=str(_id))
  unique_appointments = user.appointments_by_distance + \
      [appointment for appointment in user.appointments_by_date if appointment not in user.appointments_by_distance]
  return {"info": input_appointment} in [{"info": f"{appointment['date'][:5]} {appointment['date'][11:16]} {appointment['place'].replace('CENTRO VACCINALE: ', '')}"} for appointment in unique_appointments]


async def check_appointments(_id):
  user = User.objects.get(_id=str(_id))
  return user.last_fetch != ""


def check_region(region_name):
  return len(Region.objects(name=region_name)) > 0


def check_postal_code(region_name, postal_code_number):
  region = Region.objects(name=region_name).first()
  return len(Cap.objects(region=region, number=postal_code_number)) > 0


def check_country(region_name, country_name):
  region = Region.objects(name=region_name).first()
  return len(Country.objects(region=region, name=country_name)) > 0


def get_users():
  return User.objects.aggregate(
      {
          "$lookup": {
              "from": "region",
              "localField": "region",
              "foreignField": "_id",
              "as": "_region"
          }
      },
      {"$unwind": "$_region"},
      {
          "$lookup": {
              "from": "country",
              "localField": "country",
              "foreignField": "_id",
              "as": "_country"
          }
      },
      {"$unwind": "$_country"},
      {
          "$lookup": {
              "from": "cap",
              "localField": "postal_code",
              "foreignField": "_id",
              "as": "_cap"
          }
      },
      {"$unwind": "$_cap"},
      {
          "$project": {
              "_id": 1,
              "health_card": 1,
              "fiscal_code": 1,
              "phone": 1,
              "date": 1,
              "appointments_by_distance": 1,
              "appointments_by_date": 1,
              "is_vaccinated": 1,
              "region": "$_region.name",
              "country": "$_country.name",
              "postal_code": "$_cap.number"
          }
      }
  )


def update_appointments(_id, appointments_by_distance, appointments_by_date, last_fetch):
  User.objects(_id=_id).update(
      set__appointments_by_distance=appointments_by_distance,
      set__appointments_by_date=appointments_by_date,
      set__last_fetch=last_fetch
  )


async def update_status(_id, is_vaccinated):
  User.objects(_id=str(_id)).update(
      set__is_vaccinated=is_vaccinated
  )


def get_active_users():
  return len(User.objects(is_vaccinated=False))


def get_user(_id):
  return list(User.objects.aggregate(
      {"$match": {"_id": _id}},
      {
          "$lookup": {
              "from": "region",
              "localField": "region",
              "foreignField": "_id",
              "as": "_region"
          }
      },
      {"$unwind": "$_region"},
      {
          "$lookup": {
              "from": "country",
              "localField": "country",
              "foreignField": "_id",
              "as": "_country"
          }
      },
      {"$unwind": "$_country"},
      {
          "$lookup": {
              "from": "cap",
              "localField": "postal_code",
              "foreignField": "_id",
              "as": "_cap"
          }
      },
      {"$unwind": "$_cap"},
      {
          "$project": {
              "_id": 1,
              "health_card": 1,
              "fiscal_code": 1,
              "phone": 1,
              "date": 1,
              "appointments_by_distance": 1,
              "appointments_by_date": 1,
              "is_vaccinated": 1,
              "region": "$_region.name",
              "country": "$_country.name",
              "postal_code": "$_cap.number"
          }
      }
  ))[0]
