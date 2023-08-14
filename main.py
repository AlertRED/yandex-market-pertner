import asyncio
import logging.config
import uvicorn
import aiohttp
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

import config
import key_data


app = FastAPI()
logger = logging.getLogger('yandex_market')
with open(config.FILE_SUPPORT_MESSAGE, 'r') as file:
    SUPPORT_MESSAGE = file.read()


@app.get('/products.yml')
async def pruducts_yml(request: Request):
    with open('./products.yml', 'r') as file:
        yml_data = file.read()
    return Response(content=yml_data, media_type="application/xml")


@app.post('/cart')
async def cart(request: Request):
    json_data = await request.json()
    count_products = key_data.get_count_keys()

    response = {'cart': {}}
    response['cart']['deliveryCurrency'] = 'RUR'

    delivery_option = {}
    delivery_option['type'] = 'DIGITAL'
    delivery_option['price'] = 0
    delivery_option['serviceName'] = 'Доставка на электронную почту'
    delivery_option['dates'] = {
        'fromDate': datetime.today().strftime('%d-%m-%Y'),
    }
    delivery_option['paymentMethods'] = [
        'YANDEX',
        'APPLE_PAY',
        'GOOGLE_PAY',
        'TINKOFF_CREDIT',
        'TINKOFF_INSTALLMENTS',
        'SBP',
    ]
    response['cart']['deliveryOptions'] = [delivery_option]

    response['cart']['items'] = []
    for item in json_data['cart']['items']:
        _item = {}
        _item['feedId'] = item['feedId']
        _item['offerId'] = item['offerId']
        _item['delivery'] = True
        _item['count'] = count_products.get(item['offerId'], 0)
        _item['sellerInn'] = config.MARKET_SELLER_INN
        response['cart']['items'].append(_item)

    response['cart']['paymentMethods'] = [
        'YANDEX',
        'APPLE_PAY',
        'GOOGLE_PAY',
        'TINKOFF_CREDIT',
        'TINKOFF_INSTALLMENTS',
        'SBP',
    ]

    return JSONResponse(response)


@app.post('/order/accept')
async def order_accept(request: Request):
    json_data = await request.json()

    response = {'order': {}}
    response['order']['accepted'] = True
    response['order']['id'] = json_data['order']['id']
    response['order']['shipmentDate'] = datetime.today().strftime('%d-%m-%Y')

    return JSONResponse(response)


@app.post('/order/status', status_code=status.HTTP_200_OK)
async def order_status(request: Request):
    STATUS_FOR_SEND_ORDER = 'PROCESSING'

    json_data = await request.json()
    status = json_data['order']['status']
    logger.info(f'Заказ {json_data["order"]["id"]} переведен в статус {status}')
    if status == STATUS_FOR_SEND_ORDER:
        request_data = {'items': []}
        for item in json_data['order']['items']:
            try:
                keys = key_data.get_keys(item['offerId'], item['count'])
            except key_data.KeysNotEnough:
                logger.info(
                    f'Заказ {json_data["order"]["id"]} '
                    f'недостаточно ключей для sku {item["offerId"]}'
                )
                await products_not_enough(json_data['order']['id'])
                return
            for key in keys:
                _item = {}
                _item['id'] = item['id']
                _item['code'] = key
                _item['slip'] = SUPPORT_MESSAGE
                _item['activate_till'] = (
                    (datetime.today() + timedelta(weeks=2)).strftime('%Y-%m-%d')
                )
                request_data['items'].append(_item)
        await send_key(json_data["order"]["id"], request_data)


async def send_key(order_id: str, request_data):
    headers = {'Authorization': f'Bearer {config.MARKET_ACCESS_TOKEN}'}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(
            url=(
                f'https://api.partner.market.yandex.ru'
                f'/campaigns/{config.MARKET_CAMPAIGN_ID}'
                f'/orders/{order_id}'
                f'/deliverDigitalGoods'
            ),
            json=request_data,
        ) as resp:
            info = {
                'status': resp.status,
                'text': await resp.text(),
            }
            logger.info(f'Заказ {order_id} ключ отправлен {info}')


async def products_not_enough(order_id):
    request_data = {
        'order': {
            'status': 'CANCELLED',
            'substatus': 'SHOP_FAILED',
        }
    }
    headers = {'Authorization': f'Bearer {config.MARKET_ACCESS_TOKEN}'}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.put(
            url=(
                f'https://api.partner.market.yandex.ru'
                f'/campaigns/{config.MARKET_CAMPAIGN_ID}'
                f'/orders/{order_id}'
                f'/status'
            ),
            json=request_data,
        ) as resp:
            info = {
                'status': resp.status,
            }
            logger.info(
                f'Заказ {order_id} отменен так как '
                f'его количество не достаточно {info}'
            )


@app.post('/stocks')
async def stocks(request: Request):
    ITEM_TYPE = 'FIT'
    count_products = key_data.get_count_keys()

    json_data = await request.json()
    response = {'skus': []}

    for sku_name in json_data['skus']:
        sku = {}
        sku['sku'] = sku_name
        sku['warehouseId'] = json_data['warehouseId']

        item = {}
        item['count'] = count_products.get(sku_name, 0)
        item['type'] = ITEM_TYPE
        item['updatedAt'] = (
            datetime.now().astimezone().replace(microsecond=0).isoformat()
        )
        sku['items'] = [item]
        response['skus'].append(sku)

    return JSONResponse(response)


@app.post('/order/cancellation/notify')
async def buyer_cancellation(request: Request):
    json_data = await request.json()
    request_data = {
        'accepted': False,
        'reason': 'ORDER_DELIVERED',
    }
    headers = {'Authorization': f'Bearer {config.MARKET_ACCESS_TOKEN}'}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.put(
            url=(
                f'https://api.partner.market.yandex.ru'
                f'/campaigns/{config.MARKET_CAMPAIGN_ID}'
                f'/orders/{json_data["order"]["id"]}'
                f'/cancellation/accept'
            ),
            json=request_data,
        ) as resp:
            info = {
                'status': resp.status,
                'text': await resp.text(),
            }
            logger.info(
                f'Заказ {json_data["order"]["id"]}'
                f'отмена заказа отменена {info}'
            )


@app.on_event("startup")
async def metrics_setup():
    asyncio.create_task(key_data.run_update_count_keys())

if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        host='127.0.0.1',
        port=8000,
        log_config='logging.yaml',
        reload=True,
    )
