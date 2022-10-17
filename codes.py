import json
import logging
import requests
import datetime
from time import sleep
from pathlib import Path
from pprint import pprint
from config import config
from asyncio import sleep as aisleep

main_log = logging.getLogger('mainlog')


TYPE_TO = {
    'PS': 'ps',
    'XBOX': 'xbox',
}


class CodesException(Exception):
    pass


class PipeBlocked(CodesException):
    pass


class Codes:
    """ Класс работы с файлом кодов
    """
    CODES_FOLDER_PATH = Path('').joinpath('codes')

    def __init__(self, codes_filename: str, codes_sended_filename: str) -> None:
        self.__blocked = False
        self.__codes_file_path = self.CODES_FOLDER_PATH.joinpath(
            codes_filename)
        self.__codes_sended_file_path = self.CODES_FOLDER_PATH.joinpath(
            codes_sended_filename)
        with open(self.__codes_file_path, 'r') as file:
            self.file_cache: list = file.read().splitlines(True)
        self.total_count_codes = len(self.file_cache)
        self.__count_getted = None

    async def next(self, count):
        while self.__blocked:
            await aisleep(1)
        if len(self.file_cache) == 0:
            raise StopIteration
        elif len(self.file_cache) - count < 0:
            raise CodesException(
                f'Недостаточно строк в файле. В файле {len(self.file_cache)}, требуется {count}')
        self.__blocked = True
        self.__count_getted = count
        return self.file_cache[:self.__count_getted]

    def delete(self):
        """ Удалить отработанный код
        """
        with open(self.__codes_sended_file_path, 'a') as file:
            file.write(''.join(self.file_cache[:self.__count_getted]))
        self.file_cache = self.file_cache[self.__count_getted:]
        with open(self.__codes_file_path, 'w') as file:
            file.writelines(self.file_cache)
        self.__count_getted = None
        self.__blocked = False

    def restore(self):
        """ Восстановить ключи
        """
        self.__count_getted = None
        self.__blocked = False


class CodeSender:
    URL = 'https://api.partner.market.yandex.ru/v2/campaigns/{compaign_id}/orders/{order_id}/deliverDigitalGoods.json'
    TRIES = 3
    DELAY_SEND_TIME = 2
    COMPAING_ID = config.get('keys', 'compaing_id')
    OAUTH_CLIENT_ID = config.get('keys', 'oauth_client_id')
    OAUTH_TOKEN = config.get('keys', 'oauth_token')

    def __init__(self, codes: dict) -> None:
        self.__codes = codes
        self.__headers = {
            'Authorization':
            f'OAuth oauth_token="{self.OAUTH_TOKEN}", oauth_client_id="{self.OAUTH_CLIENT_ID}"'
        }

    async def __collect_data(self, products: list) -> list:
        items = []
        for product in products:
            keys = await self.__codes[product['type']].next(product['count'])
            main_log.info(
                f'Собрано ({product["count"]}) ключей типа ({product["type"]})'
            )
            for key in keys:
                items.append({
                    'id': int(product['id']),
                    'code': key,
                    'slip': 'Используйте данный код вставив в поле ввода кода',
                    'activate_till': (datetime.datetime.now() + datetime.timedelta(days=7)).strftime('%d-%m-%Y'),
                })
        return items

    def __delete_used_keys(self, products):
        for product in products:
            main_log.info(
                f'Удалины использованые ключи ({product["type"]})')
            self.__codes[product['type']].delete()

    def __restore_keys(self, products):
        for product in products:
            main_log.info(f'Восстановлены ({product["type"]})')
            self.__codes[product['type']].restore()

    async def send_code(self, products: list, order_id: int) -> bool:
        """ Функция отправки кодов Яндекс Маркету
        """
        url = self.URL.format(compaign_id=self.COMPAING_ID, order_id=order_id)
        main_log.info(f'Ключи для отправки собраны.')
        main_log.info(f'Отправка ключей на {url}')
        items = await self.__collect_data(products)
        data = {'items': items}
        pprint(data)
        for retry_idx in range(1, self.TRIES + 1):
            response = requests.post(url, json=json.dumps(data), headers=self.__headers, )
            if response.status_code == 200:
                main_log.info(f'Ключи успешно отправлены.')
                self.__delete_used_keys()
                main_log.info(f'Ключи удалины.')
                return True
            else:
                main_log.warning(
                    f'Запрос завершился с кодом {response.status_code}. Попытка №{retry_idx}.')
                main_log.warning(
                    f'Описание ошибки: {response.text}.')
                sleep(self.DELAY_SEND_TIME)
        self.__restore_keys(products)
        return False


codes = {
    'Forza Horizon 5 - PS': Codes(
        codes_filename='ps_codes.txt',
        codes_sended_filename='ps_codes_sended.txt',
    ),
    'xbox': Codes(
        codes_filename='xbox_codes.txt',
        codes_sended_filename='xbox_codes_sended.txt',
    ),
}

code_sender = CodeSender(codes=codes)

if __name__ == '__main__':
    code_sender.send_code(
        products=[
            {'type': 'ps', 'count': 2, 'id': 1},
            {'type': 'xbox', 'count': 3, 'id': 2},
        ],
        order_id=1,
    )
