import pytest
from pyband.proto.cosmos.base.abci.v1beta1 import TxResponse
from pyband.proto.tendermint.abci import Event, EventAttribute

from vrf_worker.band.utils import find_request_id


@pytest.fixture
def mock_request_resp():
    events = [
        Event(
            type="message",
            attributes=[EventAttribute(key="action", value="/oracle.v1.MsgRequestData")],
        ),
        Event(
            type="raw_request",
            attributes=[
                EventAttribute(key="data_source_id", value="84"),
                EventAttribute(
                    key="data_source_hash",
                    value="d7a32a142d016fa51b979051b56a83759a7c5afb838e260594ba17c0a70f6621",
                ),
                EventAttribute(key="external_id", value="1"),
                EventAttribute(
                    key="calldata",
                    value="61c602247721b14eac135379ed5e43d73d499101fd15fda55006633b339b78ee 1665454656",
                ),
                EventAttribute(key="fee", value="0"),
            ],
        ),
        Event(
            type="request",
            attributes=[
                EventAttribute(key="id", value="628823"),
                EventAttribute(key="client_id", value="vrf_worker"),
                EventAttribute(key="oracle_script_id", value="152"),
                EventAttribute(
                    key="calldata",
                    value="0000002061c602247721b14eac135379ed5e43d73d499101fd15fda55006633b339b78ee000000006344d24000000014ff1514e5a4e71702e4390cd160c33f30b529f881",
                ),
                EventAttribute(key="ask_count", value="16"),
                EventAttribute(key="min_count", value="10"),
                EventAttribute(key="gas_used", value="26019"),
                EventAttribute(key="total_fees", value="0"),
                EventAttribute(
                    key="validator",
                    value="bandvaloper1ym02hqj8e2c8qlw250zsjdjmvr5zfj5jz92w3v",
                ),
                EventAttribute(
                    key="validator",
                    value="bandvaloper132sxwpky0ptqtckgv9hnyqmd78t3xnyrg6w9hg",
                ),
                EventAttribute(
                    key="validator",
                    value="bandvaloper17v4tlepulhfvsr37lja4sf0alla582qazjrjm9",
                ),
                EventAttribute(
                    key="validator",
                    value="bandvaloper14plrcrdtphtzvqfyewcpztnuxgwukqad9mtwtv",
                ),
                EventAttribute(
                    key="validator",
                    value="bandvaloper1e6q8nskt5undr02ngq23atcu3mgvhxjpt0mwsu",
                ),
                EventAttribute(
                    key="validator",
                    value="bandvaloper16nzl5wrqwltvyhjefse0f4lyk9hp25mfqvkqx6",
                ),
                EventAttribute(
                    key="validator",
                    value="bandvaloper16mp6ey8ljqgtjxv93mwxu3ucfdnprt92z6hexh",
                ),
                EventAttribute(
                    key="validator",
                    value="bandvaloper1kfj48adjsnrgu83lau6wc646q2uf65rf84tzus",
                ),
                EventAttribute(
                    key="validator",
                    value="bandvaloper1yqlcv0azkvp2qal4zxcranfpxzq8rvs9gcfwhg",
                ),
                EventAttribute(
                    key="validator",
                    value="bandvaloper1lylssnp38wcxke592d7ethzzr4av273yu5xy3u",
                ),
                EventAttribute(
                    key="validator",
                    value="bandvaloper1xwrry9srz20qffrsnukw5zrnd4l2unzu9u766n",
                ),
                EventAttribute(
                    key="validator",
                    value="bandvaloper1uhvf525vsz0kqs757m744netzs6jkgm67e8wuk",
                ),
                EventAttribute(
                    key="validator",
                    value="bandvaloper1kxqs9pguxj2awqfl6r837e8kd5affw9gffxz0h",
                ),
                EventAttribute(
                    key="validator",
                    value="bandvaloper1d8265yjy7zlnxy0q49kpr0x0xf8mc9etc73lta",
                ),
                EventAttribute(
                    key="validator",
                    value="bandvaloper1d3z2x5kkppps6gcfy54m9qyjc4z7rydxaeex47",
                ),
                EventAttribute(
                    key="validator",
                    value="bandvaloper1hyjftngre6txc4hscty43yc4kay9zw9qp7h2sh",
                ),
            ],
        ),
    ]
    return TxResponse(events=events)


@pytest.fixture
def mock_action_resp():
    events = [
        Event(type="Action", attributes=[EventAttribute(key="action", value="")]),
    ]
    return TxResponse(events=events)


def test_find_request_id(mock_request_resp):
    assert find_request_id(mock_request_resp) == 628823


def test_find_request_id_fails(mock_action_resp):
    assert not find_request_id(mock_action_resp)
