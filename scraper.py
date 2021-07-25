import time
import asyncio
import logging
import controller as controller
from config import get_value
from aiogram import Bot
from aiogram.types import ParseMode
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select


LOGGER = logging.getLogger()


LOGIN_URL = "https://start.prenotazionevaccinicovid.regione.lombardia.it"
BOOKING_URL = "https://start.prenotazionevaccinicovid.regione.lombardia.it/cit/#/prenota"
SEARCH_URL = "https://start.prenotazionevaccinicovid.regione.lombardia.it/cit/#/ricerca"
FAKE_USER = "I codici inseriti non sono corretti o non corrispondono a persona appartenente a categoria oggetto della fase corrente del piano vaccinale."


def wait_until_present(driver, xpath=None, class_name=None, el_id=None, name=None, duration=5, frequency=0.01):
  if xpath:
    return WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.XPATH, xpath)))
  elif class_name:
    return WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.CLASS_NAME, class_name)))
  elif el_id:
    return WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.ID, el_id)))
  elif name:
    return WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.NAME, name)))


def switch_filter(driver, mode):
  wait_until_present(driver, el_id="sortSelect")
  driver.find_element_by_id("sortSelect").click()
  Select(driver.find_element_by_id("sortSelect")).select_by_visible_text(mode)
  time.sleep(1)
  try:
    overlay = driver.find_element_by_class_name("overlay")
    driver.execute_script("arguments[0].style.visibility='hidden'", overlay)
  except Exception:
    pass


def are_equal(old_appointment, new_appointment, short=False):
  if short:
    return (f"{old_appointment['date'][:5]} {old_appointment['date'][11:16]}" == new_appointment["date"] and old_appointment["place"].replace("CENTRO VACCINALE: ", "") == new_appointment["place"])
  else:
    return (time.strptime(old_appointment["date"], "%d/%m/%Y %H:%M:%S") == time.strptime(new_appointment["date"], "%d/%m/%Y %H:%M:%S") and old_appointment["place"] == new_appointment["place"])


def login(driver, username, password):
  driver.get(LOGIN_URL)
  try:
    time.sleep(1)
    driver.execute_script("document.getElementsByClassName('btn btn-primary btn-sm ng-star-inserted')[0].click()")
  except Exception:
    pass
  wait_until_present(driver, el_id="username")
  driver.find_element_by_id("username").send_keys(username)
  wait_until_present(driver, el_id="password")
  driver.find_element_by_id("password").send_keys(password)
  driver.execute_script("document.getElementById('privacy').click()")
  driver.execute_script("document.getElementsByClassName('btn btn-primary btn-icon')[0].click()")


def find(driver, region, country, postal_code, phone, date):
  try:
    wait_until_present(driver, el_id="bookingCode", duration=3)
    return True
  except Exception:
    pass
  wait_until_present(driver, el_id="birthDate")
  driver.find_element_by_id("birthDate").send_keys(date)
  driver.find_element_by_id("phoneNumber").send_keys(phone)
  try:
    overlay = driver.find_element_by_class_name("modelOverlay")
    driver.execute_script("arguments[0].style.visibility='hidden'", overlay)
  except Exception:
    pass
  driver.find_element_by_xpath("//select[@formcontrolname='provinceId']").click()
  Select(driver.find_element_by_xpath("//select[@formcontrolname='provinceId']")).select_by_visible_text(region)
  driver.find_element_by_xpath("//select[@formcontrolname='cityId']").click()
  Select(driver.find_element_by_xpath("//select[@formcontrolname='cityId']")).select_by_visible_text(country)
  driver.find_element_by_xpath("//select[@formcontrolname='postalCode']").click()
  Select(driver.find_element_by_xpath("//select[@formcontrolname='postalCode']")).select_by_visible_text(postal_code)
  driver.execute_script("document.getElementById('conditions').click()")
  driver.execute_script("document.getElementsByClassName('btn btn-primary btn-icon')[0].click()")
  return False


