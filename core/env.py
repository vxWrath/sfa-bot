import os
from typing import Any

__all__ = (
    "get_env",
    "get_stage",
    "is_dev",
    "is_production",
)


def get_env(name: str, default: Any | None = None) -> str:
    value = os.getenv(key=name, default=default)

    if value is None:
        raise OSError(f"Environment variable '{name}' is not set.")

    return value


def get_stage() -> str:
    stage = get_env("STAGE", "dev").lower()
    return stage.casefold()


_PRODUCTION_STAGES: frozenset[str] = frozenset({"prod", "production"})


def is_production() -> bool:
    return get_stage() in _PRODUCTION_STAGES


def is_dev() -> bool:
    return get_stage() == "dev"
