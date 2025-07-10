# Band VRF Worker

## What is VRF Worker?

VRF Worker is an off-chain service used for relaying VRF random value requests and results between the BandChain and the client chain (e.g. Ethereum). It works as follows:

1. The VRF Worker listens for incoming VRF random value requests from a VRF Contract on the client chain
2. The VRF Worker relays these requests to BandChain, and retrieves the generated VRF random values and the corresponding BandChain Merkle proofs
3. The proofs get relayed to the Bridge Contract, via the VRFProvider Contract, for verification
4. If the proofs are verified successfully, the VRF Worker returns the generated VRF random values back to the VRF contract

## Setup

### Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package installer

### Installation Steps

1. Copy the example config file and adjust as needed:
   ```sh
   cp config.yaml.example config.yaml
   # Edit config.yaml to match your environment and credentials
   ```
2. Run the worker:
   ```sh
   # Run worker with default path for config file
   uv run main.py 
   ```
   ```sh
   # Run worker with path to config file
   uv run main.py --config config.yaml
   ```   

## License

Copyright 2023 Band Protocol

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

```text
http://www.apache.org/licenses/LICENSE-2.0
```

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
