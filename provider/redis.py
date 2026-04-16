import json
import asyncio
import logging
from .section import RedisConfig
from .base import PubSubProvider
from typing import Optional, AsyncGenerator
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

class RedisAdapter(PubSubProvider):

    def __init__(self, config: RedisConfig) -> None:
        self._conf = config
        self.svc: Optional[Redis] = None
        self._pool: Optional[ConnectionPool] = None

    async def connect(self):
        try:
            self._pool = ConnectionPool.from_url(
                url=self._conf.url,
                decode_responses=True,
                max_connections=10
            )
            self.svc = Redis(connection_pool=self._pool)
            # Test connection
            await self.svc.ping()
            logger.info(f"Connected to Redis at {self._conf.url}")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def close(self):
        if self.svc:
            await self.svc.close()
        if self._pool:
            await self._pool.disconnect()
        return True, "closed"
    
    async def publish(self, channel: str, event: dict):
        if not self.svc:
            raise RuntimeError("Redis provider not initialized. Call connect() first.")
        
        try:
            await self.svc.publish(
                channel=channel, message=json.dumps(event)
            )
        except RedisError as e:
            logger.error(f"Error publishing to Redis: {e}")
            raise

    async def stream(
        self,
        channel: str,
        user_id: Optional[str] = None,
        filter_key: str = "user_id",
    ) -> AsyncGenerator[str, None]:
        if not self.svc:
            raise RuntimeError("Redis provider not initialized")

        pubsub = self.svc.pubsub()
        await pubsub.subscribe(channel)

        try:
            while True:
                try:
                    msg = await pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0
                    )

                    if msg and msg["type"] == "message":
                        event = json.loads(msg["data"])

                        if user_id is None or event.get(filter_key) == user_id:
                            yield f"data: {json.dumps(event)}\n\n"

                except RedisError as e:
                    logger.error(f"Redis stream error: {e}")
                    await asyncio.sleep(1) # Backoff
                
                await asyncio.sleep(self._conf.heartbeat)

        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
