from dataclasses import dataclass


@dataclass(frozen=True)
class Setting:
    key: str
    value: str
