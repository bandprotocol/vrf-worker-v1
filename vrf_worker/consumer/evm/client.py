from typing import Dict, List, Literal, Tuple, Union

from eth_account.signers.base import BaseAccount
from eth_typing import (
    Address,
    ChecksumAddress,
    Hash32,
    HexStr,
)
from hexbytes import (
    HexBytes,
)
from web3 import HTTPProvider, Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import ENS

from vrf_worker.types import Task

from .abi import BRIDGE_ABI, VRF_LENS_ABI, VRF_PROVIDER_ABI

# Custom typings
Signature = Tuple[bytes, bytes, bytes, bytes]
CEVP = Tuple[bytes, bytes]
Web3Tx = Dict[str, Union[str, int]]


class Client:
    """The class contains methods that interact with web3"""

    def __init__(
        self,
        endpoint: str,
        vrf_provider_address: Union[Address, ChecksumAddress, ENS],
        vrf_lens_address: Union[Address, ChecksumAddress, ENS],
        bridge_address: Union[Address, ChecksumAddress, ENS],
    ):
        w3 = Web3(HTTPProvider(endpoint))
        if not w3.is_connected():
            raise Exception("unable to connect to rpc endpoint")

        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        self.provider_contract = w3.eth.contract(vrf_provider_address, abi=VRF_PROVIDER_ABI)
        self.lens_contract = w3.eth.contract(vrf_lens_address, abi=VRF_LENS_ABI)
        self.bridge_contract = w3.eth.contract(bridge_address, abi=BRIDGE_ABI)

        self.w3 = w3

    def get_current_task_nonce_from_vrf_provider(self) -> int:
        """Retrieves the latest task nonce from the VRF Provider contract.

        Returns:
            int: Latest task nonce of the VRF Provider contract. This is
            the lowest nonce which has not been used.

        Raises:
            Exception: Failed to get current task nonce from vrf_provider.
        """
        try:
            return self.provider_contract.functions.taskNonce().call()
        except Exception as e:
            raise Exception(f"failed to get current task nonce from vrf_provider: {e}")

    def get_oracle_script_id(self) -> int:
        """Retrieves Oracle Script ID from the VRF Provider contract.

        Returns:
            Int: Oracle Script ID

        Raises:
            Exception: Failed to get oracle script ID from vrf_provider.
        """
        try:
            return self.provider_contract.functions.oracleScriptID().call()
        except Exception as e:
            raise Exception(f"failed to get oracle script ID from vrf_provider: {e}")

    def get_tasks_by_nonces(self, nonces: List[int]) -> List[Task]:
        """Retrieves a list of VRF request tasks given a list of task nonces.

        Args:
            nonces (List[int]): A list of task nonces to filter.

        Returns:
            List[Task]: A list of VRF request tasks

        Raises:
            Exception: Failed to get tasks by nonces from lens.
        """
        try:
            lens_tasks = self.lens_contract.functions.getTasksBulk(nonces).call()

            # Convert any values with type bytes to hex
            tasks = [[e.hex() if type(e) is bytes else e for e in task] for task in lens_tasks]

            return [Task(*task) for task in tasks]

        except Exception as e:
            raise Exception(f"failed to get tasks by nonces from lens: {e}")

    def get_encoded_band_chain_id_from_bridge(self) -> bytes:
        """Retrives encoded chain ID of BandChain for the Bridge contract.

        Returns:
            bytes: Chain ID of BandChain encoded to bytes

        Raises:
            Exception: Failed to get encoded band chain ID from bridge.
        """
        try:
            return self.bridge_contract.functions.encodedChainID().call()
        except Exception as e:
            raise Exception(f"failed to get encoded band chain ID from bridge: {e}")

    def get_validators_from_bridge(self) -> dict[str, int]:
        """Retrieves validators information from the Bridge contract.

        Returns:
            Tuple[Dict[str, int], int]: A dict mapping validators to the
            corresponding power, and the total power of all validators combined.

        Raises:
            Exception: Found a duplicated validator
        """
        try:
            validator_powers = self.bridge_contract.functions.getAllValidatorPowers().call()
            validator_power_map = {addr.lower(): int(power) for addr, power in validator_powers}

            if len(validator_power_map) != len(validator_powers):
                raise Exception("Error: duplicated validator found")

            return validator_power_map

        except Exception as e:
            raise Exception(f"failed to get validators from bridge: {e}")

    def relay_proof(
        self,
        proof: bytes,
        nonce: int,
        account: BaseAccount,
        eip1559: bool = True,
    ) -> str:
        """Relay the proof transaction data.

        Args:
            proof (bytes): the proof to relay.
            nonce (int): the task nonce.
            account (BaseAccount): Account to sign the transaction.
            eip1559 (bool, optional): Whether to use EIP-1559 transaction format. Defaults to True.

        Returns:
            str: Transaction hash as a hex string.

        Raises:
            Exception: Failed to relay proof.
        """
        try:
            tx_params: Web3Tx = {}
            if eip1559:
                tx_params = {
                    "from": account.address,
                    "nonce": self.w3.eth.get_transaction_count(account.address),
                    "maxPriorityFeePerGas": self.w3.eth.max_priority_fee,
                }
            else:
                tx_params = {
                    "from": account.address,
                    "nonce": self.w3.eth.get_transaction_count(account.address),
                    "gasPrice": self.w3.eth.gas_price,
                }

            fn = self.provider_contract.functions.relayProof(proof, nonce)

            gas = fn.estimate_gas(tx_params)
            tx_params["gas"] = gas

            tx = fn.build_transaction(tx_params)
            signed_tx = account.sign_transaction(tx)

            return self.w3.eth.send_raw_transaction(signed_tx.raw_transaction).to_0x_hex()
        except Exception as e:
            raise Exception(f"failed to relay proof: {e}")

    def get_tx_receipt_status(self, tx_hash: Hash32 | HexBytes | HexStr) -> int:
        """Retrieves the transaction receipt.

        Args:
            tx_hash (bytes): Transaction hash.

        Returns:
            int: Receipt status.
        """
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            return receipt["status"]

        except Exception as e:
            raise Exception(f"failed to get tx receipt status: {e}")
