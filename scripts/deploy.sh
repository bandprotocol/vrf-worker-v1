#!/bin/bash

# [Developer] Please fill in all the deployment environmental variables below
export SERVICE_NAME=
export REGION=
export DB_CONNECTION_NAME=
export PROJECT_ID=
export VPC_CONNECTOR=

# ENV variables 
export CHAIN=
export POA_CHAIN=
export JSON_RPC_ENDPOINT=
export BAND_RPC=laozi-testnet5.bandchain.org
export BAND_RPC_PORT=443
export BAND_RPC_BLOCK=https://rpc.laozi-testnet5.bandchain.org
export BAND_PROOF_URL=https://laozi-testnet5.bandchain.org/api/oracle/proof/
export VRF_PROVIDER_ADDRESS=
export VRF_LENS_ADDRESS=
export BRIDGE_ADDRESS=
export START_NONCE=0
export DISCORD_WEBHOOK=
export WHITELISTED_CALLERS=
export WORKER_FEE_BAND=
export BLOCK_DIFF=
export SUPPORT_EIP1559=
export INSTANCE_HOST=
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
    --set-env-vars POA_CHAIN=$POA_CHAIN \
    --set-env-vars "^##^JSON_RPC_ENDPOINT=$JSON_RPC_ENDPOINT" \
    --set-env-vars "^##^BAND_RPC=$BAND_RPC" \
    --set-env-vars BAND_RPC_PORT=$BAND_RPC_PORT \
    --set-env-vars BAND_RPC_BLOCK=$BAND_RPC_BLOCK \
    --set-env-vars BAND_PROOF_URL=$BAND_PROOF_URL \
    --set-env-vars VRF_PROVIDER_ADDRESS=$VRF_PROVIDER_ADDRESS \
    --set-env-vars VRF_LENS_ADDRESS=$VRF_LENS_ADDRESS \
    --set-env-vars BRIDGE_ADDRESS=$BRIDGE_ADDRESS \
    --set-env-vars START_NONCE=$START_NONCE \
    --set-env-vars DISCORD_WEBHOOK=$DISCORD_WEBHOOK \
    --set-env-vars "^##^WHITELISTED_CALLERS=$WHITELISTED_CALLERS" \
    --set-env-vars WORKER_FEE_BAND=$WORKER_FEE_BAND \
    --set-env-vars BLOCK_DIFF=$BLOCK_DIFF \
    --set-env-vars SUPPORT_EIP1559=$SUPPORT_EIP1559 \
    --set-env-vars INSTANCE_HOST=$INSTANCE_HOST \
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
