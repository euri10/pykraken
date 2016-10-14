import pytest

from pykraken.client import Client
from pykraken.config import API_KEY, PRIVATE_KEY


@pytest.fixture()
def client():
    client = Client(key=API_KEY, private_key=PRIVATE_KEY)
    return client