import os
import logging
import configparser
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

config = configparser.ConfigParser()
config.readfp(open(r'settings.ini'))

if not os.path.exists('./logs'):
    os.makedirs('./logs')

LOG_FORMAT = '[%(asctime)s][%(levelname)s][%(name)s][%(funcName)s]%(message)s'
DATE_FORMAT = '%d-%m-%Y %H:%M:%S'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=DATE_FORMAT)
formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

def main_logger():
    log_path = Path('logs').joinpath('logger.log')
    handler = TimedRotatingFileHandler(
        log_path, when='midnight', interval=1, encoding='utf-8'
    )
    handler.setFormatter(formatter)
    handler.suffix = "%Y-%m-%d.log"
    main_log = logging.getLogger('mainlog')
    main_log.addHandler(handler)

def uvicorn_logger():
    log_path = Path('logs').joinpath('uvicorn.log')
    handler = TimedRotatingFileHandler(
        log_path, when='midnight', interval=1, encoding='utf-8'
    )
    handler.setFormatter(formatter)
    handler.suffix = "%Y-%m-%d.log"
    uvicorn_log = logging.getLogger('uvicorn')
    uvicorn_log.addHandler(handler)

main_logger()
uvicorn_logger()