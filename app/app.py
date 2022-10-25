import asyncio
import time
from aioflask import Flask
from func_timeout import FunctionTimedOut
from helpers.config import DbConfig, AppEnvConfig, CreateTaskConfig, Abi
from helpers.create_task import CreateTask
from helpers.database import Database
from helpers.helpers import Helpers
from helpers.web3_interactor import Web3Interactor
from helpers.band_interactor import BandInteractor
from helpers.error_handler import ErrorHandler

app = Flask(__name__)
app.config.from_object(DbConfig())
db = Database(app)
app_env_config = AppEnvConfig()
abi = Abi()
create_task_config = CreateTaskConfig()

prev_block = None


@app.route("/", methods=["POST"])
async def run_vrf_worker() -> tuple[str, int]:
    """Main entry point to run the VRF worker deployed on Cloud Run.

    Listens for an incoming HTTP POST request and executes the following:

    Preparation phase - Creates new database tables if  required. Checks the
    error count and sends notification if the error limit is reached. Sets web3
    to a working JSON RPC endpoint.  Polls the client chain's block number
    until a new block is created.

    Execution phase - Checks for chain fork and makes adjustment to the tasks
    on the database if required. Retrieves new tasks from the chain and adds
    them to the database. Sends the new request tasks to BandChain and waits
    for the VRF result and the BandChain proof to be generated. Relays the
    result and proof back to the client chain.

    Final phase - Creates a new task on Cloud Tasks and resets the error count
    to zero. Returns success message and status code.

    If an error occurs during any point - Increases the error count by one.
    Creates a new task on Cloud Tasks and returns error message and status
    code.

    Returns:
        tuple[str, int]: Response message and status code.
    """
    try:
        global prev_block

        error_handler = ErrorHandler(app_env_config)
        web3_interactor = Web3Interactor(app_env_config, abi)
        band_interactor = BandInteractor(app_env_config)
        await band_interactor.set_band_client()
        helpers = Helpers(app_env_config, web3_interactor, band_interactor)

        db.create_all()
        error_count = ErrorHandler.current_error_count(db)
        print(f"Error count: {error_count}")
        error_handler.check_error_limit(error_count)

        current_block = web3_interactor.get_block_number()
        print("(prev_block, current_block)", prev_block, current_block)

        while current_block == prev_block:
            time.sleep(5)
            current_block = web3_interactor.get_block_number()
            print("(prev_block, current_block)", prev_block, current_block)

        prev_block = current_block

        helpers.check_for_chain_fork(db, current_block)
        helpers.add_new_tasks_to_db(db, current_block)
        await helpers.request_random_data_on_band_and_relay(db)

        # Create a new task on Cloud Tasks
        create_task = CreateTask(create_task_config)
        create_task.create_new_task()

        # Transaction success, reset error count
        ErrorHandler.update_error_count(db, 0)

        return "Success", 200

    except (Exception, FunctionTimedOut) as e:
        message = f"<{AppEnvConfig.CHAIN}> Error running VRF Worker"
        print(f"{message}: {e}")

        error_count = ErrorHandler.current_error_count(db) + 1
        ErrorHandler.update_error_count(db, error_count)

        # Create a new task on Cloud Tasks
        create_task = CreateTask(create_task_config)
        create_task.create_new_task()

        return message, 500


if __name__ == "__main__":
    asyncio.run(app.run(debug=True, host=AppEnvConfig.HOST, port=AppEnvConfig.PORT))
