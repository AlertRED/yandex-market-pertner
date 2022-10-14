import os
from pprint import pprint
import time
import yaml
import logging
import datetime
import threading
import traceback
from pathlib import Path
from fastapi import FastAPI
from codes import code_sender
from starlette.requests import Request
from logging.handlers import TimedRotatingFileHandler
import xmltodict
from config import config

app = FastAPI()

if not os.path.exists('./logs'):
    os.makedirs('./logs')

LOG_FORMAT = '[%(asctime)s][%(levelname)s][%(name)s]%(message)s'
DATE_FORMAT = '%Y/%m/%d %H:%M:%S'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=DATE_FORMAT)
formatter = logging.Formatter(
    '[%(asctime)s][%(levelname)s][%(name)s]%(message)s', datefmt='%Y/%m/%d %H:%M:%S')

log_path = Path('logs').joinpath('logger.log')
logger = logging.getLogger('mainlog')
handler = TimedRotatingFileHandler(
    log_path, when='midnight', interval=1, encoding='utf-8')
handler.setFormatter(formatter)
handler.suffix = "%Y-%m-%d.log"
logger.addHandler(handler)


def send_code(products, order_id):
    time.sleep(config.get('main', 'delay_send_time'))
    code_sender.send_code(products, order_id)


def get_products():
    store_filename = config.get('main', 'store_filename')
    with open(store_filename) as file:
        xml_text = file.read()
    offers = xmltodict.parse(
        xml_text)['yml_catalog']['shop']['offers']['offer']
    products = {}

    for offer in offers:
        keys = list(offer.keys())
        keys.remove('@id')
        products[offer['@id']] = {key: offer[key] for key in keys}
    return products


@app.get('/ping')
async def ping():
    logger.info('pong')
    return {'message': 'pong'}


@app.post('/stocks')
async def stocks(request: Request):
    data = await request.json()
    warehouse_id = data['warehouseId']
    dt = datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
    updated_at = dt.isoformat(timespec="seconds")
    items = []
    products = get_products()
    for sku in data['skus']:
        product = products[sku]
        items.append({
            'type': 'FIT',
            'count': int(product['count']),
            'updatedAt': str(updated_at),
        })
    return {
        'skus':
        [{
            'sku': sku,
            'warehouseId': warehouse_id,
            'items': items
        }]
    }


@app.get('/cart')
async def cart(request: Request):
    data = await request.json()
    request_items = data['cart']['items']['feedId']
    items = []
    for item in request_items:
        items.append({
            'feedId': item['feedId'],
            'offerId': item['offerId'],
            'delivery': True,
            'count': 999,
            'sellerInn': config.get('main', 'seller_inn'),
        })

    return {
        'cart': {
            'deliveryCurrency': 'RUR',
            'deliveryOptions':
            [
                {
                    'id': '',  # можно не указывать?
                    'serviceName': 'Доставка на электронную почту',
                    'type': 'DIGITAL',
                    'dates':
                    {
                        'fromDate': datetime.datetime.now().strftime('%d-%m-%Y'),
                    },
                    'paymentMethods': [
                        'YANDEX',
                        'APPLE_PAY',
                    ]
                },
            ],
            'items': items,
            'paymentMethods': [
                'YANDEX',
                'APPLE_PAY',
            ]
        }
    }


@app.post('/order/accept')
async def order_accept(request: Request):
    try:
        data = await request.json()
        logging.info(
            f'Получен запрос на подтверждение заказа order_id: { data["order"]["id"] }')

        result = {
            'order':
            {
                'accepted': True,
                'id': data['order']['id'],
                'shipmentDate': datetime.datetime.now().strftime('%d-%m-%Y')
            }
        }

        order_id = data['order']['id']
        products = [
            {
                'id': item['id'],
                'type': item['type'],
                'count': item['count'],
            }
            for item in data['order']['items']
        ]

        logging.info(f'Данные из запроса успешно получены.')

        tread_send = threading.Thread(
            target=send_code, args=(products, order_id,))
        tread_send.start()
        tread_send.join()
        logging.info(f'Отправка кода запущена.')
    except:
        logging.critical(f'{traceback.print_exc()}')
        result = {
            'order':
            {
                'accepted': False,
            }
        }
    return result
