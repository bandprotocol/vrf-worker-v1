from dataclasses import dataclass


@dataclass
class TxParams:
    min_count: int
    ask_count: int
    prepare_gas: int
    execute_gas: int
    ds_fee_limit: int
    gas_limit: int
    gas_price: float
