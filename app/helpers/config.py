from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class EvmChainConfig:
    CHAIN = os.getenv("CHAIN")
    SUPPORT_EIP1559 = os.getenv("SUPPORT_EIP1559", "False").lower() == "true"
    EVM_JSON_RPC_ENDPOINTS = os.getenv("EVM_JSON_RPC_ENDPOINTS", "").split(",")
    VRF_PROVIDER_ADDRESS = os.getenv("VRF_PROVIDER_ADDRESS")
    VRF_LENS_ADDRESS = os.getenv("VRF_LENS_ADDRESS")
    BRIDGE_ADDRESS = os.getenv("BRIDGE_ADDRESS")
    WORKER_PK = os.getenv("WORKER_PK")
    START_NONCE = int(os.getenv("START_NONCE", 0))
    WHITELISTED_CALLERS = set(os.getenv("WHITELISTED_CALLERS", "").split(","))
    BLOCK_DIFF = int(os.getenv("BLOCK_DIFF", 10))
    MAX_RELAY_PROOF_GAS = int(os.getenv("MAX_RELAY_PROOF_GAS", 1200000))


@dataclass
class BandChainConfig:
    BAND_GRPC_ENDPOINTS = os.getenv("BAND_GRPC_ENDPOINTS", "laozi-testnet6.bandchain.org:443").split(",")
    BAND_RPC_ENDPOINTS = os.getenv("BAND_RPC_ENDPOINTS", "https://rpc.laozi-testnet6.bandchain.org").split(",")
    BAND_PROOF_URLS = os.getenv("BAND_PROOF_URLS", "https://laozi-testnet6.bandchain.org/api/oracle/proof").split(",")
    BAND_MNEMONIC = os.getenv("BAND_MNEMONIC")
    BAND_PREPARE_GAS = int(os.getenv("BAND_PREPARE_GAS", 100000))
    BAND_EXECUTE_GAS = int(os.getenv("BAND_EXECUTE_GAS", 400000))
    BAND_DS_FEE_LIMIT = os.getenv("BAND_DS_FEE_LIMIT", 48)
    BAND_GAS_LIMIT = int(os.getenv("BAND_GAS_LIMIT", 800000))
    BAND_GAS_PRICE = float(os.getenv("BAND_GAS_PRICE", 0.0025))
    MIN_COUNT = int(os.getenv("MIN_COUNT", 2))
    ASK_COUNT = int(os.getenv("ASK_COUNT", 3))


@dataclass
class NotificationConfig:
    DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")


@dataclass
class CreateTaskConfig:
    PROJECT = os.getenv("PROJECT")
    QUEUE = os.getenv("QUEUE")
    LOCATION = os.getenv("LOCATION")
    CLOUD_RUN_URL = os.getenv("CLOUD_RUN_URL")
    IN_SECONDS = int(os.getenv("IN_SECONDS", 0))
    DEADLINE = int(os.getenv("DEADLINE", 0))
    AUDIENCE = os.getenv("AUDIENCE")
    SERVICE_ACCOUNT_DETAIL = os.getenv("SERVICE_ACCOUNT_DETAIL")


@dataclass
class DbConfig:
    SCHEDULER_API_ENABLED = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")

    RUN_LOCAL = os.getenv("RUN_LOCAL", "True").lower() == "true"
    if RUN_LOCAL:
        SQLALCHEMY_DATABASE_URI = "sqlite:///{}".format(os.path.join(os.path.dirname(__file__), "vrf_worker.db"))
    else:
        SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


