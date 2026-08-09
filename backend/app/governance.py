from __future__ import annotations

import json
import os
from functools import lru_cache

from web3 import Web3


ABI = [
    {"inputs":[{"internalType":"uint256","name":"id","type":"uint256"}],"name":"canExecute","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"proposalCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"proposals","outputs":[{"internalType":"address","name":"proposer","type":"address"},{"internalType":"bytes32","name":"actionHash","type":"bytes32"},{"internalType":"string","name":"description","type":"string"},{"internalType":"uint64","name":"createdAt","type":"uint64"},{"internalType":"uint64","name":"votingEnds","type":"uint64"},{"internalType":"uint64","name":"executeAfter","type":"uint64"},{"internalType":"uint128","name":"yesVotes","type":"uint128"},{"internalType":"uint128","name":"noVotes","type":"uint128"},{"internalType":"bool","name":"executed","type":"bool"},{"internalType":"bool","name":"cancelled","type":"bool"}],"stateMutability":"view","type":"function"}
]


@lru_cache(maxsize=1)
def _client():
    rpc = os.getenv("TAR_CHAIN_RPC_URL", "")
    address = os.getenv("TAR_GOVERNANCE_ADDRESS", "")
    if not rpc or not address:
        return None, None
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 20}))
    contract = w3.eth.contract(address=Web3.to_checksum_address(address), abi=ABI)
    return w3, contract


def status() -> dict:
    w3, contract = _client()
    if not w3 or not contract:
        return {"configured": False}
    try:
        return {"configured": True, "connected": bool(w3.is_connected()), "chain_id": int(w3.eth.chain_id), "contract": contract.address, "proposal_count": int(contract.functions.proposalCount().call())}
    except Exception as exc:
        return {"configured": True, "connected": False, "error": str(exc)}


def proposal(proposal_id: int) -> dict:
    w3, contract = _client()
    if not w3 or not contract:
        raise RuntimeError("Blockchain governance is not configured")
    p = contract.functions.proposals(proposal_id).call()
    return {
        "id": proposal_id,
        "proposer": p[0],
        "action_hash": Web3.to_hex(p[1]),
        "description": p[2],
        "created_at": int(p[3]),
        "voting_ends": int(p[4]),
        "execute_after": int(p[5]),
        "yes_votes": int(p[6]),
        "no_votes": int(p[7]),
        "executed": bool(p[8]),
        "cancelled": bool(p[9]),
        "can_execute": bool(contract.functions.canExecute(proposal_id).call()),
    }
