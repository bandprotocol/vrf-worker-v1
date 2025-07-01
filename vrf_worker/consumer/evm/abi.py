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
        "outputs": [
            {
                "internalType": "contract IVRFProviderViewOnly",
                "name": "",
                "type": "address",
            }
        ],
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
                    {
                        "internalType": "bytes32",
                        "name": "oracleIAVLStateHash",
                        "type": "bytes32",
                    },
                    {
                        "internalType": "bytes32",
                        "name": "paramsStoreMerkleHash",
                        "type": "bytes32",
                    },
                    {
                        "internalType": "bytes32",
                        "name": "slashingToStakingStoresMerkleHash",
                        "type": "bytes32",
                    },
                    {
                        "internalType": "bytes32",
                        "name": "govToMintStoresMerkleHash",
                        "type": "bytes32",
                    },
                    {
                        "internalType": "bytes32",
                        "name": "authToFeegrantStoresMerkleHash",
                        "type": "bytes32",
                    },
                    {
                        "internalType": "bytes32",
                        "name": "transferToUpgradeStoresMerkleHash",
                        "type": "bytes32",
                    },
                ],
                "internalType": "struct MultiStore.Data",
                "name": "multiStore",
                "type": "tuple",
            },
            {
                "components": [
                    {
                        "internalType": "bytes32",
                        "name": "versionAndChainIdHash",
                        "type": "bytes32",
                    },
                    {"internalType": "uint64", "name": "height", "type": "uint64"},
                    {"internalType": "uint64", "name": "timeSecond", "type": "uint64"},
                    {
                        "internalType": "uint32",
                        "name": "timeNanoSecondFraction",
                        "type": "uint32",
                    },
                    {
                        "internalType": "bytes32",
                        "name": "lastBlockIdAndOther",
                        "type": "bytes32",
                    },
                    {
                        "internalType": "bytes32",
                        "name": "nextValidatorHashAndConsensusHash",
                        "type": "bytes32",
                    },
                    {
                        "internalType": "bytes32",
                        "name": "lastResultsHash",
                        "type": "bytes32",
                    },
                    {
                        "internalType": "bytes32",
                        "name": "evidenceAndProposerHash",
                        "type": "bytes32",
                    },
                ],
                "internalType": "struct BlockHeaderMerkleParts.Data",
                "name": "merkleParts",
                "type": "tuple",
            },
            {
                "components": [
                    {
                        "internalType": "bytes",
                        "name": "signedDataPrefix",
                        "type": "bytes",
                    },
                    {
                        "internalType": "bytes",
                        "name": "signedDataSuffix",
                        "type": "bytes",
                    },
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
                    {
                        "internalType": "bytes",
                        "name": "encodedTimestamp",
                        "type": "bytes",
                    },
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
