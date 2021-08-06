import time
import asyncio
import logging
from aiogram import Bot
from aiogram.types import ParseMode
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from db import controller as controller
from utils.config import get_value


LOGGER = logging.getLogger()

# login url
LOGIN_URL = "https://start.prenotazionevaccinicovid.regione.lombardia.it"
# booked url
SEARCH_URL = "https://start.prenotazionevaccinicovid.regione.lombardia.it/cit/#/ricerca"
# fake user data error message
FAKE_USER = "I codici inseriti non sono corretti o non corrispondono a persona appartenente a categoria oggetto della fase corrente del piano vaccinale."


def wait_until_present(driver, xpath=None, class_name=None, el_id=None, name=None, duration=5, frequency=0.01):
  """Wait until element is present

  Args:
      driver: webdriver
      xpath (string): element xpath
      class_name (string): element class name
      el_id (string): element id
      name (string): element name attribute
      duration (int): number of seconds before timing out
      frequency (float): sleep interval between calls

  Raises:
      TimeoutException: timed out

  Returns:
      WebElement: element waited
  """
  if xpath:
    return WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.XPATH, xpath)))
  elif class_name:
    return WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.CLASS_NAME, class_name)))
  elif el_id:
    return WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.ID, el_id)))
  elif name:
    return WebDriverWait(driver, duration, frequency).until(EC.presence_of_element_located((By.NAME, name)))


def switch_filter(driver, mode):
  """Switch appointments sorting

  Args:
      driver: webdriver
      mode (string): sorting mode
  """
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
  """Check if two appointments are equal

  Args:
      old_appointment (dict): date and place of old appointment
      new_appointment (dict): date and place of new appointment
      short (boolean): False if appointments are reduced (see controller.get_appointments()) else True

  Returns:
      True: appointments are equal
      False: appointments are not equal
  """
  if short:
    return (f"{old_appointment['date'][:5]} {old_appointment['date'][11:16]}" == new_appointment["date"] and old_appointment["place"].replace("CENTRO VACCINALE: ", "") == new_appointment["place"])
  else:
    return (time.strptime(old_appointment["date"], "%d/%m/%Y %H:%M:%S") == time.strptime(new_appointment["date"], "%d/%m/%Y %H:%M:%S") and old_appointment["place"] == new_appointment["place"])


def login(driver, username, password):
  """Perform the login on the website

  Args:
      driver: webdriver
      username (string): health card code
      password (string): fiscal code
  """
  driver.get(LOGIN_URL)
  # try pressing a spam button that appears sometimes
  try:
    time.sleep(1)
    driver.execute_script("document.getElementsByClassName('btn btn-primary btn-sm ng-star-inserted')[0].click()")
  except Exception:
    pass
  # wait fields and fill them
  wait_until_present(driver, el_id="username")
  driver.find_element_by_id("username").send_keys(username)
  wait_until_present(driver, el_id="password")
  driver.find_element_by_id("password").send_keys(password)
  # click privacy checkbox
  driver.execute_script("document.getElementById('privacy').click()")
  # click login button
  driver.execute_script("document.getElementsByClassName('btn btn-primary btn-icon')[0].click()")


def remove_overlay(driver):
  try:
    wait_until_present(driver, class_name="modelOverlay", duration=3)
    overlay = driver.find_element_by_class_name("modelOverlay")
    driver.execute_script("arguments[0].style.visibility='hidden'", overlay)
  except Exception:
    pass


