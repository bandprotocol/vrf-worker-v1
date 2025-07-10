import asyncio
import argparse
import sys

from eth_account import Account
from eth_account.account import LocalAccount
from logbook import StreamHandler
from omegaconf import OmegaConf
from pyband.wallet import Wallet

from vrf_worker.band.client import Client as BandClient
from vrf_worker.band.types import TxParams
from vrf_worker.consumer.evm.client import Client as EvmClient
from vrf_worker.consumer.evm.worker import Worker


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="VRF Worker")
    parser.add_argument(
        "--config", type=str, default="config.yaml", help="Path to the config file (default: config.yaml)"
    )
    args = parser.parse_args()

    # Load configuration
    try:
        config = OmegaConf.load(args.config)
    except FileNotFoundError:
        print(f"{args.config} not found")
        sys.exit(1)

    StreamHandler(sys.stdout).push_application()

    # initialize band
    band_client = BandClient(config.band_chain_config.grpc_endpoint)
    band_wallet = Wallet.from_mnemonic(config.band_chain_config.mnemonic)

    # initialize evm
    evm_client = EvmClient(
        config.evm_chain_config.rpc_endpoint,
        config.evm_chain_config.vrf_provider_address,
        config.evm_chain_config.vrf_lens_address,
        config.evm_chain_config.bridge_address,
    )
    evm_account: LocalAccount = Account.from_key(config.evm_chain_config.private_key)

    # initialize worker
    band_tx_params = TxParams(
        prepare_gas=config.band_chain_config.prepare_gas,
        execute_gas=config.band_chain_config.execute_gas,
        ds_fee_limit=config.band_chain_config.ds_fee_limit,
        ask_count=config.band_chain_config.ask_count,
        min_count=config.band_chain_config.min_count,
        gas_limit=config.band_chain_config.gas_limit,
        gas_price=config.band_chain_config.gas_price,
    )

    worker = Worker(
        evm_client=evm_client,
        band_client=band_client,
        evm_account=evm_account,
        band_wallet=band_wallet,
        band_tx_params=band_tx_params,
        evm_config=config.evm_chain_config,
    )

    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
