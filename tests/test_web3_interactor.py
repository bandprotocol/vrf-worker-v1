import pytest
from app.helpers import Web3Interactor, Abi
from .mock_data import *


@pytest.fixture
def web3_interactor():
    return Web3Interactor(MockEvmChainConfig, Abi)


def test_recover_addresses(web3_interactor):
    result = web3_interactor.recover_addresses(
        mock_3["arg"]["common"], mock_3["arg"]["signatures"], mock_3["arg"]["encoded_band_chain_id"]
    )
    assert result == mock_3["output"]["list_of_addr_and_sig"]
