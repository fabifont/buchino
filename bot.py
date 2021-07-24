import numpy
import math
import controller as controller
import logging
from config import get_value
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor
from validation import validate_fiscal_code, validate_phone, decode_fiscal_code


WELCOME_STR = """
Questo bot ti notifica quando viene rilevata una data più recente per la prenotazione del vaccino.\n
Per iniziare il processo di registrazione dei dati necessari al controllo degli appuntamenti digita /registra\n
Per cancellare i tuoi dati registrati digita /cancella\n
Per vedere il resto dei comandi o avere informazioni sul sito ufficiale ed il gruppo di assistenza digita /info
"""


INFO_STR = """
Di seguito sono elencati i comandi che puoi utilizzare nel bot:
/start: avvia il bot (non la ricerca)
/registra: avvia il processo di registrazione
/annulla: annulla il processo di registrazione
/stop: termina la ricerca e disabilita le notifiche
/reset: abilita nuovamente le notifiche
/cancella: cancella tutti i tuoi dati
/info: stampa tutti i comandi ed informazioni aggiuntive\n
Se volessi segnalare un problema o contribuire allo sviluppo del bot visita la pagina ufficiale:
https://github.com/fabifont/buchino
oppure entra nel gruppo telegram dedicato:
https://t.me/assistenza_buchinobot
"""


LOGGER = logging.getLogger()
bot = Bot(get_value("token"))
dispatcher = Dispatcher(bot, storage=MemoryStorage())


class Form(StatesGroup):
  health_card = State()
  fiscal_code = State()
  phone = State()
  region = State()
  postal_code = State()
  country = State()


async def gen_markup(data, field, step):
  data = [elem[field] for elem in data]
  pool = numpy.array_split(data, math.ceil(len(data) / step))
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
  for elems in pool:
    markup.add(*elems)
  return markup


@dispatcher.message_handler(commands="start")
async def start(message: types.Message):
  await message.reply(WELCOME_STR)


@dispatcher.message_handler(commands="registra")
async def signup(message: types.Message):
  if await controller.check_user(message.chat.id):
    await message.reply("Sei già registrato.")
  else:
    await Form.health_card.set()
    await message.reply("Inserisci il numero della tessera sanitaria.")


@dispatcher.message_handler(state="*", commands="annulla")
async def cancel_handler(message: types.Message, state: FSMContext):
  current_state = await state.get_state()
  if current_state is None:
    return

  await state.finish()
  await message.reply("Annullato.", reply_markup=types.ReplyKeyboardRemove())


@dispatcher.message_handler(lambda message: not message.text.isdigit() or len(message.text) != 20, state=Form.health_card)
async def process_invalid_health_card(message: types.Message):
  await message.reply("Il numero della tessera sanitaria deve essere composto da 20 cifre!\nRiprova.")


@dispatcher.message_handler(state=Form.health_card)
async def process_health_card(message: types.Message, state: FSMContext):
  async with state.proxy() as data:
    data["health_card"] = message.text

  await Form.next()
  await message.reply("Inserisci il codice fiscale.")


@dispatcher.message_handler(lambda message: not validate_fiscal_code(message.text), state=Form.fiscal_code)
async def process_invalid_fiscal_code(message: types.Message):
  await message.reply("Il codice fiscale non è valido!\nRiprova.")


@dispatcher.message_handler(state=Form.fiscal_code)
async def process_fiscal_code(message: types.Message, state: FSMContext):
  async with state.proxy() as data:
    data["fiscal_code"] = message.text

  await Form.next()
  await message.reply("Inserisci il numero di telefono.")


@dispatcher.message_handler(lambda message: not validate_phone(message.text), state=Form.phone)
async def process_invalid_phone(message: types.Message):
  await message.reply("Il numero di telefono non è valido!\nAl momento sono accettati solo numeri italiani (con o senza prefisso +39)!\nRiprova.")


@dispatcher.message_handler(state=Form.phone)
async def process_phone(message: types.Message, state: FSMContext):
  async with state.proxy() as data:
    data["phone"] = message.text if "+" not in message.text else (message.text)[3:]

  await Form.next()

  markup = await gen_markup(await controller.get_regions(), "name", 3)

  await message.reply("Scegli la provincia.", reply_markup=markup)


