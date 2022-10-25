from typing import Type
from pyband import Client
from pyband.wallet import PrivateKey
from pyband.transaction import Transaction
from pyband.obi import PyObi
from pyband.proto.cosmos.base.v1beta1 import Coin
from pyband.proto.cosmos.base.abci.v1beta1 import TxResponse
from pyband.messages.oracle.v1 import MsgRequestData
from pyband.transaction import Transaction
from .config import AppEnvConfig
from .database import Task


class BandInteractor:
    """This class contains methods that interact with the BandChain Client."""

    def __init__(self, _config: AppEnvConfig) -> None:
        self.config = _config

        # BandChain settings
        self.band_private_key = PrivateKey.from_mnemonic(self.config.BAND_MNEMONIC)
        self.band_public_key = self.band_private_key.to_public_key()
        self.band_requester_address = self.band_public_key.to_address()
        self.band_client = Client.from_endpoint(self.config.BAND_RPC[0], self.config.BAND_RPC_PORT)

    async def check_band_rpc(self) -> bool:
        """Checks if BandChain RPC endpoint is connected and working.

        Returns:
            bool: True if BandChain RPC endpoint is working, false otherwise
        """
        try:
            await self.band_client.get_latest_block()
            return True
        except Exception:
            return False

    async def set_band_client(self) -> None:
        """Sets the band_client variable to a working RPC endpoint.

        Checks if the current RPC endpoint is working. If it is not, try the
        RPC endpoints from the input list one by one until a working endpoint
        is set.

        Raises:
            Exception: No working RPC endpoint for BandChain found
        """
        try:
            if not await self.check_band_rpc():
                for rpc in self.config.BAND_RPC:
                    self.band_client = Client.from_endpoint(rpc, self.config.BAND_RPC_PORT)
                    if await self.check_band_rpc():
                        return

                raise Exception("No working RPC endpoints for BandChain")

        except Exception as e:
            print("Error set_band_client", e)
            raise

    async def get_request_tx_data(
        self, oracle_script_id: int, min_count: int, ask_count: int, task: Task, worker
    ) -> "Transaction":
        """Retrieves the BandChain transaction data.

        Args:
            oracle_script_id (int): Oracle Script ID.
            min_count (int): Min count.
            ask_count (int): Ask count.
            task (Task): Task.
            worker (_type_): Worker object.

        Returns:
            Transaction: Transaction data.
        """
        try:
            band_requester_address_bech32 = self.band_requester_address.to_acc_bech32()
            account = await self.band_client.get_account(band_requester_address_bech32)
            obi = PyObi("{seed:[u8],time:u64,worker_address:[u8]}/{proof:[u8],result:[u8]}")

            return (
                Transaction()
                .with_messages(
                    MsgRequestData(
                        oracle_script_id=oracle_script_id,
                        calldata=obi.encode(
                            {
                                "seed": list(bytes.fromhex(task.seed)),
                                "time": task.time,
                                "worker_address": list(bytes.fromhex(worker.address[2:])),
                            }
                        ),
                        ask_count=ask_count,
                        min_count=min_count,
                        client_id="vrf_worker",
                        prepare_gas=50000,
                        execute_gas=200000,
                        sender=band_requester_address_bech32,
                    )
                )
                .with_sequence(account.sequence)
                .with_account_num(account.account_number)
                .with_chain_id(await self.band_client.get_chain_id())
                .with_gas(2000000)
                .with_fee([Coin(amount=self.config.WORKER_FEE_BAND, denom="uband")])
                .with_memo("")
            )

        except Exception as e:
            print("Error get_request_tx_data", e)
            raise

    async def sign_and_broadcast_tx(self, tx: "Transaction") -> TxResponse:
        """Signs and broadcasts transaction on the BandChain.

        Args:
            tx (Transaction): Transaction to broadcast.

        Returns:
            TxResponse: Transaction response.
        """
        try:
            sign_doc = tx.get_sign_doc(self.band_public_key)
            signature = self.band_private_key.sign(sign_doc.SerializeToString())
            tx_raw_bytes = tx.get_tx_data(signature, self.band_public_key)
            return await self.band_client.send_tx_block_mode(tx_raw_bytes)

        except Exception as e:
            print("Error sign_and_broadcast_tx", e)
            raise
