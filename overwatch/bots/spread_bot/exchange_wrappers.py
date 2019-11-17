import os

from wrappers.altilly import Altilly
from wrappers.bittrex import Bittrex
from wrappers.southxchange import SouthXchange


def get_wrapper(exchange):
    if exchange.lower() == 'southxchange':
        return SouthXchange(
            os.environ['API_KEY'],
            os.environ['API_SECRET'],
            os.environ['BASE_URL']
        )

    if exchange.lower() == 'bittrex':
        return Bittrex(
            os.environ['API_KEY'],
            os.environ['API_SECRET'],
            os.environ['BASE_URL']
        )

    if exchange.lower() == 'altilly':
        return Altilly(
            os.environ['API_KEY'],
            os.environ['API_SECRET'],
            os.environ['BASE_URL']
        )
