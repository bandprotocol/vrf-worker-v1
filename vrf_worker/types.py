from dataclasses import dataclass


@dataclass
class Task:
    is_resolved: bool
    time: int
    caller: str
    task_fee: int
    seed: bytes
    result: bytes
    client_seed: str
