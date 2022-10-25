import asyncio
import time
from flask import Flask
from func_timeout import FunctionTimedOut
from helpers.config import DbConfig, AppEnvConfig, Abi
from helpers.database import Database
from helpers.helpers import Helpers
from helpers.web3_interactor import Web3Interactor
from helpers.band_interactor import BandInteractor
from helpers.error_handler import ErrorHandler


async def run_vrf_worker_local() -> None:
    """Main entry point to run the locally deployed VRF worker.

    Preparation phase - Instantiates a new app and creates new database tables
    if required. Checks the error count. Sets web3 to a working JSON RPC
    endpoint. Polls the client chain's block number until a new block is
    created.

    Execution phase - Checks for chain fork and makes adjustment to the tasks
    on the database if required. Retrieves new tasks from the chain and adds
    them to the database. Sends the new request tasks to BandChain and waits
    for the VRF result and the BandChain proof to be generated. Relays the
    result and proof back to the client chain.

    Final phase - Resets the error count to zero.

    If an error occurs during any point - Increases the error count by one.
    """

    app = Flask(__name__)
    app.config.from_object(DbConfig())
    db = Database(app)
    app_env_config = AppEnvConfig()
    abi = Abi()

    prev_block = 0
    db.create_all()

    while True:
        try:
            web3_interactor = Web3Interactor(app_env_config, abi)
            band_interactor = BandInteractor(app_env_config)
            await band_interactor.set_band_client()
            helpers = Helpers(app_env_config, web3_interactor, band_interactor)

            error_count = ErrorHandler.current_error_count(db)
            print(f"Error count: {error_count}")

            current_block = web3_interactor.get_block_number()
            print("(prev_block, current_block)", prev_block, current_block)

            if current_block > prev_block:
                helpers.check_for_chain_fork(db, current_block)
                helpers.add_new_tasks_to_db(db, current_block)
                await helpers.request_random_data_on_band_and_relay(db)

            prev_block = current_block

            # Transaction success, reset error count
            ErrorHandler.update_error_count(db, 0)

            time.sleep(5)

        except (Exception, FunctionTimedOut) as e:
            message = "Error running VRF Worker"
            print(f"{message}: {e}")

            error_count = ErrorHandler.current_error_count(db) + 1
            ErrorHandler.update_error_count(db, error_count)
            time.sleep(5)


if __name__ == "__main__":
    asyncio.run(run_vrf_worker_local())
