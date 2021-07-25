import logging
import mongoengine
import multiprocessing
import bot as bot
import scraper as scraper
import booker as booker


logging.basicConfig(filename="logfile.log",
                    filemode="w",
                    format="%(asctime)s [PID %(process)d] [Thread %(thread)d] [%(levelname)s] [%(name)s] %(message)s",
                    level=logging.INFO)


mongoengine.connect(host="mongodb://127.0.0.1:27017/buchino")


if __name__ == "__main__":
  multiprocessing.Process(target=scraper.start_scraper).start()
  multiprocessing.Process(target=booker.start_booker).start()
  bot.start_bot()
