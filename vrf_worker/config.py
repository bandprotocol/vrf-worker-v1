from dataclasses import dataclass
from typing import Literal


@dataclass
class BandConfig:
    grpc_endpoint: str
    mnemonic: str
    min_count: int = 2
    ask_count: int = 3
    prepare_gas: int = 100000
    execute_gas: int = 400000
    ds_fee_limit: int = 48
    gas_limit: int = 800000
    gas_price: float = 0.0025


@dataclass
class EvmConfig:
    chain_id: str
    rpc_endpoint: str
    vrf_provider_address: str
    vrf_lens_address: str
    bridge_address: str
    private_key: str
    start_nonce: int = 0
    eip1559: bool = True
    whitelisted_callers: list[str]


@dataclass
class Config:
    evm_chain_config: EvmConfig
    band_chain_config: BandConfig
