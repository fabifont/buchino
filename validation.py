import phonenumbers
from phonenumbers import carrier
from phonenumbers.phonenumberutil import number_type
from phonenumbers import NumberParseException
from codicefiscale import codicefiscale


def validate_fiscal_code(fiscal_code):
  """Check whether the fiscal code is decodable

  Args:
      fiscal_code (string): fiscal code to be decoded

  Returns:
      True: fiscal code is decodable
      False: fiscal code is not decodable
  """
  try:
    codicefiscale.decode(fiscal_code)
    return True
  except ValueError:
    return False


def validate_phone(phone):
  """Check whether the phone number is valid

  Args:
      phone (string): phone number to be validated

  Returns:
      True: phone number is valid
      False: phone number is not valid
  """
  try:
    return carrier._is_mobile(number_type(phonenumbers.parse(phone if "+" in phone else f"+39{phone}")))
  except NumberParseException:
    return False


async def decode_fiscal_code(fiscal_code):
  """Return a dict that contains the fiscal_code uppercase and the birth date

  Args:
      fiscal_code (string): fiscal code to be decoded

  Returns:
      dict: fiscal_code and date
  """
  decoded_fiscal_code = codicefiscale.decode(fiscal_code)
  return {"fiscal_code": fiscal_code.upper(), "date": decoded_fiscal_code["birthdate"].strftime("%d/%m/%Y")}
