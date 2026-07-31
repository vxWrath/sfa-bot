"""Redis cache connection manager.

Usage::

    from core import Cache

    cache = Cache()
    await cache.connect()

    # All methods use path-based keys:
    await cache.set("sfa", "row", "players", "456", value=data, ex=300)
    profile = await cache.get("sfa", "profile", "player", "456", cls=PlayerProfile)

    # Multi-key delete takes raw key strings (use key_from_path):
    await cache.delete(
        cache.key_from_path("sfa", "row", "players", "456"),
        cache.key_from_path("sfa", "profile", "player", "456"),
    )

    # Hash operations:
    await cache.hash_set("sfa", "presence", "789", {"status": "online", "game": "Roblox"})
    status, missing = await cache.hash_get("sfa", "presence", "789", dict, fields=["status"])
    all_fields = await cache.hash_getall("sfa", "presence", "789")
"""

import asyncio
from collections.abc import Iterable
from typing import (
    Any,
    TypedDict,
    Unpack,
    overload,
)

import msgspec
import orjson
from redis.asyncio import ConnectionPool
from redis.asyncio import Redis as AsyncRedis
from redis.asyncio import RedisError

from .env import get_env
from .exceptions import SFAException
from .logging import get_logger

logger = get_logger("cache")

__all__ = [
    "Cache",
    "CacheError",
    "CacheNotConnected",
    "CacheOptions",
]


class CacheError(SFAException):
    """Raised when a cache operation fails."""


class CacheNotConnected(SFAException):
    """Raised when a cache operation is attempted before connecting to Redis."""


class CacheOptions(TypedDict, total=False):
    max_connections: int
    command_timeout: float
    connect_retries: int
    connect_retry_delay: float


