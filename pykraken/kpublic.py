import pykraken
from .exceptions import BadParamterError
from .convert import commasep


def kpublic_time(client):
    """
    Returns the servers' time
    :param client: the client
    :return: a tuple (unixtime =  as unix timestamp, rfc1123 = as RFC 1123 time format)
    """
    c = client._post("/0/public/Time")
    return c['result']['unixtime'], c['result']['rfc1123']


def kpublic_assets(client, info='info', aclass=None, asset=None):
    """
    Returns array of asset names and their info
    :param client: the client
    :param info: info to retrieve (optional), 'info' by default (doc is weird about that, optionnal but only one option...)
    :param aclass: asset class (optional), 'currency' is the default (same weirdness in doc)
    :param asset: comma delimited list of assets to get info on (optional.  default = all for given asset class)
    :return: <asset_name> = asset name
                altname = alternate name
                aclass = asset class
                decimals = scaling decimal places for record keeping
                display_decimals = scaling decimal places for output display
    """
    params = {}
    if info:
        params['info'] = info
    if asset:
        params['asset'] = commasep(asset)
    if aclass:
        if aclass is not "currency":
            raise BadParamterError('aclass should be currency')
    c = client._post("/0/public/Assets", params)
    return c['result']


def kpublic_assetpairs(client, info='info', pair=None):
    """
    Returns an array of pair names and some info about it
    :param client: the client
    :param info: pinfo to retrieve (optional), 'info' by default (doc is weird about that, optionnal but only one option...)
    :param pair:  comma delimited list of asset pairs to get info on (optional.  default = all)
    :return: <pair_name> = pair name
        altname = alternate pair name
        aclass_base = asset class of base component
        base = asset id of base component
        aclass_quote = asset class of quote component
        quote = asset id of quote component
        lot = volume lot size
        pair_decimals = scaling decimal places for pair
        lot_decimals = scaling decimal places for volume
        lot_multiplier = amount to multiply lot volume by to get currency volume
        leverage_buy = array of leverage amounts available when buying
        leverage_sell = array of leverage amounts available when selling
        fees = fee schedule array in [volume, percent fee] tuples
        fees_maker = maker fee schedule array in [volume, percent fee] tuples (if on maker/taker)
        fee_volume_currency = volume discount currency
        margin_call = margin call level
        margin_stop = stop-out/liquidation margin level
    """
    params = {}
    if info not in ['info', 'leverage', 'fees', 'margin']:
        raise pykraken.exceptions.BadParamterError()
    else:
        params['info'] = info
    if pair:
        params['pair'] = commasep(pair)

    c = client._post("/0/public/AssetPairs", params)
    return c['result']


def kpublic_ticker(client, pair=None):
    """
    Returns an array of pair names and their ticker info
    :param client: the client
    :param pair: comma delimited list of asset pairs to get info on
    :return: <pair_name> = pair name
        a = ask array(<price>, <whole lot volume>, <lot volume>),
        b = bid array(<price>, <whole lot volume>, <lot volume>),
        c = last trade closed array(<price>, <lot volume>),
        v = volume array(<today>, <last 24 hours>),
        p = volume weighted average price array(<today>, <last 24 hours>),
        t = number of trades array(<today>, <last 24 hours>),
        l = low array(<today>, <last 24 hours>),
        h = high array(<today>, <last 24 hours>),
        o = today's opening price
    """
    params = {}
    if pair:
        params['pair'] = commasep(pair)
    else:
        raise pykraken.exceptions.BadParamterError()
    c = client._post("/0/public/Ticker", params)
    return c['result']


def kpublic_ohlc(client, pair=None, interval=1, since=None):
    """
    Returns array of pair name and OHLC data
    :param client: the client
    :param pair: asset pair to get OHLC data for
    :param interval: time frame interval in minutes (optional): 1 (default), 5, 15, 30, 60, 240, 1440, 10080, 21600
    :param since: return committed OHLC data since given id (optional.  exclusive)
    :return: <pair_name> = pair name
            array of array entries(<time>, <open>, <high>, <low>, <close>, <vwap>, <volume>, <count>)
            last = id to be used as since when polling for new, committed OHLC data
    """
    params = {}
    if pair:
        params['pair'] = commasep(pair)
    else:
        raise pykraken.exceptions.BadParamterError()
    if interval:
        params['interval'] = interval
    if since:
        params['since'] = since
    c = client._post("/0/public/OHLC", params)
    return c['result']


def kpublic_depth(client, pair=None, count=None):
    """
    Returns array of pair name and market depth
    :param client: the client
    :param pair: asset pair to get market depth for
    :param count: maximum number of asks/bids (optional)
    :return: <pair_name> = pair name
                asks = ask side array of array entries(<price>, <volume>, <timestamp>)
                bids = bid side array of array entries(<price>, <volume>, <timestamp>)
    """
    params = {}
    if pair:
        params['pair'] = commasep(pair)
    else:
        raise pykraken.exceptions.BadParamterError()
    if count:
        params['count'] = count

    c = client._post("/0/public/Depth", params)
    return c['result']


def kpublic_trades(client, pair=None, since=None):
    """
    Returns an array of pair name and recent trade data
    :param client: the client
    :param pair: asset pair to get trade data for
    :param since: return trade data since given id (optional.  exclusive)
    :return: <pair_name> = pair name
        array of array entries(<price>, <volume>, <time>, <buy/sell>, <market/limit>, <miscellaneous>)
        last = id to be used as since when polling for new trade data
    """
    params = {}
    if pair:
        params['pair'] = commasep(pair)
    else:
        raise pykraken.exceptions.BadParamterError()
    if since:
        params['count'] = since

    c = client._post("/0/public/Trades", params)
    return c['result']


def kpublic_spread(client, pair=None, since=None):
    """
    Returns array of pair name and recent spread data
    :param client: the client
    :param pair: asset pair to get spread data for
    :param since: return spread data since given id (optional.  inclusive)
    :return: <pair_name> = pair name
        array of array entries(<time>, <bid>, <ask>)
        last = id to be used as since when polling for new spread data
    """
    params = {}
    if pair:
        params['pair'] = commasep(pair)
    else:
        raise pykraken.exceptions.BadParamterError()
    if since:
        params['count'] = since

    c = client._post("/0/public/Spread", params)
    return c['result']
