import logging
import datetime
import traceback
from config import config
from codes import code_sender
from starlette.requests import Request
from fastapi import FastAPI, BackgroundTasks
from utils import auth_required, get_products

app = FastAPI()
main_log = logging.getLogger('mainlog')


@app.get('/ping')
async def ping():
    main_log.info(f'pong')
    return {'message': 'pong'}


@app.post('/stocks')
@auth_required
async def stocks(request: Request):
    main_log.info(f'Получен запрос синхронизацию количества товара')
    try:
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
    except:
        main_log.critical(f'{traceback.print_exc()}')
    
@app.post('/order/accept')
@auth_required
async def order_accept(request: Request, background_tasks: BackgroundTasks):
    main_log.info(f'Получен запрос на подтверждение заказа')
    try:
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
        background_tasks.add_task(await code_sender.send_code, products, order_id)
        main_log.info(f'Отправка кода запущена.')
        return result
    except:
        main_log.critical(f'{traceback.print_exc()}')
    
@app.post('/order/status')
@auth_required
async def cart(request: Request):
    return {}

if config.get('main', 'is_debug') != 'true':
    @app.post('/cart')
    @auth_required
    async def cart(request: Request):     
        main_log.info(f'Получен запрос на синхронизацию корзины')
        try:
            data = await request.json()
            request_items = data['cart']['items']
            items = []
            for item in request_items:
                items.append({
                    'feedId': item['feedId'],
                    'offerId': item['offerId'],
                    'delivery': True,
                    'count': 999,
                    'sellerInn': config.get('main', 'seller_inn'),
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
        except:
            main_log.critical(f'{traceback.print_exc()}')
else:
    @app.post('/cart')
    @auth_required
    async def cart(request: Request):
        data = await request.json()
        request_items = data['cart']['items']
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
            "cart":
            {
                "deliveryCurrency": "RUR",
                "deliveryOptions":
                [
                {
                    "price": 0,
                    "serviceName": "PickPoint",
                    "type": "PICKUP", 
                    "dates":
                    {
                    "fromDate": datetime.datetime.now().strftime('%d-%m-%Y'),
                    "toDate": datetime.datetime.now().strftime('%d-%m-%Y')
                    },
                    "outlets":
                    [
                        {
                            "code": "359959146"
                        },
                    ]
                },
                ],
                    "items": items,
                    "paymentMethods":
                [
                    "YANDEX",
                    "CARD_ON_DELIVERY",
                    "CASH_ON_DELIVERY",
                    "TINKOFF_CREDIT",
                    "TINKOFF_INSTALLMENTS",
                    "SBP"
                ]
            }
        }