class Cache:
    """Redis cache connection manager.

    Mirrors the ``Database`` class pattern: pool management, connect/close,
    and low-level data operations.  All methods catch Redis errors and degrade
    gracefully - the bot must work without Redis.

    Single-key operations (``get``, ``set``, ``exists``) take path segments
    that are joined with ``:`` to form the Redis key::

        await cache.get("sfa", "profile", "player", "789", cls=PlayerProfile)
        # Reads from key: sfa:profile:player:789

    Multi-key ``delete`` takes pre-built key strings so you can delete several
    keys in one round-trip.  Use :meth:`key_from_path` to build them::

        await cache.delete(
            cache.key_from_path("sfa", "row", "players", "789"),
            cache.key_from_path("sfa", "profile", "player", "789"),
        )

    Hash operations store multiple fields under a single key::

        await cache.hash_set("sfa", "presence", "789", {"status": "online"})
        status, missing = await cache.hash_get("sfa", "presence", "789", dict, fields=["status"])
    """

    def __init__(self, **kwargs: Unpack[CacheOptions]) -> None:
        self._max_connections = kwargs.get("max_connections", 10)
        self._command_timeout = kwargs.get("command_timeout", 5.0)
        self._connect_retries = kwargs.get("connect_retries", 5)
        self._connect_retry_delay = kwargs.get("connect_retry_delay", 1.0)

        self._redis: AsyncRedis | None = None
        self._connection_lock = asyncio.Lock()
        self._encoder = msgspec.json.Encoder()
        self._decoders: dict[type[Any], msgspec.json.Decoder[Any]] = {}

    # -- connection lifecycle -----------------------------------------------

    async def connect(self) -> None:
        """Connect to Redis with retries."""

        if self._redis is not None:
            return

        async with self._connection_lock:
            if self._redis is not None:
                return

            last_exception: Exception | None = None

            for attempt in range(1, self._connect_retries + 1):
                try:
                    pool = ConnectionPool.from_url(
                        get_env("REDIS_URL"),
                        max_connections=self._max_connections,
                        socket_connect_timeout=self._command_timeout,
                        socket_keepalive=True,
                        retry_on_timeout=True,
                        decode_responses=False,
                    )
                    self._redis = AsyncRedis(connection_pool=pool)

                    # Verify the connection actually works.
                    await self._redis.ping()

                    logger.info("Redis pool created (max_connections=%d)", self._max_connections)
                    return
                except (OSError, RedisError) as e:
                    last_exception = e
                    logger.warning(
                        "Redis connection attempt %d/%d failed: %s",
                        attempt,
                        self._connect_retries,
                        e,
                    )

                    if attempt < self._connect_retries:
                        await asyncio.sleep(self._connect_retry_delay * attempt)

            raise CacheError(f"Failed to connect to Redis after {self._connect_retries} attempts") from last_exception

    async def close(self) -> None:
        """Gracefully close the Redis connection pool."""

        if self._redis is None:
            return

        async with self._connection_lock:
            if self._redis is None:
                return

            pool = self._redis.connection_pool
            await self._redis.aclose()

            if pool is not None:
                await pool.disconnect()

            self._redis = None

        logger.info("Redis pool closed")

    @property
    def redis(self) -> AsyncRedis:
        """Get the underlying ``AsyncRedis`` instance."""

        if self._redis is None:
            raise CacheNotConnected("Cache.connect() must be called before use")

        return self._redis

    # -- key building -------------------------------------------------------

    @staticmethod
    def key_from_path(*path: Any) -> str:
        """Build a colon-delimited Redis key from path segments.

        Each segment is converted via ``str()``, so integers, snowflakes,
        and enum values all work without manual formatting::

            Cache.key_from_path("sfa", "profile", "player", 789)
            # → "sfa:profile:player:789"
        """
        return ":".join(str(p) for p in path)

    # -- single-key operations (path-based) ---------------------------------

    @overload
    async def get(self, *path: Any, cls: type[bytes]) -> bytes | None: ...

    @overload
    async def get[T: msgspec.Struct](self, *path: Any, cls: type[T]) -> T | None: ...

    @overload
    async def get(self, *path: Any, cls: type[dict[str, Any]]) -> dict[str, Any] | None: ...

    async def get(self, *path: Any, cls: type[Any], **redis_kwargs: Any) -> Any | None:
        """Get and decode a value at *path*.  Returns ``None`` on miss or Redis error.

        *cls* controls decoding:

        - ``bytes`` → raw bytes, no decoding
        - ``dict`` → decoded via ``orjson.loads``
        - ``msgspec.Struct`` subclass → decoded via a cached ``msgspec.json.Decoder``
        """
        key = self.key_from_path(*path)

        try:
            data = await self.redis.get(key, **redis_kwargs)
        except RedisError:
            logger.warning("Redis GET failed for key %r", key, exc_info=True)
            return None

        if data is None or cls is bytes:
            return data

        if cls is dict:
            return orjson.loads(data)

        if isinstance(cls, type) and issubclass(cls, msgspec.Struct):
            decoder = self._decoders.get(cls)
            if decoder is None:
                decoder = msgspec.json.Decoder(type=cls)
                self._decoders[cls] = decoder
            return decoder.decode(data)

        raise TypeError(f"Unsupported cls {cls!r}")

    async def set(self, *path: Any, value: msgspec.Struct | dict[str, Any] | bytes, **redis_kwargs: Any) -> bool:
        """Set a value at *path* with ex in seconds.  Returns ``False`` on Redis error.

        *value* is auto-encoded: ``msgspec.Struct`` → ``msgspec.json``,
        ``dict`` → ``orjson``, ``bytes`` → stored as-is.
        """
        key = self.key_from_path(*path)

        if type(value) is bytes:
            data = value
        elif type(value) is dict:
            data = orjson.dumps(value)
        elif isinstance(value, msgspec.Struct):
            data = self._encoder.encode(value)
        else:
            raise TypeError(f"Unsupported value type {type(value)!r}")

        try:
            return await self.redis.set(key, data, ex=redis_kwargs.pop("ex", 300), **redis_kwargs)  # type: ignore[arg-type]
        except RedisError:
            logger.warning("Redis SET failed for key %r", key, exc_info=True)
            return False

    async def exists(self, *path: Any) -> bool:
        """Return ``True`` if a key exists at *path*.  Returns ``False`` on Redis error."""

        if not path:
            return False

        key = self.key_from_path(*path)

        try:
            count = await self.redis.exists(key)
            return count > 0
        except RedisError:
            logger.warning("Redis EXISTS failed for key %r", key, exc_info=True)
            return False

    async def expire(self, *path: Any, ex: int, **redis_kwargs: Any) -> bool:
        """Set or update the expiry (in seconds) on an existing key.

        Returns ``True`` if the timeout was set, ``False`` if the key doesn't
        exist or on Redis error.
        """

        key = self.key_from_path(*path)

        try:
            return await self.redis.expire(key, ex, **redis_kwargs)
        except RedisError:
            logger.warning("Redis EXPIRE failed for key %r", key, exc_info=True)
            return False

    async def incr(self, *path: Any, amount: int = 1) -> int | None:
        """Atomically increment a counter at *path* by *amount*.

        Returns the new value, or ``None`` on Redis error.  If the key doesn't
        exist it is set to 0 before incrementing.
        """

        key = self.key_from_path(*path)

        try:
            return await self.redis.incrby(key, amount)
        except RedisError:
            logger.warning("Redis INCRBY failed for key %r", key, exc_info=True)
            return None

    # -- hash operations (path-based) ---------------------------------------

    @overload
    async def hash_get(
        self, *path: Any, cls: type[bytes], fields: Iterable[str]
    ) -> tuple[dict[str, bytes] | None, set[str]]: ...

    @overload
    async def hash_get[T: msgspec.Struct](
        self, *path: Any, cls: type[T], fields: Iterable[str]
    ) -> tuple[T | None, set[str]]: ...

    @overload
    async def hash_get[D: dict[str, Any]](
        self, *path: Any, cls: type[D], fields: Iterable[str]
    ) -> tuple[D | None, set[str]]: ...

    async def hash_get(self, *path: Any, cls: type[Any], fields: Iterable[str]) -> tuple[Any | None, set[str]]:
        """Get one or more fields from a hash at *path*.

        *cls* controls how field values are decoded:

        - ``dict[str, bytes]`` → raw bytes values, no decoding
        - ``dict[str, Any]`` → each value decoded via ``orjson.loads``
        - ``msgspec.Struct`` → field mapping decoded into the struct type

        Returns ``(cls or None, missing fields)``
        """

        key = self.key_from_path(*path)

        ordered_fields = sorted(fields)
        try:
            hmget: list[bytes | None] = await self.redis.hmget(key, ordered_fields)  # type: ignore
        except RedisError:
            logger.warning("Redis HMGET failed for key %r", key, exc_info=True)
            return (None, set(fields))

        try:
            items = zip(ordered_fields, hmget, strict=True)
        except ValueError:
            logger.warning(
                "Redis HMGET field count mismatch for key %r. Requested %d, got %d",
                key,
                len(ordered_fields),
                len(hmget),
            )
            return (None, set(fields))

        mapping: dict[str, Any] = {}
        missing: set[str] = set()

        for field, value in items:
            field_name = field.decode() if isinstance(field, bytes) else field

            if value is None:
                missing.add(field_name)
                continue

            if cls is dict:
                mapping[field_name] = orjson.loads(value)

            elif cls is bytes or issubclass(cls, msgspec.Struct):
                mapping[field_name] = value

            else:
                raise TypeError(f"Unsupported cls {cls!r}")

        if cls is bytes or cls is dict:
            return (mapping, missing)

        return (msgspec.convert(mapping, type=cls, strict=False), missing)

    @overload
    async def hash_getall(self, *path: Any, cls: type[bytes]) -> dict[str, bytes] | None: ...

    @overload
    async def hash_getall[T: msgspec.Struct](self, *path: Any, cls: type[T]) -> T | None: ...

    @overload
    async def hash_getall[D: dict[str, Any]](self, *path: Any, cls: type[D]) -> D | None: ...

    async def hash_getall(self, *path: Any, cls: type[Any]) -> Any | None:
        """Get all fields from a hash at *path*.

        *cls* controls how field values are decoded:

        - ``dict[str, bytes]`` → raw bytes values, no decoding
        - ``dict[str, Any]`` → each value decoded via ``orjson.loads``
        - ``msgspec.Struct`` → field mapping decoded into the struct type

        Returns ``None`` if the key doesn't exist or on Redis error.
        """

        key = self.key_from_path(*path)

        try:
            hgetall: dict[bytes, bytes] = await self.redis.hgetall(key)  # type: ignore
        except RedisError:
            logger.warning("Redis HGETALL failed for key %r", key, exc_info=True)
            return None

        # Redis auto-deletes a hash when its last field is removed,
        # so an empty hgetall always means the key doesn't exist.
        if not hgetall:
            return None

        mapping: dict[str, Any] = {}

        for field, value in hgetall.items():
            if cls is dict:
                mapping[field.decode()] = orjson.loads(value)

            elif cls is bytes or issubclass(cls, msgspec.Struct):
                mapping[field.decode()] = value

            else:
                raise TypeError(f"Unsupported cls {cls!r}")

        if cls is bytes or cls is dict:
            return mapping

        return msgspec.convert(mapping, type=cls, strict=False)

    async def hash_set(
        self,
        *path: Any,
        instance: msgspec.Struct | dict[str, Any],
        **redis_kwargs: Any,
    ) -> int:
        """Set all fields of a hash from a ``dict`` or ``msgspec.Struct``.

        Returns the number of fields added, or 0 on Redis error.
        """

        key = self.key_from_path(*path)

        if isinstance(instance, msgspec.Struct):
            data: dict[str, Any] = msgspec.to_builtins(instance)
        else:
            data = instance

        if not data:
            return 0

        try:
            async with self.redis.pipeline() as pipe:
                await pipe.hset(key, mapping=data, **redis_kwargs)  # type: ignore
                await pipe.expire(key, time=redis_kwargs.pop("ex", 300))

                commands = await pipe.execute()
                return commands[0]

        except RedisError:
            logger.warning("Redis HSET failed for key %r", key, exc_info=True)
            return 0

    async def hash_delete(self, *path: Any, fields: Iterable[str]) -> int:
        """Delete one or more fields from a hash at *path*.

        Returns the number of fields removed, or 0 on Redis error.
        """

        key = self.key_from_path(*path)

        try:
            return await self.redis.hdel(key, *fields)
        except RedisError:
            logger.warning("Redis HDEL failed for key %r", key, exc_info=True)
            return 0

    # -- multi-key operations (raw key strings) -----------------------------

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys.  Returns count deleted, or 0 on Redis error.

        Keys are pre-built strings.  Use :meth:`key_from_path` to construct them::

            await cache.delete(
                cache.key_from_path("sfa", "row", "players", "789"),
                cache.key_from_path("sfa", "profile", "player", "789"),
            )
        """

        if not keys:
            return 0

        try:
            return await self.redis.delete(*keys)
        except RedisError:
            logger.warning("Redis DELETE failed for keys %r", keys, exc_info=True)
            return 0

    async def keys(self, pattern: str) -> list[str]:
        """Return keys matching *pattern* via ``SCAN``.  Returns empty list on Redis error.

        ``SCAN`` iterates the keyspace in small batches so it won't block
        the server.  Still prefer well-scoped patterns like
        ``sfa:profile:player:*`` — never ``*`` in production.
        """

        try:
            result: list[str] = []
            cursor = 0
            while True:
                scan: tuple[int, list[bytes]] = await self.redis.scan(cursor, match=pattern)  # type: ignore
                cursor, batch = scan

                result.extend(k.decode() for k in batch)

                if cursor == 0:
                    break

            return result
        except RedisError:
            logger.warning("Redis SCAN failed for pattern %r", pattern, exc_info=True)
            return []

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching *pattern*.  Returns count deleted."""

        keys = await self.keys(pattern)
        if not keys:
            return 0

        return await self.delete(*keys)
