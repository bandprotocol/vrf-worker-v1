#!/usr/bin/env bash
#
# migration.sh
# Usage: ./migration.sh input.env [output.yaml]
#

set -eo pipefail

if [[ -z "$1" ]]; then
  echo "Usage: $0 input.env [output.yaml]" >&2
  exit 1
fi

INPUT="$1"
OUTPUT="${2:-output.yaml}"

# load KEY=VALUE pairs (skip blank lines and comments)
while IFS='=' read -r KEY VAL; do
  # skip comments and empty lines
  [[ "$KEY" =~ ^[[:space:]]*# ]] && continue
  [[ -z "$KEY" ]] && continue
  # trim whitespace around key and value
  KEY="${KEY//[[:space:]]/}"
  VAL="${VAL#"${VAL%%[![:space:]]*}"}"
  VAL="${VAL%"${VAL##*[![:space:]]}"}"
  # export into shell variable
  declare "$KEY=$VAL"
done < "$INPUT"

# emit YAML
cat > "$OUTPUT" <<EOF
evm_chain_config:
  chain_id: "${CHAIN}"
  rpc_endpoint: "${EVM_JSON_RPC_ENDPOINTS}"
  vrf_provider_address: "${VRF_PROVIDER_ADDRESS}"
  vrf_lens_address: "${VRF_LENS_ADDRESS}"
  bridge_address: "${BRIDGE_ADDRESS}"
  private_key: "${WORKER_PK}"
  whitelisted_callers:
$(if [[ -n "$WHITELISTED_CALLERS" ]]; then
  IFS=','; for caller in $WHITELISTED_CALLERS; do
    caller_trimmed="$(echo "$caller" | xargs)"
    [[ -n "$caller_trimmed" ]] && echo "    - \"$caller_trimmed\""
  done
fi)
  start_nonce: ${START_NONCE}
  eip1559: ${SUPPORT_EIP1559:-true}

band_chain_config:
  grpc_endpoint: "${BAND_GRPC_ENDPOINTS}"
  mnemonic: "${BAND_MNEMONIC}"
  min_count: ${MIN_COUNT}
  ask_count: ${ASK_COUNT}
  prepare_gas: ${BAND_PREPARE_GAS}
  execute_gas: ${BAND_EXECUTE_GAS}
  ds_fee_limit: ${BAND_DS_FEE_LIMIT}
  gas_limit: ${BAND_GAS_LIMIT}
  gas_price: ${BAND_GAS_PRICE}
EOF

echo "Wrote converted config to $OUTPUT"
