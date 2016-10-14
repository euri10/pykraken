"""
Core client functionality, common across all API requests (including performing HTTP requests).
"""

import base64
import collections
from datetime import datetime
from datetime import timedelta
import hashlib
import hmac

import requests
import random
import time

import pykraken
from pykraken.convert import commasep, parseOTime
from .exceptions import _RetriableRequest, ApiError, RequiredParameterError, \
    BadParamterError

from urllib.parse import urlencode

_USER_AGENT = "pykraken {} (https://github.com/euri10/pykraken)".format(
    pykraken.__version__)
_DEFAULT_BASE_URL = "https://api.kraken.com"

_RETRIABLE_STATUSES = set([500, 503, 504])

ORDER_TYPES_0 = ['market']
ORDER_TYPES_1 = ['limit', 'stop-loss', 'take-profit', 'trailing-stop']
ORDER_TYPES_2 = ['stop-loss-profit', 'stop-loss-profit-limit',
                 'stop-loss-limit', 'take-profit-limit',
                 'trailing-stop-limit', 'stop-loss-and-limit']
ORDER_FLAGS = ['viqc', 'fcib', 'fciq', 'nompp', 'post']


class Client(object):
    """Performs requests to the kraken API."""

    def __init__(self, key=None, private_key=None, timeout=None,
                 connect_timeout=None, read_timeout=None,
                 retry_timeout=60, requests_kwargs=None,
                 queries_per_second=10):
        """
        :param key: API key.
        :type key: string

        :param timeout: Combined connect and read timeout for HTTP requests, in
            seconds. Specify "None" for no timeout.
        :type timeout: int

        :param connect_timeout: Connection timeout for HTTP requests, in
            seconds. You should specify read_timeout in addition to this option.
            Note that this requires requests >= 2.4.0.
        :type connect_timeout: int

        :param read_timeout: Read timeout for HTTP requests, in
            seconds. You should specify connect_timeout in addition to this
            option. Note that this requires requests >= 2.4.0.
        :type read_timeout: int

        :param retry_timeout: Timeout across multiple retriable requests, in
            seconds.
        :type retry_timeout: int

        :param queries_per_second: Number of queries per second permitted.
            If the rate limit is reached, the client will sleep for the
            appropriate amount of time before it runs the current query.
        :type queries_per_second: int

        :raises ValueError: when either credentials are missing, incomplete
            or invalid.
        :raises NotImplementedError: if connect_timeout and read_timeout are
            used with a version of requests prior to 2.4.0.

        :param requests_kwargs: Extra keyword arguments for the requests
            library, which among other things allow for proxy auth to be
            implemented. See the official requests docs for more info:
            http://docs.python-requests.org/en/latest/api/#main-interface
        :type requests_kwargs: dict

        """
        if not key:
            raise ValueError("Must provide API key when creating client.")

        self.key = key
        self.private_key = private_key

        if timeout and (connect_timeout or read_timeout):
            raise ValueError("Specify either timeout, or connect_timeout " +
                             "and read_timeout")

        if connect_timeout and read_timeout:
            # Check that the version of requests is >= 2.4.0
            chunks = requests.__version__.split(".")
            if chunks[0] < 2 or (chunks[0] == 2 and chunks[1] < 4):
                raise NotImplementedError("Connect/Read timeouts require "
                                          "requests v2.4.0 or higher")
            self.timeout = (connect_timeout, read_timeout)
        else:
            self.timeout = timeout

        self.retry_timeout = timedelta(seconds=retry_timeout)
        self.requests_kwargs = requests_kwargs or {}
        self.requests_kwargs.update({
            "headers": {"User-Agent": _USER_AGENT, "API-Key": self.key},
            "timeout": self.timeout,
            "verify": True,  # NOTE(cbro): verify SSL certs.
        })

        self.queries_per_second = queries_per_second
        self.sent_times = collections.deque("", queries_per_second)

    def _post(self, url, params={}, first_request_time=None, retry_counter=0,
              base_url=_DEFAULT_BASE_URL, accepts_clientid=True,
              extract_body=None, requests_kwargs=None):

        if not first_request_time:
            first_request_time = datetime.now()

        elapsed = datetime.now() - first_request_time
        if elapsed > self.retry_timeout:
            raise pykraken.exceptions.Timeout()

        if retry_counter > 0:
            # 0.5 * (1.5 ^ i) is an increased sleep time of 1.5x per iteration,
            # starting at 0.5s when retry_counter=0. The first retry will occur
            # at 1, so subtract that first.
            delay_seconds = 0.5 * 1.5 ** (retry_counter - 1)

            # Jitter this value by 50% and pause.
            time.sleep(delay_seconds * (random.random() + 0.5))

        # Unicode-objects must be encoded before hashing
        # "API-Sign = Message signature using HMAC-SHA512 of
        # (URI path + SHA256(nonce + POST data))
        # and base64 decoded secret API key"
        params['nonce'] = int(1000 * time.time())

        postdata = urlencode(params)

        # Unicode-objects must be encoded before hashing
        encoded = (str(params['nonce']) + postdata).encode()
        message = url.encode() + hashlib.sha256(encoded).digest()

        signature = hmac.new(base64.b64decode(self.private_key), message,
                             hashlib.sha512)
        sigdigest = base64.b64encode(signature.digest())

        self.requests_kwargs.update({
            "headers": {"User-Agent": _USER_AGENT, "API-Key": self.key,
                        "API-Sign": sigdigest.decode()},
            "timeout": self.timeout,
            "verify": True,  # NOTE(cbro): verify SSL certs.
        })

        # Default to the client-level self.requests_kwargs, with method-level
        # requests_kwargs arg overriding.
        requests_kwargs = dict(self.requests_kwargs, **(requests_kwargs or {}))
        try:
            resp = requests.post(base_url + url, data=params, **requests_kwargs)
        except requests.exceptions.Timeout:
            raise pykraken.exceptions.Timeout()
        except Exception as e:
            raise pykraken.exceptions.TransportError(e)

        if resp.status_code in _RETRIABLE_STATUSES:
            # Retry request.
            return self._post(url, params, first_request_time,
                              retry_counter + 1,
                              base_url, accepts_clientid, extract_body)

        # Check if the time of the nth previous query
        # (where n is queries_per_second)
        # is under a second ago - if so, sleep for the difference.
        if self.sent_times and len(self.sent_times) == self.queries_per_second:
            elapsed_since_earliest = time.time() - self.sent_times[0]
            if elapsed_since_earliest < 1:
                time.sleep(1 - elapsed_since_earliest)

        try:
            if extract_body:
                result = extract_body(resp)
            else:
                result = self._get_body(resp)
            self.sent_times.append(time.time())
            return result
        except _RetriableRequest:
            # Retry request.
            return self._post(url, params, first_request_time,
                              retry_counter + 1,
                              base_url, accepts_clientid, extract_body)

    def _get_body(self, resp):
        if resp.status_code != 200:
            raise pykraken.exceptions.HTTPError(resp.status_code)

        body = resp.json()

        if len(body["error"]):
            raise ApiError(resp.status_code, message=body["error"])
        else:
            return body

    def kprivate_balance(self):
        c = self._post("/0/private/Balance")
        return c['result']

    def kprivate_tradebalance(self, aclass='currency', asset='ZUSD'):
        params = {}
        if aclass:
            params['aclass'] = aclass
        if asset:
            params['asset'] = asset
        c = self._post("/0/private/TradeBalance", params)
        return c['result']

    def kprivate_openorders(self, trades=False, userref=None):
        params = {}
        if trades:
            params['trades'] = trades
        if userref:
            params['userref'] = userref
        c = self._post("/0/private/OpenOrders", params)
        return c['result']

    def kprivate_closedorders(self, trades=False, userref=None, start=None,
                              end=None, ofs=None, closetime='both'):
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

        c = self._post("/0/private/ClosedOrders", params)
        return c['result']

    def kprivate_queryorders(self, trades=False, userref=None, txid=None):
        params = {}
        if trades:
            params['trades'] = trades
        if userref:
            params['userref'] = userref
        if txid:
            params['txid'] = commasep(txid)

        c = self._post("/0/private/QueryOrders", params)
        return c['result']

    def kprivate_tradeshistory(self, typet=None, trades=False, start=None,
                               end=None, ofs=None):
        params = {}
        if typet and typet in ['all', 'any position', 'closed position',
                               'closing position', 'no position']:
            # using typet variable as type is reserved,
            # but it need to be type in the params dictionnary
            params['type'] = typet
        if trades:
            params['trades'] = trades
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        if ofs:
            params['ofs'] = ofs

        c = self._post("/0/private/TradesHistory", params)
        return c['result']

    def kprivate_querytrades(self, txid=None, trades=False):
        params = {}
        if txid and len(txid) <= 20 and isinstance(txid, list):
            params['txid'] = commasep(txid)
        else:
            raise pykraken.exceptions.RequiredParameterError('no txid found')
        if trades:
            params['trades'] = trades
        c = self._post("/0/private/QueryTrades", params)
        return c['result']

    def kprivate_openpositions(self, txid=None, docalcs=False):
        params = {}
        if txid and isinstance(txid, list):
            params['txid'] = commasep(txid)
        if docalcs:
            params['docalcs'] = docalcs

        c = self._post("/0/private/OpenPositions", params)
        return c['result']

    def kprivate_ledgers(self, aclass='currency', asset='all', typet='all',
                         start=None, end=None, ofs=None):
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

        c = self._post("/0/private/Ledgers")
        return c['result']

    def kprivate_queryledgers(self, id=None):
        params = {}
        if id and len(id) <= 20 and isinstance(id, list):
            params['id'] = commasep(id)
        else:
            raise pykraken.exceptions.BadParamterError('error in ids')
        c = self._post("/0/private/QueryLedgers", params)
        return c['result']

    def kprivate_tradevolume(self, pair=None, feeinfo=None):
        params = {}
        if pair:
            params['pair'] = commasep(pair)
        if feeinfo:
            params['fee-info'] = feeinfo

        c = self._post("/0/private/TradeVolume")
        return c['result']

    def kprivate_addorder(self, pair=None, typeo=None, ordertype=None,
                          price=None,
                          price2=None, volume=None,
                          leverage=None, oflags=None,
                          starttm=None, expiretm=None, userref=None,
                          validate=None):
        params = {}
        if pair:
            params['pair'] = pair
        else:
            raise RequiredParameterError('pair')
        if typeo and typeo in ['buy', 'sell']:
            params['type'] = typeo
        else:
            raise RequiredParameterError('typeo')
        if ordertype and ordertype in (
                        ORDER_TYPES_0 + ORDER_TYPES_1 + ORDER_TYPES_2):
            params['ordertype'] = ordertype
        else:
            raise RequiredParameterError('ordertype')

        if ordertype in ORDER_TYPES_0:
            if price:
                raise pykraken.exceptions.BadParamterError(
                    'if price is set, ordertype cant be at market')
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
                    'price and price2 required for this order type: {}'.format(
                        ordertype))
        else:
            raise pykraken.exceptions.BadParamterError(
                'ordertype: {} not allowed, it should be in {} or {} or {}'.format(
                    ordertype, ORDER_TYPES_0, ORDER_TYPES_1,
                    ORDER_TYPES_2))
        if volume:
            params['volume'] = volume
        else:
            raise pykraken.exceptions.RequiredParameterError(
                'volume is required')

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

        c = self._post("/0/private/AddOrder", params)
        return c['result']

    def kprivate_cancelorder(self, txid=None):
        params = {}
        if txid:
            params['txid'] = txid
        else:
            raise pykraken.exceptions.RequiredParameterError(
                'transaction id required')

        c = self._post("/0/private/CancelOrder", params)
        return c['result']

    def kprivate_depositmethods():
        pass

    def kpublic_time(self):
        """
        Returns the servers' time
        :param client: the client
        :return: a tuple (unixtime =  as unix timestamp, rfc1123 = as RFC 1123 time format)
        """
        c = self._post("/0/public/Time")
        return c['result']['unixtime'], c['result']['rfc1123']

    def kpublic_assets(self, info='info', aclass=None, asset=None):
        """
        Returns array of asset names and their info
        :param client: the client
        :param info: info to retrieve (optional), 'info' by default (doc is weird
        about that, optionnal but only one option...)
        :param aclass: asset class (optional), 'currency' is the default (same
        weirdness in doc)
        :param asset: comma delimited list of assets to get info on (optional.
        default = all for given asset class)
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
        c = self._post("/0/public/Assets", params)
        return c['result']

    def kpublic_assetpairs(self, info='info', pair=None):
        """
        Returns an array of pair names and some info about it
        :param client: the client
        :param info: pinfo to retrieve (optional), 'info' by default (doc is weird
        about that, optionnal but only one option...)
        :param pair:  comma delimited list of asset pairs to get info on (optional.
         default = all)
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
            fees_maker = maker fee schedule array in [volume, percent fee] tuples
            (if on maker/taker)
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

        c = self._post("/0/public/AssetPairs", params)
        return c['result']

    def kpublic_ticker(self, pair=None):
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
        c = self._post("/0/public/Ticker", params)
        return c['result']

    def kpublic_ohlc(self, pair=None, interval=1, since=None):
        """
        Returns array of pair name and OHLC data
        :param client: the client
        :param pair: asset pair to get OHLC data for
        :param interval: time frame interval in minutes (optional):
        1 (default), 5, 15, 30, 60, 240, 1440, 10080, 21600
        :param since: return committed OHLC data since given id (optional.
        exclusive)
        :return: <pair_name> = pair name
                array of array entries
                (<time>, <open>, <high>, <low>, <close>, <vwap>, <volume>, <count>)
                last = id to be used as since when polling for new,
                committed OHLC data
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
        c = self._post("/0/public/OHLC", params)
        return c['result']

    def kpublic_depth(self, pair=None, count=None):
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

        c = self._post("/0/public/Depth", params)
        return c['result']

    def kpublic_trades(self, pair=None, since=None):
        """
        Returns an array of pair name and recent trade data
        :param client: the client
        :param pair: asset pair to get trade data for
        :param since: return trade data since given id (optional.  exclusive)
        :return: <pair_name> = pair name
        array of array entries(<price>, <volume>, <time>, <buy/sell>,
        <market/limit>, <miscellaneous>)
            last = id to be used as since when polling for new trade data
        """
        params = {}
        if pair:
            params['pair'] = commasep(pair)
        else:
            raise pykraken.exceptions.BadParamterError()
        if since:
            params['count'] = since

        c = self._post("/0/public/Trades", params)
        return c['result']

    def kpublic_spread(self, pair=None, since=None):
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

        c = self._post("/0/public/Spread", params)
        return c['result']


def sign_hmac(secret, payload):
    """Returns a base64-encoded HMAC-SHA1 signature of a given string.

    :param secret: The key used for the signature, base64 encoded.
    :type secret: string

    :param payload: The payload to sign.
    :type payload: string

    :rtype: string
    """
    payload = payload.encode('ascii', 'strict')
    secret = secret.encode('ascii', 'strict')
    sig = hmac.new(base64.urlsafe_b64decode(secret), payload, hashlib.sha1)
    out = base64.urlsafe_b64encode(sig.digest())
    return out.decode('utf-8')

#
#
# def urlencode_params(params):
#     """URL encodes the parameters.
#
#     :param params: The parameters
#     :type params: list of key/value tuples.
#
#     :rtype: string
#     """
#     # urlencode does not handle unicode strings in Python 2.
#     # Firstly, normalize the values so they get encoded correctly.
#     params = [(key, normalize_for_urlencode(val)) for key, val in params]
#     # Secondly, unquote unreserved chars which are incorrectly quoted
#     # by urllib.urlencode, causing invalid auth signatures. See GH #72
#     # for more info.
#     return requests.utils.unquote_unreserved(urlencode(params))
#
#
# try:
#     unicode
#
#
#     # NOTE(cbro): `unicode` was removed in Python 3. In Python 3, NameError is
#     # raised here, and caught below.
#
#     def normalize_for_urlencode(value):
#         """(Python 2) Converts the value to a `str` (raw bytes)."""
#         if isinstance(value, unicode):
#             return value.encode('utf8')
#
#         if isinstance(value, str):
#             return value
#
#         return normalize_for_urlencode(str(value))
#
# except NameError:
#     def normalize_for_urlencode(value):
#         """(Python 3) No-op."""
#         # urlencode in Python 3 handles all the types we are passing it.
#         return value
