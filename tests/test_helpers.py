import pytest
from app.helpers import Helpers, AppEnvConfig, Abi
from .mock_data import *


@pytest.fixture
def helpers():
    return Helpers(AppEnvConfig, Abi)


def test_extract_request_id_from_request_tx(helpers):
    class Tx:
        def __init__(self):
            self.raw_log = mock_1["raw_log"]

    tx = Tx()
    result = helpers.extract_request_id_from_request_tx(tx)
    assert result == mock_1["output"]["request_id"]


def test_extract_request_id_from_request_tx_fails(helpers):
    class Tx:
        def __init__(self):
            self.raw_log = mock_2["raw_log"]

    tx = Tx()
    with pytest.raises(Exception) as e:
        helpers.extract_request_id_from_request_tx(tx)
    assert str(e.value) == "Cannot find request id"


def test_recover_addresses(helpers):
    result = helpers.recover_addresses(
        mock_3["arg"]["common"], mock_3["arg"]["signatures"], mock_3["arg"]["encoded_band_chain_id"]
    )
    assert result == mock_3["output"]["list_of_addr_and_sig"]
