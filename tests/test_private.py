import pytest

from pykraken.exceptions import RequiredParameterError



def test_balance(client):
    t = client.kprivate_balance()
    assert 'XXBT' in t.keys()


def test_trade_balance(client):
    t = client.kprivate_tradebalance()
    # print(t.keys())
    # ml should be in this list, dunno why on my account it's not, maybe because i don't have margin yet
    tbkeys = ['eb', 'tb', 'm', 'n', 'c', 'v', 'e', 'mf']
    tbbool = [k in t.keys() for k in tbkeys]
    assert all(tbbool)


def test_open_orders(client):
    t = client.kprivate_openorders(trades=False)
    assert 'open' in t.keys()


def test_closed_orders(client):
    t = client.kprivate_closedorders(trades=False)
    assert 'closed' in t.keys()


def test_tradesHistory_queryTrades(client):
    t = client.kprivate_tradeshistory(trades=False)
    assert 'count' in t.keys()
    txidexample = [list(t['trades'].keys())][0]
    t1 = client.kprivate_querytrades(txid=txidexample[:19])
    assert (txidexample[0] in t1.keys())


def test_openPositions(client):
    t = client.kprivate_openpositions()
    # TODO find a better test this one tests nothing
    assert type(t) == dict


def test_getLedgers_and_query(client):
    t = client.kprivate_ledgers()
    # TODO find a better test
    assert 'count' in t.keys()
    ledgeriidlist = [list(t['ledger'].keys())[0]]
    t1 = client.kprivate_queryledgers(id=ledgeriidlist)
    # TODO find a better test
    assert ledgeriidlist[0] in t1.keys()


def test_tradeVolume(client):
    t = client.kprivate_tradevolume()
    # TODO find a better test
    assert 'currency' in t.keys()


def test_order_required_pair(client):
    with pytest.raises(RequiredParameterError):
        t = client.kprivate_addorder()


def test_addAndCancelOrder(client):
    # add validate=True just to enter false orders
    t = client.kprivate_addorder(pair='XETHZEUR', typeo='buy', ordertype='limit', price='+5.0', volume=0.01, validate=True)
    assert 'descr' in t.keys()
    # referral_tid = t['txid']
    # openorderidList = client.kprivate_openorders()
    # assert referral_tid in openorderidList['open'].keys()
    # cancel = client.kprivate_cancelorder(referral_tid)
    # assert 'count' in cancel.keys()
