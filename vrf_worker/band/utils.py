from pyband.proto.cosmos.base.abci.v1beta1 import TxResponse
from typing import Optional


def find_request_id(tx_resp: TxResponse) -> Optional[int]:
    """Finds the request id from the tx response.

    Args:
        tx_resp (TxResponse): The tx response.

    Returns:
        Optional[int]: The request id. If not found, returns None.
    """
    for event in tx_resp.events:
        if event.type == "request":
            for attr in event.attributes:
                if attr.key == "id":
                    return int(attr.value)

    return None
