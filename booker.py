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
  for i in range(120):
    with open("codes.txt", "r") as f:
      codes = f.readlines()
    for raw_code in codes:
      code_data = raw_code.split("%")
      if code_data[0] == _id:
        codes.remove(raw_code)
        with open("codes.txt", "w") as f:
          f.writelines(codes)
        return {"_id": code_data[0], "code": code_data[1]}
    time.sleep(1)
  return None


def find_appointment(driver, wanted_date, wanted_place):
  appointments = driver.find_elements_by_class_name("text-wrap")
  for appointment in appointments:
    info = appointment.find_elements_by_tag_name("span")
    place = info[2].text.upper()
    date = f"{(info[0].text)[-10:]} {(info[1].text)[-5:]}:00"
    if scraper.are_equal({"date": date, "place": place}, {"date": wanted_date, "place": wanted_place}, True):
      appointment.click()
      return True
  return False


def check(driver, appointment):
  scraper.switch_filter(driver, "Distanza")
  if not find_appointment(driver, appointment["date"], appointment["place"]):
    scraper.switch_filter(driver, "Data")
    if not find_appointment(driver, appointment["date"], appointment["place"]):
      return False

  try:
    driver.execute_script("document.getElementsByClassName('btn btn-primary btn-icon')[0].click()")
    driver.execute_script("document.getElementsByClassName('btn btn-primary btn-icon mr-4 btn-large')[0].click()")
    return True
  except Exception:
    return False


def book(driver, _id):
  code = wait_code(_id)
  if code is None:
    return -1

  scraper.wait_until_present(driver, el_id="otpCode")
  driver.find_element_by_id("otpCode").send_keys(code["code"])
  driver.execute_script("document.getElementsByClassName('btn btn-primary btn-icon')[0].click()")
  try:
    scraper.wait_until_present(driver, el_id="bookingDetailsSection", duration=5)
    return 0
  except Exception:
    return -2


def start_booker():
  LOGGER.info("Starting booker.")
  bot = Bot(get_value("token"))
  options = webdriver.firefox.options.Options()
  options.headless = True
  driver = webdriver.Firefox(options=options)
  with open("appointments.txt", "w"):
    pass
  with open("codes.txt", "w"):
    pass
  while True:
    try:
      with open("appointments.txt", "r") as f:
        bookings = f.readlines()
      for raw_booking in bookings:
        bookings.remove(raw_booking)
        with open("appointments.txt", "w") as f:
          f.writelines(bookings)
        booking_data = raw_booking.split("%")
        booking = {"_id": booking_data[0], "date": booking_data[1][:11], "place": booking_data[1][12:]}
        user = controller.get_user(booking["_id"])
        scraper.login(driver, user["health_card"], user["fiscal_code"])
        is_vaccinated = scraper.find(driver, user["region"], user["country"], user["postal_code"], user["phone"], user["date"])
        if is_vaccinated:
          asyncio.get_event_loop().run_until_complete(controller.change_booking_state(user["_id"], False))
          asyncio.get_event_loop().run_until_complete(controller.update_status(user["_id"], is_vaccinated))
          asyncio.get_event_loop().run_until_complete(bot.send_message(
              user["_id"], "Ho notato che hai già effettuato una prenotazione perciò non controllerò le date per te.\n\nSe dovessi annullare la prenotazione e volessi essere notificato ancora digita /reset\n\nSe vuoi cancellare i tuoi dati digita /cancella"))
          continue
        still_available = check(driver, booking)
        if still_available:
          asyncio.get_event_loop().run_until_complete(bot.send_message(
              user["_id"], "Invia il comando /codice per procedere con l'inserimento del codice."))
          result = book(driver, booking["_id"])
          # if result = -2
          result_message = "Il codice che hai fornito non è corretto o è scaduto, oppure l'appuntamento non è più disponibile."
          if result == 0:
            result_message = "Prenotazione effettuata con successo. Riceverai un SMS di conferma."
          elif result == -1:
            result_message = "Non hai fornito un codice in tempo (attesa massima 2 minuti)."
          asyncio.get_event_loop().run_until_complete(bot.send_message(user["_id"], result_message))
        else:
          asyncio.get_event_loop().run_until_complete(bot.send_message(user["_id"], "L'appuntamento che volevi prenotare non è più disponibile."))
        asyncio.get_event_loop().run_until_complete(controller.change_booking_state(user["_id"], False))
        driver.delete_all_cookies()
      time.sleep(30)
    except Exception as e:
      asyncio.get_event_loop().run_until_complete(controller.change_booking_state(user["_id"], False))
      driver.delete_all_cookies()
      LOGGER.exception(e)
      if "Sessione scaduta" in driver.page_source:
        LOGGER.info("IP bannato")
        time.sleep(60 * 60)
      time.sleep(60 * 5)