@dispatcher.message_handler(lambda message: not controller.check_region(message.text), state=Form.region)
async def process_invalid_region(message: types.Message):
  await message.reply("La provincia scelta non è valida!\nRiprova.")


selected_region = None


@dispatcher.message_handler(state=Form.region)
async def process_region(message: types.Message, state: FSMContext):
  async with state.proxy() as data:
    data["region"] = message.text
    global selected_region
    selected_region = message.text

  await Form.next()

  markup = await gen_markup(await controller.get_postal_codes(message.text), "number", 3)

  await message.reply("Scegli il CAP.", reply_markup=markup)


@dispatcher.message_handler(lambda message: not controller.check_postal_code(selected_region, message.text), state=Form.postal_code)
async def process_invalid_postal_code(message: types.Message):
  await message.reply("Il CAP scelto non è valido!\nRiprova.")


@dispatcher.message_handler(state=Form.postal_code)
async def process_postal_code(message: types.Message, state: FSMContext):
  async with state.proxy() as data:
    data["postal_code"] = message.text

    markup = await gen_markup(await controller.get_countries(data["region"], message.text), "name", 3)

  await Form.next()

  await message.reply("Scegli il comune.", reply_markup=markup)


@dispatcher.message_handler(lambda message: not controller.check_country(selected_region, message.text), state=Form.country)
async def process_invalid_country(message: types.Message):
  await message.reply("Il comune scelto non è valido!\nRiprova.")


@dispatcher.message_handler(state=Form.country)
async def process_country(message: types.Message, state: FSMContext):
  async with state.proxy() as data:
    data["country"] = message.text

    markup = types.ReplyKeyboardRemove()

    user = await decode_fiscal_code(data["fiscal_code"])
    user["_id"] = message.chat.id
    user["health_card"] = data["health_card"]
    user["region"] = data["region"]
    user["country"] = data["country"]
    user["postal_code"] = data["postal_code"]
    user["phone"] = data["phone"]

    await controller.add_user(user)
    LOGGER.info("User registered")

    await bot.send_message(
        message.chat.id,
        f"L'utente è stato registrato con successo con i seguenti dati:\nid: <pre>{user['_id']}</pre>\ntessera sanitaria: <pre>{user['health_card']}</pre>\ncodice fiscale: <pre>{user['fiscal_code']}</pre>\ndata di nascita: <pre>{user['date']}</pre>\nprovincia: <pre>{user['region']}</pre>\ncomune: <pre>{user['country']}</pre>\ncap: <pre>{user['postal_code']}</pre>\ntelefono: <pre>{user['phone']}</pre>\n\nEntro 30 minuti riceverai la prima data disponibile ordinata per distanza.",
        reply_markup=markup,
        parse_mode=ParseMode.HTML
    )

  await state.finish()


@dispatcher.message_handler(commands="cancella")
async def delete(message: types.Message):
  if await controller.check_user(message.chat.id):
    await controller.delete_user(message.chat.id)
    LOGGER.info("User deleted.")
    await message.reply("I tuoi dati sono stati cancellati.")
  else:
    await message.reply("Non ci sono dati registrati.")


@dispatcher.message_handler(commands="reset")
async def reset(message: types.Message):
  if await controller.check_user(message.chat.id):
    if not await controller.get_status(message.chat.id):
      await message.reply("Le notifiche sono già abilitate.")
    else:
      await controller.update_status(message.chat.id, False)
      await message.reply("Le notifiche sono state riabilitate.")
  else:
    await message.reply("Non hai ancora registrato i tuoi dati.")


@dispatcher.message_handler(commands="stop")
async def stop(message: types.Message):
  if await controller.check_user(message.chat.id):
    if await controller.get_status(message.chat.id):
      await message.reply("Le notifiche sono già disabilitate.")
    else:
      await controller.update_status(message.chat.id, True)
      await message.reply("Le notifiche sono state disabilitate.")
  else:
    await message.reply("Non hai ancora registrato i tuoi dati.")


@dispatcher.message_handler(commands="info")
async def info(message: types.Message):
  await message.reply(INFO_STR)


def start_bot():
  LOGGER.info("Starting bot.")
  executor.start_polling(dispatcher, skip_updates=True)