def check(driver):
  appointments_by_distance = []
  appointments_by_date = []
  # appointments by distance
  switch_filter(driver, "Distanza")
  appointments = driver.find_elements_by_class_name("text-wrap")
  for appointment in appointments:
    info = appointment.find_elements_by_tag_name("span")
    place = info[2].text.upper()
    date = f"{(info[0].text)[-10:]} {(info[1].text)[-5:]}:00"
    new_appointment = {"date": date, "place": place}
    appointments_by_distance.append(new_appointment)
  # appointments by date
  switch_filter(driver, "Data")
  appointments = driver.find_elements_by_class_name("text-wrap")
  for appointment in appointments:
    info = appointment.find_elements_by_tag_name("span")
    place = info[2].text.upper()
    date = f"{(info[0].text)[-10:]} {(info[1].text)[-5:]}:00"
    new_appointment = {"date": date, "place": place}
    appointments_by_date.append(new_appointment)
  return {"appointments_by_distance": appointments_by_distance, "appointments_by_date": appointments_by_date, "last_fetch": time.strftime("%d/%m/%Y %H:%M:%S", time.gmtime())}


def start_scraper():
  LOGGER.info("Starting scraper.")
  bot = Bot(get_value("token"))
  options = webdriver.firefox.options.Options()
  # options.headless = True
  driver = webdriver.Firefox(options=options)
  while True:
    try:
      users = controller.get_users()
      for user in users:
        if user["is_vaccinated"]:
          continue
        last_appointments_by_distance = user["appointments_by_distance"]
        last_appointments_by_date = user["appointments_by_date"]  # time.strptime(user["last_date"], "%d/%m/%Y")
        login(driver, user["health_card"], user["fiscal_code"])
        if FAKE_USER in driver.page_source:
          asyncio.get_event_loop().run_until_complete(controller.delete_user(user["_id"]))
          asyncio.get_event_loop().run_until_complete(bot.send_message(
              user["_id"], "Ho cancellato i dati che hai registrato perchè non sono corretti. Esegui /cancella e rieffettua la registrazione con /registra"))
        is_vaccinated = find(driver, user["region"], user["country"], user["postal_code"], user["phone"], user["date"])
        if is_vaccinated:
          asyncio.get_event_loop().run_until_complete(controller.update_status(user["_id"], is_vaccinated))
          asyncio.run(bot.send_message(
              user["_id"], "Ho notato che hai già effettuato una prenotazione perciò non controllerò le date per te.\n\nSe dovessi annullare la prenotazione e volessi essere notificato ancora digita /reset\n\nSe vuoi cancellare i tuoi dati digita /cancella"))
          continue
        result = check(driver)
        controller.update_appointments(user["_id"], result["appointments_by_distance"], result["appointments_by_date"], result["last_fetch"])
        appointments_by_distance_length = len(result["appointments_by_distance"])
        appointments_by_date_length = len(result["appointments_by_date"])
        if appointments_by_distance_length > 0 or appointments_by_date_length > 0:
          new_by_distance = ""
          if appointments_by_distance_length > 0:
            if len(last_appointments_by_distance) == 0 or not are_equal(last_appointments_by_distance[0], result["appointments_by_distance"][0]):
              new_by_distance = f"Nuovo appuntamento ordinato per distanza:\n{result['appointments_by_distance'][0]['date']}\n{result['appointments_by_distance'][0]['place']}\n\n"

          new_by_date = ""
          if appointments_by_date_length > 0:
            if len(last_appointments_by_date) == 0 or not are_equal(last_appointments_by_date[0], result["appointments_by_date"][0]):
              new_by_date = f"Nuovo appuntamento ordinato per data:\n{result['appointments_by_date'][0]['date']}\n{result['appointments_by_date'][0]['place']}\n\n"

          if new_by_distance != "" or new_by_date != "":
            asyncio.run(bot.send_message(
                user["_id"], f"{new_by_distance}{new_by_date}Per tutti gli appuntamenti disponibili digita /tutti e per prenotare digita /prenota oppure effettua la procedura manuale: {LOGIN_URL}\nUsername: <pre>{user['health_card']}</pre>\nPassword: <pre>{user['fiscal_code']}</pre>", parse_mode=ParseMode.HTML))
        driver.delete_all_cookies()
      active_users = controller.get_active_users()
      time.sleep(60 * int(15 / ((50 if active_users < 50 else active_users / 50))))
    except Exception as e:
      driver.delete_all_cookies()
      LOGGER.exception(e)
      if "Sessione scaduta" in driver.page_source:
        LOGGER.info("IP bannato")
        time.sleep(60 * 60)
      time.sleep(60 * 5)
