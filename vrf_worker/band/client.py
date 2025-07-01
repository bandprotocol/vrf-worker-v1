import asyncio
import time

import grpclib
import pyband
from pyband.messages.band.oracle.v1 import MsgRequestData
from pyband.obi import PyObi
from pyband.proto.band.base.oracle.v1 import ProofRequest
from pyband.proto.band.oracle.v1 import ResolveStatus
from pyband.proto.cosmos.base.abci.v1beta1 import TxResponse
from pyband.proto.cosmos.base.tendermint.v1beta1 import GetBlockByHeightRequest
from pyband.proto.cosmos.base.v1beta1 import Coin
from pyband.transaction import Transaction
from pyband.wallet import Wallet

from vrf_worker.band.types import TxParams

VRF_OBI = PyObi("{seed:[u8],time:u64,worker_address:[u8]}/{proof:[u8],result:[u8]}")


class Client:
    """This class contains methods that interact with the BandChain Client."""

    def __init__(self, grpc_endpoint: str) -> None:
        try:
            (grpc_endpoint, port) = grpc_endpoint.split(":")
        except Exception as _:
            raise Exception("invalid grpc endpoint. endpoint must be in the format of host:port")

        self.client = pyband.Client.from_endpoint(grpc_endpoint, port)
        self.channel = self.client.__channel

    async def request_vrf(
        self,
        oracle_script_id: int,
        worker_address: str,
        seed: str,
        time: int,
        tx_params: TxParams,
        signer: Wallet,
    ) -> TxResponse:
        """Requests VRF from BandChain.

        Args:
            oracle_script_id (int): The ID of the oracle script to request VRF from.
            worker_address (str): Worker address.
            seed (str): Seed.
            time (int): Time.
            request_params (OracleRequestParams): The parameters for the transaction.
            signer (PrivateKey): Signer.

        Returns:
            TxResponse: Transaction response.

        Raises:
            Exception: Account not found.
            Exception: Transaction failed.
        """
        address = signer.get_address().to_acc_bech32()
        account = await self.client.get_account(address)
        if account is None:
            raise Exception("Account not found")

        try:
            calldata = VRF_OBI.encode(
                {
                    "seed": list(bytes.fromhex(seed)),
                    "time": time,
                    "worker_address": list(bytes.fromhex(worker_address[2:])),
                }
            )

            msg = MsgRequestData(
                oracle_script_id=oracle_script_id,
                calldata=calldata,
                ask_count=tx_params.ask_count,
                min_count=tx_params.min_count,
                client_id="vrf_worker",
                prepare_gas=tx_params.prepare_gas,
                execute_gas=tx_params.execute_gas,
                sender=address,
                fee_limit=[Coin(amount=str(tx_params.ds_fee_limit), denom="uband")],
            )

            chain_id = await self.client.get_chain_id()

            tx = Transaction(
                msgs=[msg],
                account_num=account.account_number,
                sequence=account.sequence,
                chain_id=chain_id,
                gas_price=tx_params.gas_price,
                gas_limit=tx_params.gas_limit,
                memo="",
            )

            payload = signer.sign_and_build(tx)

            return await self.client.send_tx_sync_mode(payload)

        except Exception as e:
            raise e

    async def get_transaction(self, tx_hash: str, timeout: int = 30) -> TxResponse:
        """Get a transaction response from BandChain.

        Args:
            tx_hash (str): The hash of the transaction.
            timeout (int): The timeout for the request in seconds.

        Returns:
            TxResponse: The transaction response.

        Raises:
            Exception: Transaction not found.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                return await self.client.get_tx_response(tx_hash)
            except Exception:
                await asyncio.sleep(1)
        raise Exception(f"Transaction `{tx_hash}` not found after timeout")

    async def get_evm_proof_and_block_hash(self, request_id: int, timeout: int = 60) -> tuple[bytes, bytes]:
        """Gets the evm proof and block hash from the request id.

        Args:
            request_id (int): The request id.
            timeout (int): The timeout for the request in seconds.

        Returns:
            tuple: (evm_proof_bytes, block_hash)
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            asyncio.sleep(1)
            try:
                # Get initial proof
                proof_request = ProofRequest(request_id=request_id)
                resp = await self.client.get_proof(proof_request)
                resolve_status = resp.result.proof.oracle_data_proof.result.resolve_status
                match resolve_status:
                    case ResolveStatus.OPEN_UNSPECIFIED:
                        continue
                    case ResolveStatus.SUCCESS:
                        pass
                    case ResolveStatus.FAILURE:
                        raise Exception("request for request id {request_id} has failed")
                    case ResolveStatus.EXPIRED:
                        raise Exception("request for request id {request_id} is expired")

                # Set block height to the next block after request is resolved
                block_height = resp.result.proof.oracle_data_proof.version + 1

                # Get proof at block height
                proof_request = ProofRequest(request_id=request_id, height=block_height)
                resp = await self.client.get_proof(proof_request)
                evm_proof_bytes = resp.result.evm_proof_bytes

                block_response = await self.client.tendermint_service_stub.get_block_by_height(
                    GetBlockByHeightRequest(height=block_height)
                )

                block_hash = block_response.block_id.hash
                return (evm_proof_bytes, block_hash)
            except grpclib.exceptions.GRPCError as e:
                if e.status == grpclib.const.Status.UNKNOWN:
                    pass
                else:
                    raise e
            except Exception as e:
                raise e

        raise Exception(f"Failed to get evm proof and block hash for request id {request_id} after timeout")
