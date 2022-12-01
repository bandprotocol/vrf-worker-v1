# Band VRF Worker

### What is VRF Worker?

VRF Worker is an off-chain service used for relaying VRF random value requests and results between the BandChain and the client chain (e.g. Ethereum). It works as follows:

1. The VRF Worker listens for incoming VRF random value requests from a VRF Contract on the client chain
2. The VRF Worker relays these requests to BandChain, and retrieves the generated VRF random values and the corresponding BandChain Merkle proofs
3. The proofs get relayed to the Bridge Contract, via the VRFProvider Contract, for verification
4. If the proofs are verified successfully, the VRF Worker returns the generated VRF random values back to the VRF contract

## Deployment

We provide scripts and instructions for local deployment and deployment on Google Cloud Platform. Note that the deployment procedures are currently only avaiable in Python.

### Folder structure

```
vrf_worker
   ├─ Dockerfile
   ├─ app
   │  ├─ app.py
   │  ├─ app_run_local.py
   │  └─ helpers
   │     ├─ band_interactor.py
   │     ├─ config.py
   │     ├─ create_task.py
   │     ├─ create_task_main.py
   │     ├─ database.py
   │     ├─ error_handler.py
   │     ├─ helpers.py
   │     ├─ web3_interactor.py
   ├─ scripts
   │  ├─ create_task.sh
   │  ├─ deploy.sh
   │  ├─ deploy.sh.example
   │  └─ deploy_local.sh
   └─ tests
      ├─ mock_data.py
      └─ test_helpers.py
```

#### Key files

| Files                 | Details                                                |
| :-------------------- | :----------------------------------------------------- |
| `app.py `             | Main entry point of the service for GCP                |
| `app_run_local.py`    | Main entry point for local deployment                  |
| `helpers.py`          | Helper with core logics                                |
| `web3_interactor.py`  | Helper to interact with Web3                           |
| `band_interactor.py`  | Helper to interact with Band Client                    |
| `error_handler.py`    | Helper to handle errors and notification               |
| `database.py`         | Helper to manage database interaction                  |
| `signatures.py `      | Helper to manage signature filtering                   |
| `create_task.py`      | Helper to create a new task on Cloud Tasks             |
| `create_task_main.py` | Entry point for creating a new task on Cloud Tasks     |
| `config.py`           | Helper to manage environment variables configuration   |
| `deploy.sh `          | Deploy script for Cloud Run                            |
| `deploy_local.sh `    | Deploy script for local deployment                     |
| `create_task.sh`      | Script for creating a new task on Cloud Tasks          |
| `Dockerfile `         | For preparing a Docker image to be used in `deploy.sh` |

---

### Deploy on local machine

1. Install dependency manager [Poetry](https://python-poetry.org/docs/) on your machine (if required)
    ```
    curl -sSL https://install.python-poetry.org | python3 -
    ```
2. Install dependencies from `poetry.lock`
   ```
   poetry install
   ```
3. Create a `.env` file from `.env.template` and update required environmental variables
4. Setup a database. The default for local deployment is SQLite. To connect to another the database, please update `SQLALCHEMY_DATABASE_URI` in `app/helpers/config.py` file
5. Run `deploy_local.sh` script to start the service. Note that the service will continue running until manually interupted.
   ```
   ./scripts/deploy_local.sh
   ```

---

### Deploy on Google Cloud Platform

**Tools used:** Cloud SQL, Cloud Tasks, Cloud Run

1. Setup Cloud SQL
   - Create a Cloud SQL instance (using PostgreSQL) with Private IP. Refer to this [guide](https://cloud.google.com/sql/docs/postgres/configure-private-ip).
   - Create a new database inside the Cloud SQL instance
2. Setup Cloud Tasks
   - Create a push queue on Cloud tasks. Refer to this [guide](https://cloud.google.com/tasks/docs/creating-queues)
   - Set `Max concurrent dispatches` to 1
   - Set `Max attempts` to 1
3. Prepare script for deploying the service
   - Install dependency manager [Poetry](https://python-poetry.org/docs/) on your machine (if required)
     ```
     curl -sSL https://install.python-poetry.org | python3 -
     ```
   - Install dependencies from `poetry.lock`
     ```
     poetry install
     ```
   - In `deploy.sh` file, fill out all environment variables (refer to `deploy.sh.example` and `.env.template` for examples). Note that some variables such as `CLOUD_RUN_URL` and `AUDIENCE` may not be known prior to the first deployment. These variables can be manually added in the Cloud Run service after deployment
4. Deploy the service on Cloud Run
   - Run `./deploy.sh` to build a Docker image and deploy the service on Cloud Run.
     ```
     ./scripts/deploy.sh
     ```
   - If a prompt to setup `gcloud auth login` appears, please follow the instruction
   - Once deployed successfully, create and reference the following secrets in the Cloud Run console:
     ```
     WORKER_PK
     BAND_MNEMONIC
     DB_PASSWORD
     ```
   - From the Cloud Run console, deploy a new revision after filling in any remaining environment variables (e.g. `CLOUD_RUN_URL` and `AUDIENCE`)
5. Create initial task on Cloud Tasks
   - Fill out all environment variables `.env`
   - Run `create_task.sh` script to create a new task in the Cloud Tasks queue
     ```
     ./scripts/create_task.sh
     ```
   - After the current task is finished, a new task will be created automatically by the service
   - The service will now continuously until the Cloud Tasks queue is paused or deleted
   - If there is an error in the automatic task creation by the service, you may run `create_task.sh` script to create a new task in the Cloud Tasks queue again.
