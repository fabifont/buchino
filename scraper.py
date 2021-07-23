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
UNIX_EPOCH = time.strptime("01/01/1970", "%d/%m/%Y")


def wait_until_present(driver, xpath=None, class_name=None, el_id=None, name=None, duration=5, frequency=0.01):
  if xpath:
    return WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.XPATH, xpath)))
  elif class_name:
    return WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.CLASS_NAME, class_name)))
  elif el_id:
    return WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.ID, el_id)))
  elif name:
    return WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.NAME, name)))


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


def check(driver, last_date, last_place):
  wait_until_present(driver, el_id="sortSelect")
  driver.find_element_by_id("sortSelect").click()
  Select(driver.find_element_by_id("sortSelect")).select_by_visible_text("Distanza")
  time.sleep(1)
  try:
    overlay = driver.find_element_by_class_name("overlay")
    driver.execute_script("arguments[0].style.visibility='hidden'", overlay)
  except Exception:
    pass
  available_appointments = driver.find_elements_by_class_name("text-wrap")
  if len(available_appointments) > 0:
    info = available_appointments[0].find_elements_by_tag_name("span")
    place = info[2].text.upper()
    date = time.strptime((info[0].text)[-10:], "%d/%m/%Y")
    if last_date == UNIX_EPOCH or date != last_date or place != last_place:
      return {"date": date, "place": place}
    else:
      return None
  return None


def start_scraper():
  LOGGER.info("Starting scraper.")
  bot = Bot(get_value("token"))
  options = webdriver.firefox.options.Options()
  options.headless = True
  driver = webdriver.Firefox(options=options)
  while True:
    try:
      users = controller.get_users()
      for user in users:
        if user["is_vaccinated"]:
          continue
        last_date = time.strptime(user["last_date"], "%d/%m/%Y")
        login(driver, user["health_card"], user["fiscal_code"])
        is_vaccinated = find(driver, user["region"], user["country"], user["postal_code"], user["phone"], user["date"])
        if is_vaccinated:
          controller.update_status(user["_id"], is_vaccinated)
          asyncio.run(bot.send_message(
              user["_id"], "Ho notato che hai già effettuato una prenotazione perciò non controllerò le date per te.\n\nSe dovessi annullare la prenotazione e volessi essere notificato ancora digita /reset\n\nSe vuoi cancellare i tuoi dati digita /cancella"))
          continue
        result = check(driver, last_date, user["last_place"])
        if result is not None:
          controller.update_date_and_place(user["_id"], time.strftime("%d/%m/%Y", result["date"]), result["place"])
          asyncio.run(bot.send_message(
              user["_id"], f"{'Prima data disponibile (ordinata per distanza)' if last_date == UNIX_EPOCH else 'Nuova data (ordinata per distanza, se non è più recente della precedente significa che quella non è più disponibile)'}: {time.strftime('%d/%m/%Y', result['date'])}\nLuogo: {result['place']}\n\nPrenota ora: {LOGIN_URL}\nUsername: <pre>{user['health_card']}</pre>\nPassword: <pre>{user['fiscal_code']}</pre>", parse_mode=ParseMode.HTML))
        driver.delete_all_cookies()
      active_users = controller.get_active_users()
      time.sleep(60 * int(15 / ((50 if active_users < 50 else active_users / 50))))
    except Exception as e:
      driver.delete_all_cookies()
      LOGGER.error(e)
