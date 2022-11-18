import hashlib
from typing import List, Tuple, Dict, Type, Union
from web3 import Web3, HTTPProvider
from web3._utils.abi import get_abi_input_types
from web3.middleware import geth_poa_middleware
from .config import EvmChainConfig, Abi
from .database import Task

# Custom typings
Signature = Tuple[bytes, bytes, bytes, bytes]
CEVP = Tuple[bytes, bytes]
Web3Tx = Dict[str, Union[str, int]]


class Web3Interactor:
    """The class contains methods that interact with web3"""

    def __init__(self, _config: EvmChainConfig, _abi: Abi) -> None:
        self.config = _config
        self.abi = _abi

        # Client chain (EVM) settings
        self.web3 = Web3(HTTPProvider(self.config.EVM_JSON_RPC_ENDPOINTS[0]))
        self.set_web3()

        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.worker = self.web3.eth.account.from_key(self.config.WORKER_PK)
        self.provider_contract = self.web3.eth.contract(
            address=self.web3.toChecksumAddress(self.config.VRF_PROVIDER_ADDRESS), abi=self.abi.VRF_PROVIDER_ABI
        )
        self.lens_contract = self.web3.eth.contract(
            address=self.web3.toChecksumAddress(self.config.VRF_LENS_ADDRESS), abi=self.abi.VRF_LENS_ABI
        )
        self.bridge_contract = self.web3.eth.contract(
            address=self.web3.toChecksumAddress(self.config.BRIDGE_ADDRESS), abi=self.abi.BRIDGE_ABI
        )

    def get_worker(self):
        return self.worker

    def set_web3(self) -> None:
        """Sets the web3 variable to a working JSON RPC endpoint.

        Checks if the current web3 variable is working. If it is not,
        try the JSON RPC endpoints from the input list one by one until a
        working endpoint is set.

        Raises:
            Exception: No working JSON RPC endpoint for Client chain found.
        """
        if not self.web3.isConnected():
            for rpc in self.config.EVM_JSON_RPC_ENDPOINTS[1:]:
                try:
                    self.web3 = Web3(HTTPProvider(rpc))
                    if self.web3.isConnected():
                        return
                except Exception as e:
                    print(f"Bad endpoint - {rpc} - {e}")
                    continue

            raise Exception("No working RPC endpoints for Client chain")

    def get_block_number(self) -> int:
        """Retrieves the current block number from the client chain.

        Returns:
            int: Current block number.
        """
        try:
            return self.web3.eth.get_block_number()
        except Exception as e:
            print("Error get_block_number:", e)
            raise

    def get_current_task_nonce_from_vrf_provider(self) -> int:
        """Retrieves the latest task nonce from the VRF Provider contract.

        Returns:
            int: Latest task nonce of the VRF Provider contract. This is
            the lowest nonce which has not been used.
        """
        try:
            return self.provider_contract.functions.taskNonce().call()
        except Exception as e:
            print("Error get_current_task_nonce_from_vrf_provider:", e)
            raise

    def get_vrf_provider_config(self) -> Tuple[int, int, int]:
        """Retrieves Oracle Script configurations of the VRF Provider contract.

        Returns:
            Tuple[int, int, int]: Oracle Script ID, validators minimum count, and
            validators ask count.
        """
        try:
            oracle_script_id, min_count, ask_count = self.lens_contract.functions.getProviderConfig().call()
            return oracle_script_id, min_count, ask_count
        except Exception as e:
            print("Error get_vrf_provider_config:", e)
            raise

    def get_tasks_by_nonces(self, nonces: List[int]) -> List[Task]:
        """Retrieves a list of VRF request tasks given a list of task nonces.

        Args:
            nonces (List[int]): A list of task nonces to filter.

        Returns:
            List[Task]: A list of VRF request tasks
        """
        try:
            lens_tasks = self.lens_contract.functions.getTasksBulk(nonces).call()

            # Convert any values with type bytes to hex
            lens_tasks_hex = [[e.hex() if type(e) is bytes else e for e in task] for task in lens_tasks]

            # Convert from Lens tasks format to database tasks format
            database_tasks = [[nonce] + list(task)[:7] + [False] for nonce, task in zip(nonces, lens_tasks_hex)]

            return [Task(*task) for task in database_tasks]

        except Exception as e:
            print("Error get_tasks_by_nonces:", e)
            raise

    def get_encoded_band_chain_id_from_bridge(self) -> bytes:
        """Retrives encoded chain ID of BandChain for the Bridge contract.

        Returns:
            bytes: Chain ID of BandChain encoded to bytes
        """
        try:
            return self.bridge_contract.functions.encodedChainID().call()
        except Exception as e:
            print("Error get_encoded_band_chain_id_from_bridge:", e)
            raise

    def get_validators_from_bridge(self) -> Tuple[Dict[str, int], int]:
        """Retrieves validators information from the Bridge contract.

        Raises:
            Exception: Found a duplicated validator

        Returns:
            Tuple[Dict[str, int], int]: A dict mapping validators to the
            corresponding power, and the total power of all validators combined.
        """
        try:
            vps = self.bridge_contract.functions.getAllValidatorPowers().call()
            total_power_from_bridge = 0
            tmp = {}
            for v, p in vps:
                if v.lower() in tmp:
                    raise Exception("Error: duplicated validator found " + v.lower())

                total_power_from_bridge += int(p)
                tmp[v.lower()] = int(p)

            return tmp, total_power_from_bridge

        except Exception as e:
            print("Error get_validators_from_bridge:", e)
            raise

    def get_relay_proof_tx_data(self, proof: bytes, task: Task) -> Web3Tx:
        """Retrieves the proof transaction data.

        Args:
            proof (bytes): The proof from the BandChain.
            task (Task): The task to relay proof.

        Returns:
            Web3Tx: Web3 transaction data.
        """
        try:
            if self.config.SUPPORT_EIP1559:
                return self.provider_contract.functions.relayProof(proof, task.nonce).build_transaction(
                    {
                        "gas": self.config.MAX_RELAY_PROOF_GAS,
                        "from": self.worker.address,
                        "nonce": self.web3.eth.get_transaction_count(self.worker.address),
                        "maxPriorityFeePerGas": self.web3.eth.max_priority_fee,
                    }
                )
            else:
                return self.provider_contract.functions.relayProof(proof, task.nonce).build_transaction(
                    {
                        "gas": self.config.MAX_RELAY_PROOF_GAS,
                        "from": self.worker.address,
                        "nonce": self.web3.eth.get_transaction_count(self.worker.address),
                        "gasPrice": self.web3.eth.gas_price,
                    }
                )

        except Exception as e:
            print("Error get_relay_proof_tx_data:", e)
            raise

    def check_tx_data_validity(self, tx: Web3Tx) -> bool:
        """Checks the validity of the transaction data.

        Args:
            tx (Web3Tx): Web3 transaction data.

        Returns:
            bool: True if the transaction is valid, false otherwise.
        """
        try:
            self.web3.eth.estimate_gas(tx)
            return True
        except:
            return False

    def send_transaction(self, tx: Web3Tx) -> bytes:
        """Sends web3 transaction.

        Args:
            tx (Web3Tx): Web3 transaction.

        Returns:
            bytes: The transaction hash.
        """
        try:
            return self.web3.eth.send_raw_transaction(self.worker.sign_transaction(tx).rawTransaction)

        except Exception as e:
            print("Error send_transaction:", e)
            raise

    def get_tx_receipt_status(self, tx_hash: bytes) -> int:
        """Retrieves the transaction receipt.

        Args:
            tx_hash (bytes): Transaction hash.

        Returns:
            int: Receipt status.
        """
        try:
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            return receipt.status

        except Exception as e:
            print("Error get_tx_receipt_status:", e)
            raise

    def recover_addresses(
        self, common: bytes, signatures: List[Signature], encoded_band_chain_id: bytes
    ) -> List[Tuple[str, Signature]]:
        """Retrieves a list of validtor addresses and corresponding signatures.

        Args:
            common (bytes): Common part of the Canonical Vote.
            signatures (List[Signature]): List of validator signatures.
            encoded_band_chain_id (bytes): Chain ID of BandChain encoded to bytes.

        Returns:
            List[Tuple[str, Signature]]: List of validator addresses and the
            corresponding signatures.
        """
        list_of_addr_and_sig = []
        for r, s, v, encoded_timestamp in signatures:
            try:
                msg = common + bytes([42, len(encoded_timestamp)]) + encoded_timestamp + encoded_band_chain_id
                list_of_addr_and_sig.append(
                    (
                        self.web3.eth.account._recover_hash(
                            hashlib.sha256(bytes([len(msg)]) + msg).digest(), vrs=(v, r, s)
                        ).lower(),
                        (r, s, v, encoded_timestamp),
                    )
                )
            except:
                pass

        return list_of_addr_and_sig

    def get_only_enough_sigs(
        self, block_hash: bytes, cevp: CEVP, signatures: List[Signature], encoded_band_chain_id: bytes
    ) -> List[Signature]:
        """Retrieves the only neccesary signatures for the proof.

        Compares the validator signatures from BandChain and thos of the Bridge
        contract. Sorts and selects only the neccesary signatures (2/3 of total
        power).

        Args:
            block_hash (bytes): Block hash.
            cevp (CEVP): Common encoded vote part.
            signatures (List[Signature]): List of validator signatures.
            encoded_band_chain_id (bytes): Chain ID of BandChain encoded to bytes.

        Raises:
            Exception: Accumulated power not exceed 2/3

        Returns:
            List[Signature]: A list of validator signatures
        """
        try:
            mapping, total_power_from_bridge = self.get_validators_from_bridge()
            list_of_addr_and_sig = self.recover_addresses(
                cevp[0] + block_hash + cevp[1], signatures, encoded_band_chain_id
            )

            vps = []
            for addr, sig in list_of_addr_and_sig:
                if addr in mapping:
                    power = mapping[addr]
                    vps.append((addr, sig, power))

            ordered_by_power_desc = sorted(vps, key=lambda vp: -vp[2])
            acc_power = 0
            for i in range(len(ordered_by_power_desc)):
                acc_power += ordered_by_power_desc[i][2]
                if acc_power * 3 > total_power_from_bridge * 2:
                    ordered_by_address = sorted(ordered_by_power_desc[: i + 1], key=lambda vp: int(vp[0], 16))
                    return [vp[1] for vp in ordered_by_address]

            raise Exception("Accumulated power not exceed 2/3")

        except Exception as e:
            print("Error get_only_enough_sigs:", e)
            raise

    def get_recomposed_signature(self, evm_proof_bytes: bytes, block_hash: str, encoded_band_chain_id: bytes) -> bytes:
        """Recomposes and retrieves only neccessary signatures.

        Args:
            evm_proof_bytes (bytes): EVM proof.
            block_hash (str): Block hash.
            encoded_band_chain_id (bytes): Encoded BandChain ID.

        Returns:
            bytes: Recomposed signatures.
        """
        try:
            relay_data, verify_data = self.web3.codec.decode_single("(bytes,bytes)", bytes.fromhex(evm_proof_bytes))
            types = get_abi_input_types(
                next((abi for abi in self.abi.BRIDGE_ABI if abi["name"] == "relayBlock"), None)
            )
            multi_store, merkle_parts, cevp, sigs = self.web3.codec.decode_abi(types, relay_data)

            minimal_sigs = self.get_only_enough_sigs(bytes.fromhex(block_hash), cevp, sigs, encoded_band_chain_id)
            minimal_relay_data = self.web3.codec.encode_abi(types, (multi_store, merkle_parts, cevp, minimal_sigs))

            return self.web3.codec.encode_single("(bytes,bytes)", (minimal_relay_data, verify_data))

        except Exception as e:
            print("Error get_recomposed_signature:", e)
            raise
