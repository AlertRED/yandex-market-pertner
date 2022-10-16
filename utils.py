import logging
import xmltodict
from config import config
from functools import wraps

main_log = logging.getLogger('mainlog')

def get_products():
    """ Вернуть товары магазина из yaml файла
    """
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

def auth_required(func):
    @wraps(func)
    async def check_auth(*args, **kwargs):
        auth_token = kwargs['request'].query_params.get('auth-token')
        if not auth_token == config.get('main', 'auth_token'):
            message_error = 'Токен авторизации не подходит.'
            main_log.warning(message_error)
            raise Exception(message_error)
        return await func(*args, **kwargs)
    return check_auth