from __future__ import print_function

import os.path
from typing import Dict, List
from datetime import datetime
from pytz import timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from pprint import pprint
from config import GOOGLE_TOKEN_FILE_NAME, GOOGLE_SPREADSHEET_ID

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

headers = {}


def __get_creds():
    creds = None
    if os.path.exists(GOOGLE_TOKEN_FILE_NAME):
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_TOKEN_FILE_NAME,
        )
    return creds


def __get_skus_from_sheet() -> list:
    creds = __get_creds()
    headers_sku = {}
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(
                spreadsheetId=GOOGLE_SPREADSHEET_ID,
                range="keys!B2:ZZ2",
            )
            .execute()
        )
        values = result.get("values", [])
        if not values:
            print("No data found.")
            return
        else:
            for i, value in enumerate(values[0]):
                if value:
                    headers_sku[value] = __get_column_letter(i + 2)
        return headers_sku
    except HttpError as err:
        pprint(err)


def __update_keys_columns(data: list, column_name: str):
    creds = __get_creds()
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        response = (
            sheet.values()
            .update(
                spreadsheetId=GOOGLE_SPREADSHEET_ID,
                range=f"keys!{column_name}3:{column_name}999",
                valueInputOption="USER_ENTERED",
                body={"values": [[i] for i in data]},
            )
            .execute()
        )
        print(response)
    except HttpError as err:
        pprint(err)


def __add_used_keys_columns(keys: List[str], sku: str):
    creds = __get_creds()
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        tz = timezone("Europe/Moscow")
        current_dt = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
        response = (
            sheet.values()
            .append(
                spreadsheetId=GOOGLE_SPREADSHEET_ID,
                range="used_keys!A1:C1",
                valueInputOption="USER_ENTERED",
                body={"values": [(sku, key, current_dt) for key in keys]},
            )
            .execute()
        )
        print(response)
    except HttpError as err:
        pprint(err)


def __get_keys_from_product(column_name: str) -> list:
    creds = __get_creds()
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(
                spreadsheetId=GOOGLE_SPREADSHEET_ID,
                range=f"keys!{column_name}3:{column_name}999",
            )
            .execute()
        )
        values = result.get("values", [])
        if not values:
            print("No data found.")
            return
        else:
            return [value[0] for value in values if len(value)]
    except HttpError as err:
        pprint(err)


def __get_column_letter(col_idx):
    letters = []
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx, 26)
        if remainder == 0:
            remainder = 26
            col_idx -= 1
        letters.append(chr(remainder + 64))
    return "".join(reversed(letters))


def get_keys(sku: str, count: int = 1):
    headers = __get_skus_from_sheet()
    column_name = headers[sku]

    keys = __get_keys_from_product(column_name)
    if keys and len(keys) >= count:
        result = keys[-count:]
        __update_keys_columns(keys[:-count] + [""] * count, column_name)
        __add_used_keys_columns(result, sku)
        return result


def get_count_keys() -> Dict:
    sku_indexes = {}
    counter = {}
    creds = __get_creds()
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        response = (
            sheet.values()
            .get(
                spreadsheetId=GOOGLE_SPREADSHEET_ID,
                range="keys!B2:ZZ999",
            )
            .execute()
        )
        values = response["values"]
        for i, product_sku in enumerate(values[0]):
            if product_sku:
                sku_indexes[i] = product_sku
                counter[product_sku] = 0
        for keys in values[1:]:
            for i, key in enumerate(keys):
                if key:
                    counter[sku_indexes[i]] += 1
        return counter
    except HttpError as err:
        pprint(err)


if __name__ == "__main__":
    # Exampels
    print(get_count_keys())
    print(get_keys("240152903041", 2))