def find(driver, region, country, postal_code, phone, date):
  """Perform booking page filling

  Args:
      driver: webdriver
      region (string): region of residence
      country (string): country of residence
      postal_code (string): CAP of residence
      phone (string): phone number
      date (string): birthdate dd/mm/YYYY

  Returns:
      True: user has already booked an appointment
      False: filling done
  """
  # check if page content is different from booking page (e.g. element with bookingCode id)
  try:
    wait_until_present(driver, el_id="bookingCode", duration=3)
    return True
  except Exception:
    pass
  # wait fields and fill them
  wait_until_present(driver, el_id="birthDate")
  driver.find_element_by_id("birthDate").send_keys(date)
  driver.find_element_by_id("phoneNumber").send_keys(phone)
  # remove overlay that hides 'select' elements
  remove_overlay(driver)
  # TODO 4: above overlay can appear also after clicking on a 'select'
  # TODO 5: wait for 'select' elements to appear (useful when the website is slow)
  driver.find_element_by_xpath("//select[@formcontrolname='provinceId']").click()
  Select(driver.find_element_by_xpath("//select[@formcontrolname='provinceId']")).select_by_visible_text(region)
  remove_overlay(driver)
  driver.find_element_by_xpath("//select[@formcontrolname='cityId']").click()
  Select(driver.find_element_by_xpath("//select[@formcontrolname='cityId']")).select_by_visible_text(country)
  remove_overlay(driver)
  driver.find_element_by_xpath("//select[@formcontrolname='postalCode']").click()
  Select(driver.find_element_by_xpath("//select[@formcontrolname='postalCode']")).select_by_visible_text(postal_code)
  # click conditions checkbox
  driver.execute_script("document.getElementById('conditions').click()")
  # click search button
  driver.execute_script("document.getElementsByClassName('btn btn-primary btn-icon')[0].click()")
  return False


def check(driver):
  """Return dict with two list of appointments, one sorted by distance and one sorted by date, and the current time

  Args:
      driver: webdriver

  Returns:
      dict: dict with appointments_by_distance and appointments_by_date and last_fetch
  """
  # appointments by distance
  appointments_by_distance = []
  switch_filter(driver, "Distanza")
  appointments = driver.find_elements_by_class_name("text-wrap")
  for appointment in appointments:
    info = appointment.find_elements_by_tag_name("span")
    place = info[2].text.upper()
    date = f"{(info[0].text)[-10:]} {(info[1].text)[-5:]}:00"
    new_appointment = {"date": date, "place": place}
    appointments_by_distance.append(new_appointment)
  # appointments by date
  appointments_by_date = []
  switch_filter(driver, "Data")
  appointments = driver.find_elements_by_class_name("text-wrap")
  for appointment in appointments:
    info = appointment.find_elements_by_tag_name("span")
    place = info[2].text.upper()
    date = f"{(info[0].text)[-10:]} {(info[1].text)[-5:]}:00"
    new_appointment = {"date": date, "place": place}
    appointments_by_date.append(new_appointment)
  return {"appointments_by_distance": appointments_by_distance, "appointments_by_date": appointments_by_date, "last_fetch": time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())}


