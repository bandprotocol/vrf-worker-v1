import json
import requests
import time
from func_timeout import func_timeout, FunctionTimedOut
from typing import Optional, Tuple, List
from pyband.proto.cosmos.base.abci.v1beta1 import TxResponse
from .config import EvmChainConfig, BandChainConfig
from .database import Database, Task
from .web3_interactor import Web3Interactor
from .band_interactor import BandInteractor


class Helpers:
    """The class contains helper methods for the main app."""

    def __init__(
        self,
        _evm_chain_config: EvmChainConfig,
        _band_chain_config: BandChainConfig,
        _web3_interactor: Web3Interactor,
        _band_interactor: BandInteractor,
    ) -> None:
        self.evm_chain_config = _evm_chain_config
        self.band_chain_config = _band_chain_config
        self.web3_interactor = _web3_interactor
        self.band_interactor = _band_interactor

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
            nonce_from_contract = self.web3_interactor.get_current_task_nonce_from_vrf_provider()
            latest_task_from_db = db.get_latest_task_by_nonce()
            start_nonce = self.evm_chain_config.START_NONCE

            if latest_task_from_db is not None:
                start_nonce = latest_task_from_db.nonce

            if start_nonce + 1 == nonce_from_contract:
                print(f"DB_latest_nonce={start_nonce} and current_contract_nonce={nonce_from_contract} -> up to date")
                print("---------------------------------------------------------")
                return

            new_tasks = self.web3_interactor.get_tasks_by_nonces([i for i in range(start_nonce, nonce_from_contract)])

            if new_tasks is None:
                print("Latest task by nonce: ", db.get_latest_task_by_nonce())
                print("Unresolved tasks: ", db.get_unresolved_tasks(0, 100))
                print("---------------------------------------------------------")
                return

            try:
                for t in new_tasks:
                    if t.caller in self.evm_chain_config.WHITELISTED_CALLERS:
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
            tx = self.web3_interactor.get_relay_proof_tx_data(proof, task)

            if not self.web3_interactor.check_tx_data_validity(tx):
                print("Invalid tx data")
                # Handle fork case: No task on-chain and task in db not resolve yet
                task_on_chain = self.web3_interactor.get_tasks_by_nonces([task.nonce])[0]
                if task_on_chain.seed != task.seed:
                    db.delete_task(task.nonce)
                    db.session.commit()
                    print(f"Task {task.nonce} in database deleted")

                raise Exception("Invalid tx data")

            tx_hash = self.web3_interactor.send_transaction(tx)
            print("sending", tx_hash.hex())

            receipt_status = self.web3_interactor.get_tx_receipt_status(tx_hash)
            if receipt_status == 1:
                print(f"Status: {receipt_status} | Successfully relayed proof for task {task.nonce}")
                current_block = self.web3_interactor.get_block_number()
                db.resolve_task(task.nonce, current_block)
                db.session.commit()
                print(f"Successfully updated resolved task {task.nonce} on database")

            else:
                print(f"Status: {receipt_status} | Failed to relay proof for task {task.nonce}")
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
            oracle_script_id, min_count, ask_count = self.web3_interactor.get_vrf_provider_config()
            worker = self.web3_interactor.get_worker()
            unknown_status_tasks = db.get_unresolved_tasks(0, 100)

            for task in unknown_status_tasks:
                current_task_on_chain = self.web3_interactor.get_tasks_by_nonces([task.nonce])[0]

                if current_task_on_chain.is_resolve:
                    try:
                        current_block = self.web3_interactor.get_block_number()
                        db.resolve_task(current_task_on_chain.nonce, current_block)
                        db.session.commit()
                        continue
                    except Exception:
                        db.session.rollback()
                        raise

                tx = await self.band_interactor.get_request_tx_data(
                    oracle_script_id, min_count, ask_count, task, worker
                )
                tx_block = await self.band_interactor.sign_and_broadcast_tx(tx)
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
            tasks_to_fork_check = db.get_tasks_to_fork_check(current_block, 0, 100, self.evm_chain_config.BLOCK_DIFF)
            print("Tasks to fork check:", tasks_to_fork_check)
            nonces_to_check = [t.nonce for t in tasks_to_fork_check]
            tasks_on_chain = self.web3_interactor.get_tasks_by_nonces(nonces_to_check)

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

    def get_block_band_latest_block_height_and_hash(self, block_height: Optional[int]) -> Tuple[int, str]:
        """Retrieves block height and block hash of BandChain

        If the block height is not specified, retrieves the latest block height and
        the corresponding block hash from BandChain.

        Args:
            block_height (Optional[int]): Block height to retrieve.

        Returns:
            Tuple[int, str]: Block height and the corresponding block hash.
        """
        block_endpoint = self.get_working_endpoint(self.band_chain_config.BAND_RPC_ENDPOINTS, "block")
        url = f"{block_endpoint}/block" + ("" if block_height is None else f"?height={block_height + 1}")
        try:
            r = requests.get(url).json()
            current_height = int(r["result"]["block"]["header"]["height"]) - 1
            current_hash = r["result"]["block"]["header"]["last_block_id"]["hash"]
            return current_height, current_hash

        except Exception as e:
            print("Failed to get block:", e)
            raise

    def check_endpoint(self, url: str) -> bool:
        """Checks if the endpoint is working.

        Args:
            url (str): endpoint url

        Returns:
            bool: True if the endpoint is working.
        """
        res = requests.get(url)
        return res.status_code == 200

    def get_working_endpoint(self, endpoints: List[str], path: str) -> str:
        """Sets a working endpoint.

        Args:
            endpoints (List[str]): A list of endpoints.
            path (str): Path.

        Raises:
            Exception: No working endpoints.

        Returns:
            str: A working endpoint.
        """
        for endpoint in endpoints:
            try:
                if self.check_endpoint(f"{endpoint}/{path}"):
                    return endpoint
            except Exception:
                continue
        raise Exception("No working endpoints")

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
            proof_endpoint = self.get_working_endpoint(self.band_chain_config.BAND_PROOF_URLS, "1")

            count = 1
            while count <= 10:
                try:
                    height = int(requests.get(f"{proof_endpoint}/{req_id}").json()["result"]["proof"]["block_height"])
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
                    requests.get(f"{proof_endpoint}/{req_id}?height={height}").json()["result"]["evm_proof_bytes"],
                    height,
                )
            count += 1
            time.sleep(3)
            if count >= 10:
                raise Exception("Unable to get proof - final proof not retrieved")

        except Exception as e:
            print("Error try_get_request_proof_by_id", e)
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
            encoded_band_chain_id = self.web3_interactor.get_encoded_band_chain_id_from_bridge()
            return self.web3_interactor.get_recomposed_signature(evm_proof_bytes, block_hash, encoded_band_chain_id)

        except Exception as e:
            print("Error get_proof_and_recompose_signature:", e)
            raise
