import uuid
import aiohttp
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

import config


app = FastAPI()


@app.get('/products.yml')
async def pruducts_yml(request: Request):
    with open('./products.yml', 'r') as file:
        yml_data = file.read()
    return Response(content=yml_data, media_type="application/xml")


@app.post('/cart')
async def cart(request: Request):
    json_data = await request.json()

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
        _item['count'] = item['count']
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


@app.post('/order/status')
async def order_status(request: Request):
    STATUS_FOR_SEND_ORDER = 'PROCESSING'

    json_data = await request.json()
    status = json_data['order']['status']

    request_data = {'items': []}
    for item in json_data['order']['items']:
        for _ in range(item['count']):
            _item = {}
            _item['id'] = item['id']
            _item['code'] = str(uuid.uuid4())
            _item['slip'] = (
                f'Instruction for {item["id"]}'
            )
            _item['activate_till'] = (
                (datetime.today() + timedelta(weeks=2)).strftime('%Y-%m-%d')
            )
            request_data['items'].append(_item)

    if status == STATUS_FOR_SEND_ORDER:
        headers = {'Authorization': f'Bearer {config.MARKET_ACCESS_TOKEN}'}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(
                url=(
                    f'https://api.partner.market.yandex.ru'
                    f'/campaigns/{config.MARKET_CAMPAIGN_ID}'
                    f'/orders/{json_data["order"]["id"]}'
                    f'/deliverDigitalGoods'
                ),
                json=request_data,
            ) as resp:
                print(resp.status)
                print(await resp.text())
