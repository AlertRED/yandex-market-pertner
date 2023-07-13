schema = {
    'type': 'object',
    'properties': {
        'cart': {
            'type': 'object',
            'properties': {
                'deliveryCurrency': {'type': 'string'},
                'deliveryOptions': {
                    'type': 'array',
                    'items': {
                        'properties': {
                            'price': {'type': 'number'},
                            'serviceName': {'type': 'string'},
                            'dates': {
                                'type': 'object',
                                'properties': {
                                    'toDate': {'type': 'string'},
                                    'fromDate': {'type': 'string'},
                                }
                            },
                        },
                        'required': [
                            'price',
                            'serviceName',
                            'dates',
                        ],
                        'additionalProperties': False,
                    },
                },
                'items': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'feedId': {'type': 'number'},
                            'offerId': {'type': 'string'},
                            'delivery': {'type': 'boolean'},
                            'count': {'type': 'number'},
                            'sellerInn': {'type': 'string'},
                        },
                        'required': [
                            'feedId',
                            'offerId',
                            'delivery',
                            'count',
                            'sellerInn',
                        ],
                        'additionalProperties': False,
                    },
                },
                'paymentMethods': {
                    'type': 'array',
                    'items': {
                        'type': 'string',
                    },
                },
            },
            'required': [
                'deliveryCurrency',
                'deliveryOptions',
                'items',
                'paymentMethods',
            ],
            'additionalProperties': False,
        },
    },
    'required': ['cart'],
    'additionalProperties': False,
}
