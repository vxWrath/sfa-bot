"""League-wide settings loaded from config.toml at startup.

Usage::

    from core import League

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

    # -- guild -----------------------------------------------------------------
    snowflake: int

    # -- roles -----------------------------------------------------------------
    commissioner_role_id: int
    vice_role_id: int
    staff_stats_role_id: int
    staff_media_role_id: int
    staff_mods_role_id: int
    staff_justice_role_id: int

    # -- channels --------------------------------------------------------------
    scheduling_channel_id: int
    gametimes_channel_id: int
    lfp_channel_id: int
    media_channel_ids: list[int]
    alerts_channel_id: int

    # -- alerts ----------------------------------------------------------------
    enabled_alerts: list[str]

    # -- misc ------------------------------------------------------------------
    logging_webhook_url: str

    @classmethod
    def load(cls) -> None:
        """Read ``config.toml`` and populate class variables."""
        with open("config.toml", "rb") as f:
            data = tomllib.load(f)

        for key, value in data.items():
            setattr(cls, key, value)

    @classmethod
    def save(cls, *keys: str) -> None:
        """Write current class variables back to ``config.toml``.

        Only the specified *keys* are updated; all other existing keys in
        the file are preserved.
        """
        if not keys:
            raise ValueError("League.save() requires at least one key")

        # Read existing data so we don't destroy unmentioned keys.
        try:
            with open("config.toml", "rb") as f:
                data = tomllib.load(f)
        except FileNotFoundError:
            data = {}

        for key in keys:
            data[key] = getattr(cls, key)

        with open("config.toml", "wb") as f:
            tomli_w.dump(data, f)
