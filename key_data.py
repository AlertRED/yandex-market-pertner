from __future__ import print_function
import logging.config
from threading import Thread
import cachetools.func
from asyncio import sleep as asleep

import os.path
from typing import  List
from datetime import datetime
from pytz import timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from config import GOOGLE_TOKEN_FILE_NAME, GOOGLE_SPREADSHEET_ID

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

logger = logging.getLogger('google_sheets')
keys_count = {}


class KeysNotEnough(Exception):
    pass


@cachetools.func.ttl_cache(ttl=60)
def __get_creds():
    creds = None
    if os.path.exists(GOOGLE_TOKEN_FILE_NAME):
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_TOKEN_FILE_NAME,
        )
    return creds


@cachetools.func.ttl_cache(ttl=10)
def __get_skus_from_sheet() -> list:
    creds = __get_creds()
    headers_sku = {}
    try:
        service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(
                spreadsheetId=GOOGLE_SPREADSHEET_ID,
                range='keys!B2:2',
            )
            .execute()
        )
        values = result.get('values', [])
        if not values:
            logger.error('No data found.')
            return
        else:
            for i, value in enumerate(values[0]):
                if value:
                    headers_sku[value] = __get_column_letter(i + 2)
        return headers_sku
    except HttpError as err:
        logger.error(err)


def __update_keys_columns(data: list, column_name: str):
    creds = __get_creds()
    try:
        service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
        sheet = service.spreadsheets()
        response = (
            sheet.values()
            .update(
                spreadsheetId=GOOGLE_SPREADSHEET_ID,
                range=f'keys!{column_name}3:{column_name}',
                valueInputOption='USER_ENTERED',
                body={'values': [[i] for i in data]},
            )
            .execute()
        )
        logger.info(response)
    except HttpError as err:
        logger.error(err)


def __add_used_keys_columns(keys: List[str], sku: str):
    creds = __get_creds()
    try:
        service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
        sheet = service.spreadsheets()
        tz = timezone('Europe/Moscow')
        current_dt = datetime.now(tz).strftime('%Y-%m-%d %H:%M')
        response = (
            sheet.values()
            .append(
                spreadsheetId=GOOGLE_SPREADSHEET_ID,
                range='used_keys!A1:C1',
                valueInputOption='USER_ENTERED',
                body={'values': [(sku, key, current_dt) for key in keys]},
            )
            .execute()
        )
        logger.info(response)
    except HttpError as err:
        logger.error(err)


def __get_keys_from_product(column_name: str) -> list:
    creds = __get_creds()
    try:
        service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(
                spreadsheetId=GOOGLE_SPREADSHEET_ID,
                range=f'keys!{column_name}3:{column_name}',
            )
            .execute()
        )
        values = result.get('values', [])
        if not values:
            logger.error('No data found.')
            return
        else:
            return [value[0] for value in values if len(value)]
    except HttpError as err:
        logger.error(err)


def __get_column_letter(col_idx):
    letters = []
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx, 26)
        if remainder == 0:
            remainder = 26
            col_idx -= 1
        letters.append(chr(remainder + 64))
    return ''.join(reversed(letters))


def get_keys(sku: str, count: int = 1):
    headers = __get_skus_from_sheet()
    column_name = headers[sku]

    keys = __get_keys_from_product(column_name)
    if keys and len(keys) >= count:
        result = keys[-count:]
        __update_keys_columns(keys[:-count] + [''] * count, column_name)
        __add_used_keys_columns(result, sku)
        return result
    raise KeysNotEnough()


def __update_keys_count() -> None:
    sku_indexes = {}
    counter = {}
    creds = __get_creds()
    try:
        service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
        sheet = service.spreadsheets()
        response = (
            sheet.values()
            .get(
                spreadsheetId=GOOGLE_SPREADSHEET_ID,
                range='keys!B2:ZZ',
            )
            .execute()
        )
        values = response['values']
        # Collect SKU
        for i, product_sku in enumerate(values[0]):
            if product_sku:
                sku_indexes[i] = product_sku
                counter[product_sku] = 0

        # Counting keys
        for keys in values[1:]:
            for i, key in enumerate(keys):
                if key:
                    counter[sku_indexes[i]] += 1
        global keys_count
        keys_count = counter
    except HttpError as err:
        logger.error(err)


async def run_update_count_keys():
    while True:
        thread = Thread(target=__update_keys_count)
        thread.start()
        thread.join()
        await asleep(30)


def get_count_keys():
    return keys_count


if __name__ == '__main__':
    # Exampels
    creds = __get_creds()
    headers_sku = {}
    service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
    sheet = service.spreadsheets()
    a = sheet.sheets()
    a = 1

    # print(get_count_keys())
    # get_keys('240152903041', 2)
