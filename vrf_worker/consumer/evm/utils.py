import hashlib

from eth_abi import decode, encode
from eth_account.account import Account

from vrf_worker.consumer.evm.types import RELAY_DATA_TYPES

Signature = tuple[bytes, bytes, bytes, bytes]


def trim_proof(
    evm_proof_bytes: bytes,
    block_hash: bytes,
    encoded_band_chain_id: str,
    validator_power: dict[str, int],
) -> bytes:
    """Deconstructs the proof and reconstructs it with only the signatures to achieve 2/3 of the total power.

    Args:
        evm_proof_bytes (bytes): The EVM proof bytes.
        block_hash (str): The block hash.
        encoded_band_chain_id (str): The encoded BandChain ID.

    Returns:
        bytes: The trimmed proof.
    """
    relay_data, verify_data = decode(("bytes", "bytes"), evm_proof_bytes)
    multi_store, merkle_parts, cevp, sigs = decode(RELAY_DATA_TYPES, relay_data)
    minimal_sigs = _trim_signatures_by_power(block_hash, cevp, sigs, encoded_band_chain_id, validator_power)
    minimized_relay_data = encode(RELAY_DATA_TYPES, (multi_store, merkle_parts, cevp, minimal_sigs))
    trimmed_proof = encode(("bytes", "bytes"), (minimized_relay_data, verify_data))

    return trimmed_proof


def _trim_signatures_by_power(
    block_hash: bytes,
    cevp: bytes,
    signatures: list[Signature],
    encoded_band_chain_id: bytes,
    validator_power: dict[str, int],
) -> bytes:
    total_power = sum(validator_power.values())
    try:
        common = cevp[0] + block_hash + cevp[1]
        addresses = _recover_addresses(signatures, common, encoded_band_chain_id)

        vps = []
        for addr, sig in zip(addresses, signatures):
            if addr.lower() in validator_power:
                power = validator_power[addr]
                vps.append((addr, sig, power))

        # reorder by power in descending order
        vps = sorted(vps, key=lambda vp: vp[2], reverse=True)
        accumulated_power = 0
        for i in range(len(vps)):
            accumulated_power += vps[i][2]
            if accumulated_power * 3 > total_power * 2:
                ordered_by_address = sorted(vps[: i + 1], key=lambda vp: int(vp[0], 16))
                return [vp[1] for vp in ordered_by_address]
        raise Exception("Accumulated power does not exceed 2/3 of total power")
    except Exception as e:
        raise Exception(f"failed to trim necessary signatures: {e}")


def _recover_addresses(signatures: list[Signature], common: bytes, encoded_band_chain_id: bytes) -> list[str]:
    try:
        return [_recover_address(signature, common, encoded_band_chain_id) for signature in signatures]
    except Exception as e:
        raise Exception(f"failed to recover addresses: {e}")


def _recover_address(signature: Signature, common: bytes, encoded_band_chain_id: bytes) -> str:
    (r, s, v, encoded_timestamp) = signature
    msg = common + bytes([42, len(encoded_timestamp)]) + encoded_timestamp + encoded_band_chain_id
    prefixed_msg = bytes([len(msg)]) + msg
    msg_hash = hashlib.sha256(prefixed_msg).digest()
    address = Account._recover_hash(msg_hash, vrs=(v, r, s)).lower()
    return address
