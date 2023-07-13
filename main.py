import aiohttp
from datetime import datetime
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


