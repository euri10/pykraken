import pykraken
from .exceptions import RequiredParameterError
from .convert import commasep, parseOTime


def kprivate_balance(client):
    c = client._post("/0/private/Balance")
    return c['result']


def kprivate_tradebalance(client, aclass='currency', asset='ZUSD'):
    params = {}
    if aclass:
        params['aclass'] = aclass
    if asset:
        params['asset'] = asset
    c = client._post("/0/private/TradeBalance", params)
    return c['result']


def kprivate_openorders(client, trades=False, userref=None):
    params = {}
    if trades:
        params['trades'] = trades
    if userref:
        params['userref'] = userref
    c = client._post("/0/private/OpenOrders", params)
    return c['result']


def kprivate_closedorders(client, trades=False, userref=None, start=None, end=None, ofs=None, closetime='both'):
    params = {}
    if trades:
        params['trades'] = trades
    if userref:
        params['userref'] = userref
    if start:
        params['start'] = start
    if end:
        params['end'] = end
    if ofs:
        params['ofs'] = ofs
    if closetime:
        params['closetime'] = closetime

    c = client._post("/0/private/ClosedOrders", params)
    return c['result']


def kprivate_queryorders(client, trades=False, userref=None, txid=None):
    params = {}
    if trades:
        params['trades'] = trades
    if userref:
        params['userref'] = userref
    if txid:
        params['txid'] = commasep(txid)

    c = client._post("/0/private/QueryOrders", params)
    return c['result']


def kprivate_tradeshistory(client, typet=None, trades=False, start=None, end=None, ofs=None):
    params = {}
    if typet and typet in ['all', 'any position', 'closed position', 'closing position', 'no position']:
        # using typet variable as type is reserved, but it need to be type in the params dictionnary
        params['type'] = typet
    if trades:
        params['trades'] = trades
    if start:
        params['start'] = start
    if end:
        params['end'] = end
    if ofs:
        params['ofs'] = ofs

    c = client._post("/0/private/TradesHistory", params)
    return c['result']


def kprivate_querytrades(client, txid=None, trades=False):
    params = {}
    if txid and len(txid) <= 20 and isinstance(txid, list):
        params['txid'] = commasep(txid)
    else:
        raise pykraken.exceptions.RequiredParameterError('no txid found')
    if trades:
        params['trades'] = trades
    c = client._post("/0/private/QueryTrades", params)
    return c['result']


def kprivate_openpositions(client, txid=None, docalcs=False):
    params = {}
    if txid and isinstance(txid, list):
        params['txid'] = commasep(txid)
    if docalcs:
        params['docalcs'] = docalcs

    c = client._post("/0/private/OpenPositions", params)
    return c['result']


def kprivate_ledgers(client, aclass='currency', asset='all', typet='all', start=None, end=None, ofs=None):
    params = {}
    if aclass:
        params['aclass'] = aclass
    if asset:
        params['asset'] = asset
    if typet:
        params['type'] = typet
    if start:
        params['start'] = start
    if end:
        params['end'] = end
    if ofs:
        params['ofs'] = ofs

    c = client._post("/0/private/Ledgers")
    return c['result']


def kprivate_queryledgers(client, id=None):
    params = {}
    if id and len(id) <= 20 and isinstance(id, list):
        params['id'] = commasep(id)
    else:
        raise pykraken.exceptions.BadParamterError('error in ids')
    c = client._post("/0/private/QueryLedgers", params)
    return c['result']


def kprivate_tradevolume(client, pair=None, feeinfo=None):
    params = {}
    if pair:
        params['pair'] = commasep(pair)
    if feeinfo:
        params['fee-info'] = feeinfo

    c = client._post("/0/private/TradeVolume")
    return c['result']


ORDER_TYPES_0 = ['market']
ORDER_TYPES_1 = ['limit', 'stop-loss', 'take-profit', 'trailing-stop']
ORDER_TYPES_2 = ['stop-loss-profit', 'stop-loss-profit-limit', 'stop-loss-limit', 'take-profit-limit',
                 'trailing-stop-limit', 'stop-loss-and-limit']
ORDER_FLAGS = ['viqc', 'fcib', 'fciq', 'nompp', 'post']


def kprivate_addorder(client, pair=None, typeo=None, ordertype=None, price=None, price2=None, volume=None,
                      leverage=None, oflags=None,
                      starttm=None, expiretm=None, userref=None, validate=None):
    params = {}
    if pair:
        params['pair'] = pair
    else:
        raise RequiredParameterError('pair')
    if typeo and typeo in ['buy', 'sell']:
        params['type'] = typeo
    else:
        raise RequiredParameterError('typeo')
    if ordertype and ordertype in (ORDER_TYPES_0 + ORDER_TYPES_1 + ORDER_TYPES_2):
        params['ordertype'] = ordertype
    else:
        raise RequiredParameterError('ordertype')

    if ordertype in ORDER_TYPES_0:
        if price:
            raise pykraken.exceptions.BadParamterError('if price is set, ordertype cant be at market')
    elif ordertype in ORDER_TYPES_1:
        if price:
            params['price'] = price
        else:
            raise pykraken.exceptions.RequiredParameterError(
                'price required for this order type: {}'.format(ordertype))
    elif ordertype in ORDER_TYPES_2:
        if price and price2:
            params['price'] = price
            params['price2'] = price2
        else:
            raise pykraken.exceptions.RequiredParameterError(
                'price and price2 required for this order type: {}'.format(ordertype))
    else:
        raise pykraken.exceptions.BadParamterError(
            'ordertype: {} not allowed, it should be in {} or {} or {}'.format(ordertype, ORDER_TYPES_0, ORDER_TYPES_1,
                                                                               ORDER_TYPES_2))
    if volume:
        params['volume'] = volume
    else:
        raise pykraken.exceptions.RequiredParameterError('volume is required')

    if leverage:
        params['leverage'] = leverage

    if oflags:
        params['oflags'] = commasep(oflags)
    if starttm:
        params['starttm'] = parseOTime(starttm)
    if expiretm:
        params['expiretm'] = parseOTime(expiretm)
    if userref:
        params['userref'] = userref
    if validate:
        params['validate'] = validate

    c = client._post("/0/private/AddOrder", params)
    return c['result']


def kprivate_cancelorder(client, txid=None):
    params = {}
    if txid:
        params['txid'] = txid
    else:
        raise pykraken.exceptions.RequiredParameterError('transaction id required')

    c = client._post("/0/private/CancelOrder", params)
    return c['result']


def kprivate_depositmethods():
    pass

