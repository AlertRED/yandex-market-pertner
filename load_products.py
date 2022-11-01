from itertools import product
import logging
from pprint import pprint
import traceback
import requests
import json
from random import randint, randrange
import xmltodict
import asyncio
from utils import get_products

headers = {
    'Content-Type': 'application/json',
    'Authorization': 'OAuth oauth_token="y0_AgAAAABlleQxAAiG-gAAAADSeMeOmrrYpAYzSs2pg7igpl5UtP_XjOA", oauth_client_id="8e3957c94bdb4839847a86d9d0ddb84e"',
}
main_log = logging.getLogger('mainlog')


def __load_products(products):
    offers = []
    category = 'Онлайн-подписки и карты оплаты'
    for sku, product_info in products.items():
        offers.append({
            "offer":
            {
                "shopSku": sku,
                "name": product_info['name'],
                "description": product_info['description'],
                "vendorCode": product_info['vendorCode'],
                "category": category,
                "manufacturerCountries":
                [
                    "Россия"
                ],
                "urls":
                [
                    product_info['url']
                ],
                "pictures":
                [
                    product_info['picture'],
                ],
            }
        })

    data = {
        "offerMappingEntries": offers
    }

    response = requests.post(
        'https://api.partner.market.yandex.ru/v2/campaigns/41094984/offer-mapping-entries/updates.json',
        headers=headers,
        data=json.dumps(data).encode('utf-8')
    )


def __load_prices(products):
    offers = []
    for sku, product_info in products.items():
        offers.append({
            "id": sku,
            "price":
            {
                "currencyId": 'RUR' if product_info['currencyId'] == 'RUB' else product_info['currencyId'],
                "value": product_info['price'],
            }
        })
    data = {"offers": offers}

    response = requests.post(
        'https://api.partner.market.yandex.ru/v2/campaigns/41094984/offer-prices/updates.json',
        headers=headers,
        data=json.dumps(data).encode('utf-8')
    )


def update_info_for_yandex():
    try:
        products = get_products()
        __load_products(products)
        __load_prices(products)
    except:        
        main_log.critical(f'При загрузке информации товаров на yandex произошла ошибка.')
        main_log.critical(f'{traceback.print_exc()}')