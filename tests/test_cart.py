import json
from fastapi.testclient import TestClient
from jsonschema import validate
from jsonschema.exceptions import ValidationError, SchemaError

from main import app
from schemas.cart import schema as cart_schema


client = TestClient(app)


def test_cart_response_json_validate():
    with open('tests/assets/cart', 'r') as file:
        json_data = file.read()
    response = client.post('cart', json=json.loads(json_data))
    json_response = response.json()
    try:
        validate(json_response, cart_schema)
    except (ValidationError, SchemaError) as e:
        assert False, e
