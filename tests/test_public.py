import time
import pykraken
import pytest
from pykraken.config import PROXY, API_KEY, PRIVATE_KEY


def test_no_api_key():
    with pytest.raises(Exception):
        client = pykraken.Client()

def test_server_time():
    client = pykraken.Client(API_KEY, PRIVATE_KEY, requests_kwargs=PROXY)
    utcnow = time.time()
    t = client.kpublic_time()
    # t_compare = datetime.strptime(t[1], '%a, %d %b %y %H:%M:%S +0000')
    t_compare = t[0]
    print("t_compare: {} utcnow: {}".format(t_compare, utcnow))
    delta = t_compare - utcnow
    assert abs(delta)<= 10

def test_assets_asset_parameter():
    client = pykraken.Client(API_KEY, PRIVATE_KEY, requests_kwargs=PROXY)
    t = client.kpublic_assets(asset=['XETH'])
    assert u'XETH' in t.keys()

def test_assets_aclass_parameter():
    with pytest.raises(pykraken.exceptions.BadParamterError):
        client = pykraken.Client(API_KEY, PRIVATE_KEY, requests_kwargs=PROXY)
        t = client.kpublic_assets(aclass='mouahahah bad parameter')

def test_assetpairs():
    client = pykraken.Client(API_KEY, PRIVATE_KEY, requests_kwargs=PROXY)
    t = client.kpublic_assetpairs()
    # TODO: find a better test
    assert 'XXBTZUSD' in t.keys()

def test_ticker():
    client = pykraken.Client(API_KEY, PRIVATE_KEY, requests_kwargs=PROXY)
    t = client.kpublic_ticker(pair=['XETHXXBT'])
    print(t)
    assert 'XETHXXBT' in t.keys()

def test_OHLC():
    client = pykraken.Client(API_KEY, PRIVATE_KEY, requests_kwargs=PROXY)
    t = client.kpublic_ohlc(pair=['XETHXXBT'])
    print(t)
    assert 'XETHXXBT' in t.keys()

def test_depth():
    client = pykraken.Client(API_KEY, PRIVATE_KEY, requests_kwargs=PROXY)
    t = client.kpublic_depth(pair=['XETHXXBT'])
    print(t)
    assert 'XETHXXBT' in t.keys()

def test_trades():
    client = pykraken.Client(API_KEY, PRIVATE_KEY, requests_kwargs=PROXY)
    t = client.kpublic_trades(pair=['XETHXXBT'])
    print(t)
    assert 'XETHXXBT' in t.keys()

def test_spread():
    client = pykraken.Client(API_KEY, PRIVATE_KEY, requests_kwargs=PROXY)
    t = client.kpublic_spread(pair=['XETHXXBT'])
    print(t)
    assert 'XETHXXBT' in t.keys()
