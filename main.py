import logging
import datetime
import subprocess
from config import config
from codes import code_sender
from starlette.requests import Request
from fastapi import FastAPI, BackgroundTasks

from utils import auth_required, catch_internal_error, get_products

app = FastAPI()
main_log = logging.getLogger('mainlog')
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


@app.post('/stocks')
@auth_required
@catch_internal_error
async def stocks(request: Request):
    main_log.info(f'Получен запрос синхронизацию количества товара')
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

