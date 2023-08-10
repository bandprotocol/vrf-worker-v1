#!/bin/bash

# [Developer] Please fill in all the deployment environmental variables below
export SERVICE_NAME=
export REGION=
export DB_CONNECTION_NAME=
export PROJECT_ID=
export VPC_CONNECTOR=

# ENV variables 
export CHAIN=
export EVM_JSON_RPC_ENDPOINTS=
export BAND_GRPC_ENDPOINTS=laozi-testnet6.bandchain.org:443
export BAND_RPC_ENDPOINTS=https://rpc.laozi-testnet6.bandchain.org
export BAND_PROOF_URLS=https://laozi-testnet6.bandchain.org/api/oracle/proof/
export BAND_PREPARE_GAS=100000
export BAND_EXECUTE_GAS=400000
export BAND_GAS_LIMIT=800000
export MIN_COUNT=2
export ASK_COUNT=3
export VRF_PROVIDER_ADDRESS=
export VRF_LENS_ADDRESS=
export BRIDGE_ADDRESS=
export MAX_RELAY_PROOF_GAS=1200000
export START_NONCE=0
export DISCORD_WEBHOOK=
export WHITELISTED_CALLERS=
export WORKER_FEE_BAND=5000
export BLOCK_DIFF=
export SUPPORT_EIP1559=
export DB_HOST=
export DB_PORT=
export DB_USER=
export DB_NAME=
export PROJECT=
export QUEUE=
export LOCATION=
export CLOUD_RUN_URL=
export IN_SECONDS=
export DEADLINE=
export AUDIENCE=
export SERVICE_ACCOUNT_DETAIL=

# ENV to be referenced as secret on Cloud Run
# WORKER_PK
# BAND_MNEMONIC
# DB_PASSWORD


# Deploy Cloud Run
gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --no-allow-unauthenticated \
    --add-cloudsql-instances $DB_CONNECTION_NAME \
    --project $PROJECT_ID \
    --vpc-connector $VPC_CONNECTOR \
    --set-env-vars CHAIN=$CHAIN \
    --set-env-vars "^##^EVM_JSON_RPC_ENDPOINTS=$EVM_JSON_RPC_ENDPOINTS" \
    --set-env-vars "^##^BAND_GRPC_ENDPOINTS=$BAND_GRPC_ENDPOINTS" \
    --set-env-vars "^##^BAND_RPC_ENDPOINTS=$BAND_RPC_ENDPOINTS" \
    --set-env-vars "^##^BAND_PROOF_URLS=$BAND_PROOF_URLS" \
    --set-env-vars BAND_PREPARE_GAS=$BAND_PREPARE_GAS \
    --set-env-vars BAND_EXECUTE_GAS=$BAND_EXECUTE_GAS \
    --set-env-vars BAND_DS_FEE_LIMIT=$BAND_DS_FEE_LIMIT \
    --set-env-vars BAND_GAS_LIMIT=$BAND_GAS_LIMIT \
    --set-env-vars BAND_GAS_PRICE=$BAND_GAS_PRICE \
    --set-env-vars MIN_COUNT=$MIN_COUNT \
    --set-env-vars ASK_COUNT=$ASK_COUNT \
    --set-env-vars VRF_PROVIDER_ADDRESS=$VRF_PROVIDER_ADDRESS \
    --set-env-vars VRF_LENS_ADDRESS=$VRF_LENS_ADDRESS \
    --set-env-vars BRIDGE_ADDRESS=$BRIDGE_ADDRESS \
    --set-env-vars MAX_RELAY_PROOF_GAS=$MAX_RELAY_PROOF_GAS \
    --set-env-vars START_NONCE=$START_NONCE \
    --set-env-vars DISCORD_WEBHOOK=$DISCORD_WEBHOOK \
    --set-env-vars "^##^WHITELISTED_CALLERS=$WHITELISTED_CALLERS" \
    --set-env-vars WORKER_FEE_BAND=$WORKER_FEE_BAND \
    --set-env-vars BLOCK_DIFF=$BLOCK_DIFF \
    --set-env-vars SUPPORT_EIP1559=$SUPPORT_EIP1559 \
    --set-env-vars DB_HOST=$DB_HOST \
    --set-env-vars DB_PORT=$DB_PORT \
    --set-env-vars DB_USER=$DB_USER \
    --set-env-vars DB_NAME=$DB_NAME \
    --set-env-vars PROJECT=$PROJECT \
    --set-env-vars QUEUE=$QUEUE \
    --set-env-vars LOCATION=$LOCATION \
    --set-env-vars CLOUD_RUN_URL=$CLOUD_RUN_URL \
    --set-env-vars IN_SECONDS=$IN_SECONDS \
    --set-env-vars DEADLINE=$DEADLINE \
    --set-env-vars AUDIENCE=$AUDIENCE \
    --set-env-vars SERVICE_ACCOUNT_DETAIL=$SERVICE_ACCOUNT_DETAIL
