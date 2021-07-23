import phonenumbers
from phonenumbers import carrier
from phonenumbers.phonenumberutil import number_type
from phonenumbers import NumberParseException
from codicefiscale import codicefiscale


def validate_fiscal_code(fiscal_code):
  try:
    codicefiscale.decode(fiscal_code)
    return True
  except ValueError:
    return False


def validate_phone(phone):
  try:
    return carrier._is_mobile(number_type(phonenumbers.parse(phone if "+" in phone else f"+39{phone}")))
  except NumberParseException:
    return False


async def decode_fiscal_code(fiscal_code):
  decoded_fiscal_code = codicefiscale.decode(fiscal_code)
  return {"fiscal_code": fiscal_code, "date": decoded_fiscal_code["birthdate"].strftime("%d/%m/%Y")}
