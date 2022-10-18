import json
import requests
import requests
import hashlib
import time
from func_timeout import func_timeout, FunctionTimedOut
from typing import Optional, List, Tuple, Dict, Type
from web3 import Web3, HTTPProvider
from web3._utils.abi import get_abi_input_types
from web3.middleware import geth_poa_middleware
from pyband import Client
from pyband.wallet import PrivateKey
from pyband.transaction import Transaction
from pyband.obi import PyObi
from pyband.proto.cosmos.base.v1beta1 import Coin
from pyband.proto.cosmos.base.abci.v1beta1 import TxResponse
from pyband.messages.oracle.v1 import MsgRequestData
from .config import AppEnvConfig, Abi
from .database import Database, Task

# Custom typings
Signature = Tuple[bytes, bytes, bytes, bytes]
CEVP = Tuple[bytes, bytes]


class Helpers:
    """The class contains helper methods for the main app."""

    def __init__(self, _config: Type[AppEnvConfig], _abi: Type[Abi]) -> None:
        """Sets config and ABI from AppEnvConfig and Abi classes. Sets
        BandChain and web3 settings according to the config.

        Args:
            _config (Type[AppEnvConfig]): Class AppEnvConfig
            _abi (Type[Abi]): Class Abi
        """
        self.config = _config
        self.abi = _abi

        # BandChain settings
        self.band_private_key = PrivateKey.from_mnemonic(self.config.BAND_MNEMONIC)
        self.band_public_key = self.band_private_key.to_public_key()
        self.band_requester_address = self.band_public_key.to_address()
        self.band_client = Client.from_endpoint(self.config.BAND_RPC[0], self.config.BAND_RPC_PORT)

        # Client chain (EVM) settings
        self.web3 = Web3(HTTPProvider(self.config.JSON_RPC_ENDPOINT[0]))

        if self.config.POA_CHAIN:
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

    def set_web3(self) -> None:
        """Sets the web3 variable to a working JSON RPC endpoint.

        Checks if the current web3 variable is working. If it is not,
        try the JSON RPC endpoints from the input list one by one until a
        working endpoint is set.

        Raises:
            Exception: No working JSON RPC endpoint for Client chain found.
        """
        try:
            if not self.web3.isConnected():
                for rpc in self.config.JSON_RPC_ENDPOINT:
                    self.web3 = Web3(HTTPProvider(rpc))
                    if self.web3.isConnected():
                        return

                raise Exception("No working RPC endpoints for Client chain")

        except Exception as e:
            print("Error set_web3:", e)
            raise

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
            tasks = self.lens_contract.functions.getTasksBulk(nonces).call()
            return [
                Task(*[e.hex() if type(e) is bytes else e for e in [n] + list(t)[:7] + [0]])
                for n, t in zip(nonces, tasks)
            ]
        except Exception as e:
            print("Error get_tasks_by_nonces:", e)
            raise

    def add_new_tasks_to_db(self, db: Database, current_block: int) -> None:
        """Retrieves new request tasks from VRF Contract and adds to database.

        Checks if the latest task on the database is up to date with the latest
        task on the VRF Provider contract. If it is not up to date, retrieves the
        new tasks, then checks if the task was created by a whitelisted address. If
        it is, adds the new tasks on the database.

        Args:
            db (Database): Database object for interacting with the SQL database.
            current_block (int): Current block number.
        """
        try:
            nonce_from_contract = self.get_current_task_nonce_from_vrf_provider()
            latest_task_from_db = db.get_latest_task_by_nonce()
            start_nonce = self.config.START_NONCE

            if latest_task_from_db is not None:
                start_nonce = latest_task_from_db.nonce

            if start_nonce + 1 == nonce_from_contract:
                print(f"DB_latest_nonce={start_nonce} and current_contract_nonce={nonce_from_contract} -> up to date")
                print("---------------------------------------------------------")
                return

            new_tasks = self.get_tasks_by_nonces([i for i in range(start_nonce, nonce_from_contract)])

            if new_tasks is None:
                print("Latest task by nonce: ", db.get_latest_task_by_nonce())
                print("Unresolved tasks: ", db.get_unresolved_tasks(0, 100))
                print("---------------------------------------------------------")
                return

            try:
                for t in new_tasks:
                    if t.caller in self.config.WHITELISTED_CALLERS:
                        db.add_new_task_if_not_existed(t, current_block)

                db.session.commit()
                print("New tasks added to db")

            except Exception:
                db.session.rollback()
                raise

            print("Latest task by nonce: ", db.get_latest_task_by_nonce())
            print("Unresolved tasks: ", db.get_unresolved_tasks(0, 100))

        except Exception as e:
            print("Error add_new_tasks_to_db:", e)
            raise

    def extract_request_id_from_request_tx(self, tx: TxResponse) -> int:
        """Retrieves the request ID from a request transaction.

        Args:
            tx (TxResponse): Request transaction object.

        Raises:
            ValueError: Request ID is not found in the request transaction.

        Returns:
            int: Request ID of the request transaction.
        """
        try:
            logs = json.loads(tx.raw_log)
            for log in logs:
                for event in log["events"]:
                    if event["type"] == "request":
                        for attr in event["attributes"]:
                            if attr["key"] == "id":
                                return attr["value"]

            raise Exception("Cannot find request id")

        except Exception as e:
            print("Error extract_request_id_from_request_tx:", e)
            raise

    def relay_proof(self, db: Database, proof: bytes, task: Task) -> None:
        """Relays the proof of autheticity from BandChain on the client chain.

        Prepares the 'relayProof' transaction, then estimates the transaction's gas
        to be consumed. If the estimation fail, deletes the transaction from the
        database to handle the client chain's forking (Case: No task on-chain and
        task in database is not resolved yet). Otherwise, calls the relayProof
        function on the VRF Provider contract, and waits for the transaction
        receipt. If the transaction succeed, change the task's status on the
        database to resolved.

        Args:
            db (Database): Database object for interacting with the SQL database.
            proof (bytes): Proof of autheticity from BandChain.
            task (Task): Task that the proof is checked against.

        Raises:
            Exception: An error occured while relaying proof on the client chain
        """
        try:
            if self.config.SUPPORT_EIP1559:
                tx = self.provider_contract.functions.relayProof(proof, task.nonce).build_transaction(
                    {
                        "gas": 1200000,
                        "from": self.worker.address,
                        "nonce": self.web3.eth.get_transaction_count(self.worker.address),
                    }
                )
            else:
                tx = self.provider_contract.functions.relayProof(proof, task.nonce).build_transaction(
                    {
                        "gas": 1200000,
                        "from": self.worker.address,
                        "nonce": self.web3.eth.get_transaction_count(self.worker.address),
                        "gasPrice": self.web3.eth.gas_price,
                    }
                )

            try:
                # Throw error if tx is expected to fail
                self.web3.eth.estimate_gas(tx)
            except Exception as e:
                print("Failed to estimate gas:", e)
                # Handle fork case: No task on-chain and task in db not resolve yet
                task_on_chain = self.get_tasks_by_nonces([task.nonce])[0]
                if task_on_chain.seed != task.seed:
                    db.delete_task(task.nonce)
                    db.session.commit()
                    print(f"Task {task.nonce} in database deleted")
                return

            tx_hash = self.web3.eth.send_raw_transaction(self.worker.sign_transaction(tx).rawTransaction)
            print("sending", tx_hash.hex())

            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            if receipt.status == 1:
                print(f"Status: {receipt.status} | Successfully relayed proof for task {task.nonce}")
                current_block = self.web3.eth.get_block_number()
                db.resolve_task(task.nonce, current_block)
                db.session.commit()
                print(f"Successfully updated resolved task {task.nonce} on database")

            else:
                print(f"Status: {receipt.status} | Failed to relay proof for task {task.nonce}")
                db.session.rollback()
                raise Exception("Failed to relay proof")

        except Exception as e:
            print("Error relay_proof:", e)
            raise

    async def request_random_data_on_band_and_relay(self, db: Database) -> None:
        """Requests a random value on BandChain and relay the result and proof.

        Retrieves unresolved tasks from the database, checks them against the
        status on the client chain, and marks resolved on the database accordingly.
        For each unresolved task on the client chain, prepares a transaction for
        requesting a random value, then broadcasts the transaction on BandChain.
        Polls until the proof of authenticiy is published on BandChain, then
        retrives and recomposes the proof with only the necessary signatures.
        Relays the resulting proof to the VRF Provider contract.

        Args:
            db (Database): Database object for interacting with the SQL database.
        """
        try:
            oracle_script_id, min_count, ask_count = self.get_vrf_provider_config()
            obi = PyObi("{seed:[u8],time:u64,worker_address:[u8]}/{proof:[u8],result:[u8]}")
            band_requester_address_bech32 = self.band_requester_address.to_acc_bech32()
            unknown_status_tasks = db.get_unresolved_tasks(0, 100)
            for task in unknown_status_tasks:
                current_task_on_chain = self.get_tasks_by_nonces([task.nonce])[0]

                if current_task_on_chain.is_resolve:
                    try:
                        current_block = self.web3.eth.get_block_number()
                        db.resolve_task(current_task_on_chain.nonce, current_block)
                        db.session.commit()
                        continue
                    except Exception:
                        db.session.rollback()
                        raise

                account = await self.band_client.get_account(band_requester_address_bech32)
                txn = (
                    Transaction()
                    .with_messages(
                        MsgRequestData(
                            oracle_script_id=oracle_script_id,
                            calldata=obi.encode(
                                {
                                    "seed": list(bytes.fromhex(task.seed)),
                                    "time": task.time,
                                    "worker_address": list(bytes.fromhex(self.worker.address[2:])),
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

                # Sign a transaction by using private key
                sign_doc = txn.get_sign_doc(self.band_public_key)
                signature = self.band_private_key.sign(sign_doc.SerializeToString())
                tx_raw_bytes = txn.get_tx_data(signature, self.band_public_key)

                # Broadcast a transaction
                tx_block = await self.band_client.send_tx_block_mode(tx_raw_bytes)
                request_id = self.extract_request_id_from_request_tx(tx_block)

                # Get only necessary signatures
                print("---------------------------------------------------------")
                print(f"Getting proof for Task {current_task_on_chain.nonce}")
                proof = func_timeout(100, self.get_proof_and_recompose_signature, args=[request_id])
                print("proof size:", len(proof))

                func_timeout(60, self.relay_proof, args=(db, proof, task))

        except (Exception, FunctionTimedOut) as e:
            print("Error request_random_data_on_band_and_relay:", e)
            raise

    def check_for_chain_fork(self, db: Database, current_block: int) -> None:
        """Checks for forking on the client chain.

        Retrieves tasks that have not been fork checked from the database and
        compares to the corresponding tasks on the client chain. If the seeds are
        different, deletes the task from the database (Fork case: on-chain task
        and db task are not the same task). If the on-chain task status is
        unresolved, marks the database's task status unresolved. (Fork case:
        on-chain task not resolved, but db task resolved). Otherwise, mark the
        database's task as fork checked.

        Args:
            db (Database): Database object for interacting with the SQL database.
            current_block (int): Current block number.
        """
        try:
            print("---------------------------------------------------------")
            tasks_to_fork_check = db.get_tasks_to_fork_check(current_block, 0, 100, AppEnvConfig)
            print("Tasks to fork check:", tasks_to_fork_check)
            nonces_to_check = [t.nonce for t in tasks_to_fork_check]
            tasks_on_chain = self.get_tasks_by_nonces(nonces_to_check)

            for i in range(len(tasks_to_fork_check)):
                task_nonce = nonces_to_check[i]

                # Fork case: on-chain task and db task are not the same task (different seeds)
                if tasks_to_fork_check[i].seed != tasks_on_chain[i].seed:
                    try:
                        print(f"Found discrepancy for Task {task_nonce}")
                        # Delete all tasks from this task nonce onwards, asssuming all
                        # the remaining tasks will change to new tasks from another fork
                        db.delete_multiple_tasks(task_nonce)
                        db.session.commit()
                        print(f"Successfully deleted all tasks from Task {task_nonce}")
                        break
                    except Exception:
                        db.session.rollback()
                        print(f"Failed to delete all tasks from Task {task_nonce}")
                        raise

                # Fork case: on-chain task not resolved, but db task resolved
                if not tasks_on_chain[i].is_resolve:
                    try:
                        db.mark_not_resolve(task_nonce)
                        db.session.commit()
                        print(f"Successfully mark_not_resolve Task {task_nonce}")
                        continue
                    except Exception:
                        db.session.rollback()
                        print(f"Failed to mark_not_resolve Task {task_nonce}")
                        raise

                # Normal case: complete fork check
                try:
                    db.fork_check_mark_done(task_nonce)
                    db.session.commit()
                    print(f"Completed fork check for Task {task_nonce}")
                except Exception:
                    db.session.rollback()
                    print(f"Failed to fork check for Task {task_nonce}")
                    raise

        except Exception as e:
            print(e)
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

    def get_block_band_latest_block_height_and_hash(self, block_height: Optional[int]) -> Tuple[int, str]:
        """Retrieves block height and block hash of BandChain

        If the block height is not specified, retrieves the latest block height and
        the corresponding block hash from BandChain.

        Args:
            block_height (Optional[int]): Block height to retrieve.

        Returns:
            Tuple[int, str]: Block height and the corresponding block hash.
        """
        url = f"{self.config.BAND_RPC_BLOCK}/block" + ("" if block_height is None else f"?height={block_height + 1}")
        try:
            r = requests.get(url).json()
            current_height = int(r["result"]["block"]["header"]["height"]) - 1
            current_hash = r["result"]["block"]["header"]["last_block_id"]["hash"]
            return current_height, current_hash

        except Exception as e:
            print("Failed to get block:", e)
            raise

    def try_get_request_proof_by_id(self, req_id: int) -> Tuple[bytes, int]:
        """Retrieves proof from BandChain for a specified request ID.

            Retrieves the block height from BandChain for the input request ID that
            the proof was first published. Waits for the latest block to exceed the
            original proof block height to ensure the majority of signatures have
            been collected. Retrieves the EVM proof bytes and the corresponding
            block height.

        Args:
            req_id (int): Request ID.

        Raises:
            Exception: Unable to get proof - initial proof not retrieved
            Exception: Unable to get proof - latest block height not retrieved
            Exception: Unable to get proof - final proof not retrieved

        Returns:
            Tuple[bytes, int]: EVM proof bytes and block height
        """
        try:
            count = 1
            while count <= 10:
                try:
                    height = int(
                        requests.get(f"{self.config.BAND_PROOF_URL}/{req_id}").json()["result"]["proof"][
                            "block_height"
                        ]
                    )
                    break
                except Exception as e:
                    print("Get proof attempt ", count)
                count += 1
                time.sleep(3)
            if count >= 10:
                raise Exception("Unable to get proof - initial proof not retrieved")

            count = 1
            while count <= 10:
                latest_height, _ = self.get_block_band_latest_block_height_and_hash(None)
                if latest_height > height:
                    break
                count += 1
                time.sleep(3)
            if count >= 10:
                raise Exception("Unable to get proof - latest block height not retrieved")

            count = 1
            while count <= 10:
                return (
                    requests.get(f"{self.config.BAND_PROOF_URL}/{req_id}?height={height}").json()["result"][
                        "evm_proof_bytes"
                    ],
                    height,
                )
            count += 1
            time.sleep(3)
            if count >= 10:
                raise Exception("Unable to get proof - final proof not retrieved")

        except Exception as e:
            print("Error try_get_request_proof_by_id", e)
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

    def get_proof_and_recompose_signature(self, req_id: int) -> bytes:
        """Retrieves the proof with only neccesary signatures.

        Args:
            req_id (int): Request ID.

        Returns:
            bytes: Proof from BandChain with only neccesary signatures to be used
            for relaying on the Bridge contract.
        """
        try:
            evm_proof_bytes, block_height = self.try_get_request_proof_by_id(req_id)
            _, block_hash = self.get_block_band_latest_block_height_and_hash(block_height)
            encoded_band_chain_id = self.get_encoded_band_chain_id_from_bridge()

            relay_data, verify_data = self.web3.codec.decode_single("(bytes,bytes)", bytes.fromhex(evm_proof_bytes))
            types = get_abi_input_types(
                next((abi for abi in self.abi.BRIDGE_ABI if abi["name"] == "relayBlock"), None)
            )
            multi_store, merkle_parts, cevp, sigs = self.web3.codec.decode_abi(types, relay_data)

            minimal_sigs = self.get_only_enough_sigs(bytes.fromhex(block_hash), cevp, sigs, encoded_band_chain_id)
            minimal_relay_data = self.web3.codec.encode_abi(types, (multi_store, merkle_parts, cevp, minimal_sigs))

            return self.web3.codec.encode_single("(bytes,bytes)", (minimal_relay_data, verify_data))

        except Exception as e:
            print("Error get_proof_and_recompose_signature:", e)
            raise

    def check_error_limit(self, error_count: int) -> None:
        """Checks the error count.

        Sends notification to discord if the error count reaches 3.

        Args:
            error_count (int): Cumulative error count
        """
        try:
            if error_count == 3:
                message = f"<{self.config.CHAIN}> VRF Worker failed to run multiple times!"
                Helpers.send_notification_to_discord(self.config.DISCORD_WEBHOOK, message)

        except Exception as e:
            print("Error check_error_count", e)

    @staticmethod
    def send_notification_to_discord(url: str, message: str) -> None:
        """Sends notification to discord.

        Args:
            url (str): Discord webhook URL.
            message (str): Message to send.
        """
        try:
            res = requests.post(
                url=url,
                json={"content": message},
                headers={"Content-type": "application/json"},
            )

            res.raise_for_status()

        except Exception as e:
            print("Error send_notification_to_discord", e)
            raise

    @staticmethod
    def current_error_count(db: Database) -> None:
        """Retrieves the current error count from database

        Args:
            db (Database): Database object for interacting with the SQL database.
        """
        try:
            return db.get_error_count()

        except Exception as e:
            print("Error check_error_count", e)
            raise

    @staticmethod
    def update_error_count(db: Database, new_count: int) -> None:
        """Update the error count in the database

        Args:
            db (Database): Database object for interacting with the SQL database.
            new_count (int): New error count
        """
        try:
            db.change_error_count(new_count)
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print("Error update_error_count", e)
            raise
