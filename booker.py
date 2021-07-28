import time
import asyncio
import logging
import scraper as scraper
import controller as controller
from config import get_value
from aiogram import Bot
from selenium import webdriver


LOGGER = logging.getLogger()


def wait_code(_id):
  """Wait for SMS code for a maximum of 2 minutes

  Args:
      _id: telegram chat id

  Returns:
      dict: dict with _id and code
      None: code not found
  """
  for i in range(120):
    # read file
    with open("codes.txt", "r") as f:
      codes = f.readlines()
    # check a code with matching _id
    for raw_code in codes:
      code_data = raw_code.split("%")
      # if found
      if code_data[0] == _id:
        # remove line from file
        codes.remove(raw_code)
        with open("codes.txt", "w") as f:
          f.writelines(codes)
        # return dict
        return {"_id": code_data[0], "code": code_data[1]}
    time.sleep(1)
  return None


def find_appointment(driver, wanted_date, wanted_place):
  """Search for the wanted appointment on the page and click on it

  Args:
      driver: webdriver
      wanted_date (string): wanted appointment date
      wanted_place (string): wanted appointment place

  Returns:
      True: appointment found and clicked
      False: appointment not found
  """
  # list of appointments
  appointments = driver.find_elements_by_class_name("text-wrap")
  for appointment in appointments:
    info = appointment.find_elements_by_tag_name("span")
    place = info[2].text.upper()
    date = f"{(info[0].text)[-10:]} {(info[1].text)[-5:]}:00"
    # check if appointment equals wanted appointment
    if scraper.are_equal({"date": date, "place": place}, {"date": wanted_date, "place": wanted_place}, True):
      appointment.click()
      return True
  return False


def check(driver, appointment):
  """Check if wanted appointment is still available and proceed with the booking

  Args:
      driver: webdriver
      appointment (dict): wanted appointment

  Returns:
      True: appointment found and booking process started
      False: appointment not found
  """
  # check if appointment is still available
  # by distance filter
  scraper.switch_filter(driver, "Distanza")
  if not find_appointment(driver, appointment["date"], appointment["place"]):
    # by date filter
    scraper.switch_filter(driver, "Data")
    # appointment not found
    if not find_appointment(driver, appointment["date"], appointment["place"]):
      return False

  try:
    # start booking process
    driver.execute_script("document.getElementsByClassName('btn btn-primary btn-icon')[0].click()")
    driver.execute_script("document.getElementsByClassName('btn btn-primary btn-icon mr-4 btn-large')[0].click()")
    return True
  except Exception:
    # appointment is not available anymore
    return False


def book(driver, _id):
  """Perform booking process

  Args:
      driver: webdriver
      _id (str): telegram chat id

  Returns:
      0 (int): booking done
      -1 (int): code not found
      -2 (int): wrong or expired code or appointment not available anymore
  """
  # search code
  code = wait_code(_id)
  if code is None:
    return -1

  # fill code field and proceed
  scraper.wait_until_present(driver, el_id="otpCode")
  driver.find_element_by_id("otpCode").send_keys(code["code"])
  driver.execute_script("document.getElementsByClassName('btn btn-primary btn-icon')[0].click()")
  try:
    # if that element is present booking was successful
    scraper.wait_until_present(driver, el_id="bookingDetailsSection", duration=5)
    return 0
  except Exception:
    # booking failed due to wrong/expired code or appointment not available
    return -2


def start_booker():
  """Start booker loop"""
  LOGGER.info("Starting booker.")
  # bot istance
  bot = Bot(get_value("token"))
  # webdriver options
  options = webdriver.firefox.options.Options()
  options.headless = True
  # wedriver
  driver = webdriver.Firefox(options=options)
  # files initialization
  with open("appointments.txt", "w"):
    pass
  with open("codes.txt", "w"):
    pass
  # loop
  while True:
    try:
      # read booking requests
      with open("appointments.txt", "r") as f:
        bookings = f.readlines()
      for raw_booking in bookings:
        # remove booking request from the file
        bookings.remove(raw_booking)
        with open("appointments.txt", "w") as f:
          f.writelines(bookings)
        # parse data
        booking_data = raw_booking.split("%")
        booking = {"_id": booking_data[0], "date": booking_data[1][:11], "place": booking_data[1][12:]}
        # get user
        user = controller.get_user(booking["_id"])
        # perform login
        scraper.login(driver, user["health_card"], user["fiscal_code"])
        is_vaccinated = scraper.find(driver, user["region"], user["country"], user["postal_code"], user["phone"], user["date"])
        # if user has already booked an appointment or he disabled notifications
        if is_vaccinated:
          # set is_booking to False and is_vaccinated to True and send a notification
          asyncio.get_event_loop().run_until_complete(controller.change_booking_state(user["_id"], False))
          asyncio.get_event_loop().run_until_complete(controller.update_status(user["_id"], is_vaccinated))
          asyncio.get_event_loop().run_until_complete(bot.send_message(
              user["_id"], "Ho notato che hai già effettuato una prenotazione perciò non controllerò le date per te.\n\nSe dovessi annullare la prenotazione e volessi essere notificato ancora digita /reset\n\nSe vuoi cancellare i tuoi dati digita /cancella"))
          # next booking request
          time.sleep(30)
          continue
        still_available = check(driver, booking)
        # if wanted appointment is still availale
        if still_available:
          # send SMS code request notification
          asyncio.get_event_loop().run_until_complete(bot.send_message(
              user["_id"], "Invia il comando /codice per procedere con l'inserimento del codice."))
          # perform  booking
          result = book(driver, booking["_id"])
          # booking failed -> if result = -2
          result_message = "Il codice che hai fornito non è corretto o è scaduto, oppure l'appuntamento non è più disponibile."
          # booking done
          if result == 0:
            result_message = "Prenotazione effettuata con successo. Riceverai un SMS di conferma."
          # booking failed
          elif result == -1:
            result_message = "Non hai fornito un codice in tempo (attesa massima 2 minuti)."
          # send a notification with the booking result
          asyncio.get_event_loop().run_until_complete(bot.send_message(user["_id"], result_message))
        else:
          asyncio.get_event_loop().run_until_complete(bot.send_message(user["_id"], "L'appuntamento che volevi prenotare non è più disponibile."))
        # set is_booking to False
        asyncio.get_event_loop().run_until_complete(controller.change_booking_state(user["_id"], False))
        # clear cookies and wait 30 seconds for next
        driver.delete_all_cookies()
        time.sleep(30)
      # loop cycle done, wait 1 minute for next cycle
      time.sleep(60)
    except Exception as e:
      LOGGER.exception(e)
      try:
        # set is_booking to False
        asyncio.get_event_loop().run_until_complete(controller.change_booking_state(user["_id"], False))
        # clear cookies
        driver.delete_all_cookies()
        # check IP ban
        if "Sessione scaduta" in driver.page_source:
          LOGGER.info("IP banned")
          # wait 60 minutes but I think it's useless, need to change IP
          time.sleep(60 * 60)
      except Exception as e:
        LOGGER.exception(e)
      # wait 5 minutes
      time.sleep(60 * 5)
