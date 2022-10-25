import pytest
from app.helpers import Helpers, AppEnvConfig, Web3Interactor, BandInteractor
from .mock_data import *


@pytest.fixture
def helpers():
    return Helpers(AppEnvConfig, Web3Interactor, BandInteractor)


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
