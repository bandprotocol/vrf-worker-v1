import asyncio

from eth_account.signers.base import BaseAccount
from logbook import Logger
from pyband.wallet import Wallet

from vrf_worker.band.client import Client as BandClient
from vrf_worker.band.types import TxParams
from vrf_worker.band.utils import find_request_id
from vrf_worker.config import EvmConfig
from vrf_worker.consumer.evm.utils import trim_proof
from vrf_worker.types import Task

from .client import Client as EvmClient


class Worker:
    def __init__(
        self,
        evm_client: EvmClient,
        band_client: BandClient,
        evm_account: BaseAccount,
        band_wallet: Wallet,
        band_tx_params: TxParams,
        evm_config: EvmConfig,
        logger: Logger = Logger("vrf_worker", 11),
        poll_rate: int = 5,
        startup_nonce_check: int = 100,
        max_retries: int = 3,
    ) -> None:
        self.evm_client = evm_client
        self.band_client = band_client

        self.evm_account = evm_account
        self.band_wallet = band_wallet

        self.band_tx_params = band_tx_params
        self.evm_config = evm_config

        self.poll_rate = poll_rate
        self.startup_nonce_check = startup_nonce_check
        self.max_retries = max_retries

        self.logger = logger

    async def start(self) -> None:
        """Starts the worker."""
        self.logger.info("Starting worker")

        queue: asyncio.Queue[(int, Task, int)] = asyncio.Queue(10000)

        # get bandchain encoded chain id
        encoded_band_chain_id = self.evm_client.get_encoded_band_chain_id_from_bridge()

        # get oracle script id
        oracle_script_id = self.evm_client.get_oracle_script_id()

        # check latest nonce
        current_nonce = self.evm_client.get_current_task_nonce_from_vrf_provider()
        start_nonce = max(current_nonce - self.startup_nonce_check, self.evm_config.start_nonce)

        # poll the contract for new tasks every 5 seconds
        loop = asyncio.get_running_loop()
        loop.create_task(
            poll_tasks(self.evm_client, start_nonce, self.poll_rate, queue, self.evm_config.whitelisted_callers)
        )

        while True:
            (nonce, task, retry) = await queue.get()
            if retry >= self.max_retries:
                self.logger.error(f"Max retries reached for nonce {nonce}. Skipping task.")
                continue

            self.logger.info(f"Received task: {nonce}")

            # request VRF data on bandchain
            try:
                self.logger.info(f"Requesting VRF for nonce: {nonce}")
                tx_resp = await self.band_client.request_vrf(
                    oracle_script_id,
                    self.evm_account.address,
                    task.seed,
                    task.time,
                    self.band_tx_params,
                    self.band_wallet,
                )
                self.logger.info(f"Successfully requested VRF for nonce: {nonce}")
            except Exception as e:
                self.logger.error(f"Error requesting VRF for nonce {nonce}: {e}")
                await queue.put((nonce, task, retry + 1))
                continue

            try:
                if tx_resp.code != 0:
                    raise Exception(f"Transaction failed with code {tx_resp.code}: {tx_resp.raw_log}")
                tx_resp = await self.band_client.get_transaction(tx_resp.txhash)
            except Exception as e:
                self.logger.error(f"Error getting transaction for nonce {nonce}: {e}")
                await queue.put((nonce, task, retry + 1))
                continue

            request_id = find_request_id(tx_resp)
            self.logger.info(f"requested VRF with request_id {request_id}")
            if not request_id:
                self.logger.error(f"Request ID not found for nonce {nonce}. received tx with code: {tx_resp.code}")
                await queue.put((nonce, task, retry + 1))
                continue

            try:
                self.logger.info(f"Generating VRF proof for nonce {nonce}")
                (
                    evm_proof_bytes,
                    block_hash,
                ) = await self.band_client.get_evm_proof_and_block_hash(request_id)
                validators = self.evm_client.get_validators_from_bridge()
                trimmed_proof = trim_proof(evm_proof_bytes, block_hash, encoded_band_chain_id, validators)
                self.logger.info(f"Sucessfully generated VRF proof for nonce {nonce}")
            except Exception as e:
                self.logger.error(f"Error getting evm proof and block hash for nonce {nonce}: {e}")
                await queue.put((nonce, task, retry + 1))
                continue

            # relay proof
            try:
                self.logger.info(f"Relaying VRF proof for nonce: {nonce}")
                tx_hash = self.evm_client.relay_proof(
                    trimmed_proof,
                    nonce,
                    self.evm_account,
                    self.evm_config.eip1559,
                )
                status = self.evm_client.get_tx_receipt_status(tx_hash)
                if status == 1:
                    self.logger.info(f"Successfully relayed proof for nonce {nonce}")
                else:
                    self.logger.error(f"Failed to relay proof for nonce {nonce}")
                    await queue.put((nonce, task, retry + 1))
            except Exception as e:
                self.logger.error(f"Error relaying proof for nonce {nonce}: {e}")
                await queue.put((nonce, task, retry + 1))


async def poll_tasks(
    client: EvmClient,
    current_nonce: int,
    poll_rate: int,
    queue: asyncio.Queue[(int, Task)],
    whitelisted_callers: list[str],
) -> None:
    while True:
        await asyncio.sleep(poll_rate)
        latest_nonce = client.get_current_task_nonce_from_vrf_provider()
        if latest_nonce > current_nonce:
            nonces_to_check = list(range(current_nonce, latest_nonce))
            tasks = client.get_tasks_by_nonces(nonces_to_check)
            for nonce, task in zip(nonces_to_check, tasks):
                if not task.is_resolved and task.caller in whitelisted_callers:
                    await queue.put((nonce, task, 0))

            current_nonce = latest_nonce