@dataclass
class Abi:
    VRF_PROVIDER_ABI = [
        {
            "inputs": [
                {"internalType": "bytes", "name": "_proof", "type": "bytes"},
                {"internalType": "uint64", "name": "_taskNonce", "type": "uint64"},
            ],
            "name": "relayProof",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "taskNonce",
            "outputs": [{"internalType": "uint64", "name": "", "type": "uint64"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "oracleScriptID",
            "outputs": [{"internalType": "uint64", "name": "", "type": "uint64"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]

    VRF_LENS_ABI = [
        {
            "inputs": [{"internalType": "uint64[]", "name": "nonces", "type": "uint64[]"}],
            "name": "getTasksBulk",
            "outputs": [
                {
                    "components": [
                        {"internalType": "bool", "name": "isResolved", "type": "bool"},
                        {"internalType": "uint64", "name": "time", "type": "uint64"},
                        {"internalType": "address", "name": "caller", "type": "address"},
                        {"internalType": "uint256", "name": "taskFee", "type": "uint256"},
                        {"internalType": "bytes32", "name": "seed", "type": "bytes32"},
                        {"internalType": "bytes32", "name": "result", "type": "bytes32"},
                        {"internalType": "bytes", "name": "clientSeed", "type": "bytes"},
                    ],
                    "internalType": "struct VRFLensV2.Task[]",
                    "name": "",
                    "type": "tuple[]",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "provider",
            "outputs": [{"internalType": "contract IVRFProviderViewOnly", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]

    BRIDGE_ABI = [
        {
            "inputs": [],
            "name": "encodedChainID",
            "outputs": [{"internalType": "bytes", "name": "", "type": "bytes"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "getAllValidatorPowers",
            "outputs": [
                {
                    "components": [
                        {"internalType": "address", "name": "addr", "type": "address"},
                        {"internalType": "uint256", "name": "power", "type": "uint256"},
                    ],
                    "internalType": "struct Bridge.ValidatorWithPower[]",
                    "name": "",
                    "type": "tuple[]",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "components": [
                        {"internalType": "bytes32", "name": "oracleIAVLStateHash", "type": "bytes32"},
                        {"internalType": "bytes32", "name": "paramsStoreMerkleHash", "type": "bytes32"},
                        {"internalType": "bytes32", "name": "slashingToStakingStoresMerkleHash", "type": "bytes32"},
                        {"internalType": "bytes32", "name": "govToMintStoresMerkleHash", "type": "bytes32"},
                        {"internalType": "bytes32", "name": "authToFeegrantStoresMerkleHash", "type": "bytes32"},
                        {"internalType": "bytes32", "name": "transferToUpgradeStoresMerkleHash", "type": "bytes32"},
                    ],
                    "internalType": "struct MultiStore.Data",
                    "name": "multiStore",
                    "type": "tuple",
                },
                {
                    "components": [
                        {"internalType": "bytes32", "name": "versionAndChainIdHash", "type": "bytes32"},
                        {"internalType": "uint64", "name": "height", "type": "uint64"},
                        {"internalType": "uint64", "name": "timeSecond", "type": "uint64"},
                        {"internalType": "uint32", "name": "timeNanoSecondFraction", "type": "uint32"},
                        {"internalType": "bytes32", "name": "lastBlockIdAndOther", "type": "bytes32"},
                        {"internalType": "bytes32", "name": "nextValidatorHashAndConsensusHash", "type": "bytes32"},
                        {"internalType": "bytes32", "name": "lastResultsHash", "type": "bytes32"},
                        {"internalType": "bytes32", "name": "evidenceAndProposerHash", "type": "bytes32"},
                    ],
                    "internalType": "struct BlockHeaderMerkleParts.Data",
                    "name": "merkleParts",
                    "type": "tuple",
                },
                {
                    "components": [
                        {"internalType": "bytes", "name": "signedDataPrefix", "type": "bytes"},
                        {"internalType": "bytes", "name": "signedDataSuffix", "type": "bytes"},
                    ],
                    "internalType": "struct CommonEncodedVotePart.Data",
                    "name": "commonEncodedVotePart",
                    "type": "tuple",
                },
                {
                    "components": [
                        {"internalType": "bytes32", "name": "r", "type": "bytes32"},
                        {"internalType": "bytes32", "name": "s", "type": "bytes32"},
                        {"internalType": "uint8", "name": "v", "type": "uint8"},
                        {"internalType": "bytes", "name": "encodedTimestamp", "type": "bytes"},
                    ],
                    "internalType": "struct TMSignature.Data[]",
                    "name": "signatures",
                    "type": "tuple[]",
                },
            ],
            "name": "relayBlock",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ]
