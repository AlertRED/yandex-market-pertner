from hashlib import sha224
import logging
import asyncio
import datetime
import traceback
import requests
import subprocess
from config import add_config_meta, config
from codes import code_sender
from starlette.requests import Request
from fastapi import FastAPI, BackgroundTasks, status
from load_products import update_info_for_yandex

from utils import auth_required, catch_internal_error, get_products

app = FastAPI()
main_log = logging.getLogger('mainlog')
loop = asyncio.get_event_loop()
last_update_date_time = subprocess.run('stat -c %Y .git/FETCH_HEAD'.split(), capture_output=True)
try:
    dt = datetime.datetime.fromtimestamp(int(last_update_date_time.stdout[:-1]))
except ValueError:
    last_update_time = None
else:
    last_update_time = dt.strftime('%d-%m-%Y %H:%M:%S')


@app.get('/ping')
@catch_internal_error
async def ping():
    main_log.info('ping')
    return {
        'message': 'pong',
        'last_update': last_update_time,
    }


@asyncio.coroutine
def sync_yaml():
    SLEEP_TIME = 60
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.132 YaBrowser/22.3.1.922 Yowser/2.5 Safari/537.36',
    }
    with open(config.get('settings', 'store_filename'), 'r') as file:
        last_hash = sha224(file.readline().encode()).hexdigest()

    while True:
        main_log.info('Обновление yml файла.')
        url_yaml_products = config.get('settings', 'url_yaml_products')
        response = requests.get(url_yaml_products, headers=headers)
        if response.status_code == status.HTTP_200_OK:
            current_hash = sha224(response.text.encode()).hexdigest()
            if last_hash != current_hash:
                with open(config.get('settings', 'store_filename'), 'w') as file:
                    file.write(response.text)
                last_hash = current_hash
                main_log.info(f'Обнаружено изменение между данными. Файл обновлен.')
            else:
                main_log.info(f'Изменений не обнаружено.')
        else:
            main_log.info(f'Код ответа при загрузке файла: {response.status_code}')
            main_log.info(f'Содержание ответа: {response.text}')
        yield from asyncio.sleep(SLEEP_TIME)


@asyncio.coroutine
def send_products_to_yandex():
    SLEEP_TIME = 60
    last_hash = config.get('meta', 'last_hash_yaml')

    while True:
        try:
            main_log.info('Обновление товаров на площадке yandex.')
            with open(config.get('settings', 'store_filename'), 'r') as file:
                current_hash = sha224(file.readline().encode()).hexdigest()
            if current_hash != last_hash:
                main_log.info('Обнаружены изменения в файле. Идет загрузка...')
                last_hash = current_hash
                add_config_meta('last_hash_yaml', last_hash)
                update_info_for_yandex()
                main_log.info('Данные успешно загружены.')
            else:
                main_log.info('Изменений в файле не обнаружено.')
        except:
            main_log.critical(f'При обновлении товаров на yandex произошла ошибка.')
            main_log.critical(f'{traceback.print_exc()}')
        yield from asyncio.sleep(SLEEP_TIME)

task1 = loop.create_task(sync_yaml())
task2 = loop.create_task(send_products_to_yandex())


@app.post('/stocks')
@auth_required
@catch_internal_error
async def stocks(request: Request):
    main_log.info(f'Получен запрос синхронизации количества товара')
    data = await request.json()
    warehouse_id = data['warehouseId']
    dt = datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
    updated_at = dt.isoformat(timespec="seconds")
    skus = []
    products = get_products()
    unfounded_skus = []
    for sku in data['skus']:
        product = products.get(sku)
        if product:
            skus.append({
                    "sku": sku,
                    "warehouseId": warehouse_id,
                    'items': [{
                        'type': 'FIT',
                        'count': int(product['count']),
                        'updatedAt': str(updated_at),
                    }]}
            )
        else:
            unfounded_skus.append(sku)
    
    main_log.info(f'Найдено {len(data["skus"]) - len(unfounded_skus)} из {len(data["skus"])}')
    if len(unfounded_skus):
        main_log.info(f'Ненайдены следующие sku: {", ".join(str(sku) for sku in unfounded_skus)}')
    main_log.info(f'Данные собраны и отправлены')
    return { "skus": skus }
    
@app.post('/order/accept')
@auth_required
@catch_internal_error
async def order_accept(request: Request, background_tasks: BackgroundTasks):
    main_log.info(f'Получен запрос на подтверждение заказа')
    data = await request.json()
    main_log.info(f'Номер заказа: { data["order"]["id"] }')
    result = {
        'order':
        {
            'accepted': True,
            'id': str(data['order']['id']),
            'shipmentDate': datetime.datetime.now().strftime('%d-%m-%Y')
        }
    }
    order_id = data['order']['id']
    products = [
        {
            'id': item['shopSku'],
            'type': item['offerName'],
            'count': item['count'],
        }
        for item in data['order']['items']
    ]
    main_log.info(f'Данные из запроса успешно получены.')
    background_tasks.add_task(code_sender.send_code, products, order_id)
    main_log.info(f'Отправка кода запущена.')
    return result

    
@app.post('/order/status')
@auth_required
@catch_internal_error
async def cart(request: Request):
    return {}

@app.post('/cart')
@auth_required
@catch_internal_error
async def cart(request: Request):     
    main_log.info(f'Получен запрос на синхронизацию корзины')
    data = await request.json()
    request_items = data['cart']['items']
    items = []
    for item in request_items:
        items.append({
            'feedId': item['feedId'],
            'offerId': item['offerId'],
            'delivery': True,
            'count': 999,
            'sellerInn': config.get('keys', 'seller_inn'),
        })
    result =  {
        'cart': {
            'deliveryCurrency': 'RUR',
            'deliveryOptions':
            [
                {   
                    "id": "12345",
                    "price": 0,
                    'serviceName': 'Доставка на электронную почту',
                    'type': 'DIGITAL',
                    'dates':
                    {
                        'fromDate': datetime.datetime.now().strftime('%d-%m-%Y'),
                    },
                    'paymentMethods': [
                        "YANDEX",
                        "APPLE_PAY",
                        "GOOGLE_PAY",
                        "TINKOFF_CREDIT",
                        "TINKOFF_INSTALLMENTS",
                        "SBP"
                    ]
                },
            ],
            'items': items,
            'paymentMethods': [
                "YANDEX",
                "APPLE_PAY",
                "GOOGLE_PAY",
                "TINKOFF_CREDIT",
                "TINKOFF_INSTALLMENTS",
                "SBP"
            ]
        }
    }
    main_log.info(f'Ответ собран и отправлен')
    return result