def scraping_process(driver, bot, user):
  """Perform scraping process for the user specified

  Args:
      driver: webdriver
      bot: telegram bot
      user (dict): user whose appointments are to be checked
  """
  # update is new flag
  controller.update_is_new(user["_id"], False)
  # skip user if is vaccinated or if its notifications are disabled
  # TODO: see TODO 1
  # TODO 2: add 'notifications' flag to user to differentiate vaccinated users and muted notifications users
  if user["is_vaccinated"]:
    # next user
    return
  # last fetched appointments
  last_appointments_by_distance = user["appointments_by_distance"]
  last_appointments_by_date = user["appointments_by_date"]
  # perform login
  login(driver, user["health_card"], user["fiscal_code"])
  # give the website the time to check if user data are fake
  time.sleep(3)
  # if user data are fake delete all its data and send him a notification
  if FAKE_USER in driver.page_source:
    asyncio.get_event_loop().run_until_complete(controller.delete_user(user["_id"]))
    asyncio.get_event_loop().run_until_complete(bot.send_message(
        user["_id"], "Ho cancellato i dati che hai registrato perchè non sono corretti. Rieffettua la registrazione con /registra"))
    return
  # perform booking page filling
  is_vaccinated = find(driver, user["region"], user["country"], user["postal_code"], user["phone"], user["date"])
  # booking page not filled because user has already booked an appointment
  if is_vaccinated:
    # set user is_vaccinated to True to stop checking for him and send him a notification
    asyncio.get_event_loop().run_until_complete(controller.update_status(user["_id"], is_vaccinated))
    asyncio.get_event_loop().run_until_complete(bot.send_message(
        user["_id"], "Ho notato che hai già effettuato una prenotazione perciò non controllerò le date per te.\n\nSe dovessi annullare la prenotazione e volessi essere notificato ancora digita /reset\n\nSe vuoi cancellare i tuoi dati digita /cancella"))
    # wait 30 seconds for next user
    time.sleep(30)
    return
  # get new appointments
  result = check(driver)
  # update user appointments and fetch date
  controller.update_appointments(user["_id"], result["appointments_by_distance"], result["appointments_by_date"], result["last_fetch"])
  # number of appointments
  appointments_by_distance_length = len(result["appointments_by_distance"])
  appointments_by_date_length = len(result["appointments_by_date"])
  # if appointments have been found
  if appointments_by_distance_length > 0 or appointments_by_date_length > 0:
    new_by_distance = ""
    # if appointments_by_distance have been found
    if appointments_by_distance_length > 0:
      # if user had no appointments_by_distance or first appointment of both old and new appointments is different
      # setup new_by_distance message
      if len(last_appointments_by_distance) == 0 or not are_equal(last_appointments_by_distance[0], result["appointments_by_distance"][0]):
        new_by_distance = f"Nuovo appuntamento ordinato per distanza:\n{result['appointments_by_distance'][0]['date']}\n{result['appointments_by_distance'][0]['place']}\n\n"

    new_by_date = ""
    # if appointments_by_date have been found
    if appointments_by_date_length > 0:
      # if user had no appointments_by_date or first appointment of both old and new appointments is different
      # setup new_by_distance message
      if len(last_appointments_by_date) == 0 or not are_equal(last_appointments_by_date[0], result["appointments_by_date"][0]):
        new_by_date = f"Nuovo appuntamento ordinato per data:\n{result['appointments_by_date'][0]['date']}\n{result['appointments_by_date'][0]['place']}\n\n"

    # if new first appointments have been found send a notification
    if new_by_distance != "" or new_by_date != "":
      LOGGER.info("New date message sent.")
      asyncio.get_event_loop().run_until_complete(bot.send_message(
          user["_id"], f"{new_by_distance}{new_by_date}Per tutti gli appuntamenti disponibili digita /disponibili e per prenotare digita /prenota oppure effettua la procedura manuale: {LOGIN_URL}\nUsername: <pre>{user['health_card']}</pre>\nPassword: <pre>{user['fiscal_code']}</pre>", parse_mode=ParseMode.HTML))
  # clear cookies and wait 30 seconds for next user
  driver.delete_all_cookies()
  time.sleep(30)


def sleep_with_check(driver, bot):
  """Check for new users and serve them while sleeping for a calculated amount of seconds based on active users number

  Args:
      driver: webdriver
      bot: telegram bot
  """
  # get active users count
  active_users = controller.get_active_users()
  # calculate sleep time after the loop through users is completed
  if active_users > 0:
    sleep_time = 60 * int(15 if active_users < 50 else (15 / (active_users / 50)))
    LOGGER.info(f"Sleep with check for {sleep_time} s")
    # check for new users every second of sleep
    for i in range(sleep_time):
      new_users = controller.get_new_users()
      for user in new_users:
        LOGGER.info("New user found while sleeping")
        # serve new user without waiting
        scraping_process(driver, bot, user)
      time.sleep(1)


def start_scraper():
  """Start scraper loop"""
  LOGGER.info("Starting scraper.")
  # bot instance
  bot = Bot(get_value("token"))
  # webdriver options
  options = webdriver.firefox.options.Options()
  options.headless = True
  # webdriver
  driver = webdriver.Firefox(options=options)
  # file initialization
  with open("new_users.txt", "w"):
    pass
  # loop
  while True:
    try:
      # get all users
      # TODO 1: should get only active users (e.g with is_vaccinated=False)
      users = controller.get_users()
      # loop through users
      for user in users:
        scraping_process(driver, bot, user)
      # sleep with check for new users
      sleep_with_check(driver, bot)
    except Exception as e:
      LOGGER.exception(e)
      try:
        # clear cookies
        driver.delete_all_cookies()
        # check for IP ban
        if "Sessione scaduta" in driver.page_source:
          LOGGER.info("IP banned")
          # wait 60 minutes but I think it's useless, need to change IP
          time.sleep(60 * 30)
      except Exception as e:
        LOGGER.exception(e)
      # wait 5 minutes
      time.sleep(60 * 5)
