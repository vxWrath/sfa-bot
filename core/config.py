"""Guild configuration loaded from config.toml at startup.

Usage::

    from sfa_bot.config import League

    League.load()
    print(League.snowflake)

    League.snowflake = 123456789012345678
    League.save("snowflake")
"""

import tomllib

import tomli_w


class League:
    """League-wide settings stored as class variables.

    Call ``League.load()`` once at startup to populate from disk,
    then access values directly as ``League.snowflake``.

    Call ``League.save()`` to write changes back to disk.
    """

    snowflake: int = 0

    @classmethod
    def load(cls) -> None:
        """Read ``config.toml`` and populate class variables."""
        with open("config.toml", "rb") as f:
            data = tomllib.load(f)

        for key, value in data.items():
            setattr(cls, key, value)

    @classmethod
    def save(cls, *keys: str) -> None:
        """Write current class variables back to ``config.toml``."""
        if not keys:
            raise ValueError("League.save() requires at least one key")

        data = {key: getattr(cls, key) for key in keys}

        with open("config.toml", "wb") as f:
            tomli_w.dump(data, f)
