import time
import asyncio
import logging
import scraper as scraper
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
bookings = []


async def add_booking(_id, code):
  global bookings
  bookings.append({"_id": _id, "code": code})


def check(driver, last_date, last_place):
  scraper.wait_until_present(driver, el_id="sortSelect")
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
    # TODO: find appointment. if it doesn't exist anymore return None, else try to book with the provided code
    return None
  return None


def start_booker():
  LOGGER.info("Starting booker.")
  bot = Bot(get_value("token"))
  options = webdriver.firefox.options.Options()
  options.headless = True
  driver = webdriver.Firefox(options=options)
  while True:
    try:
      global bookings
      for booking in bookings:
        user = controller.get_user(booking["_id"])
        last_date = time.strptime(user["last_date"], "%d/%m/%Y")
        scraper.login(driver, user["health_card"], user["fiscal_code"])
        is_vaccinated = scraper.find(driver, user["region"], user["country"], user["postal_code"], user["phone"], user["date"])
        if is_vaccinated:
          controller.update_status(user["_id"], is_vaccinated)
          asyncio.run(bot.send_message(
              user["_id"], "Ho notato che hai già effettuato una prenotazione perciò non controllerò le date per te.\n\nSe dovessi annullare la prenotazione e volessi essere notificato ancora digita /reset\n\nSe vuoi cancellare i tuoi dati digita /cancella"))
          continue
        result = check(driver, last_date, user["last_place"])
        if result is not None:
          controller.update_status(user["_id"], True)
          asyncio.run(bot.send_message(user["_id"], f"{}")
          bookings.remove(booking)
        driver.delete_all_cookies()
    except Exception as e:
      driver.delete_all_cookies()
      LOGGER.error(str(e))
      LOGGER.error(repr(e))
