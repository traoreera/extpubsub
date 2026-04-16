import asyncio
import json
import uuid
import logging
from typing import Optional, AsyncGenerator
from .base import PubSubProvider
from .section import HivemqConfig

logger = logging.getLogger(__name__)

# Note: Requires 'gmqtt' or similar async mqtt library
try:
    from gmqtt import Client as MQTTClient
except ImportError:
    MQTTClient = None

class HivemqAdapter(PubSubProvider):
    def __init__(self, config: HivemqConfig) -> None:
        self._conf = config
        self.client: Optional[MQTTClient] = None
        self._connected = asyncio.Event()
        self._messages = asyncio.Queue()

    def _on_message(self, client, topic, payload, qos, properties):
        try:
            data = json.loads(payload.decode())
            self._messages.put_nowait((topic, data))
        except Exception as e:
            logger.error(f"MQTT message parse error: {e}")

    def _on_connect(self, client, flags, rc, properties):
        self._connected.set()
        logger.info("Connected to HiveMQ")

    async def connect(self) -> None:
        if MQTTClient is None:
            raise ImportError("gmqtt is required for HivemqAdapter")
        
        url_parts = self._conf.url.replace("mqtt://", "").split(":")
        host = url_parts[0]
        port = int(url_parts[1]) if len(url_parts) > 1 else 1883

        self.client = MQTTClient(client_id=str(uuid.uuid4()))
        self.client.on_message = self._on_message
        self.client.on_connect = self._on_connect
        
        if self._conf.username:
            self.client.set_auth_credentials(self._conf.username, self._conf.password)

        await self.client.connect(host, port)
        await self._connected.wait()

    async def close(self) -> None:
        if self.client:
            await self.client.disconnect()

    async def publish(self, channel: str, event: dict) -> None:
        if not self.client:
            raise RuntimeError("HiveMQ not connected")
        self.client.publish(channel, json.dumps(event))

    async def stream(
        self, 
        channel: str, 
        user_id: Optional[str] = None, 
        filter_key: str = "user_id"
    ) -> AsyncGenerator[str, None]:
        if not self.client:
            raise RuntimeError("HiveMQ not connected")
        
        self.client.subscribe(channel)
        
        try:
            while True:
                topic, event = await self._messages.get()
                if topic == channel:
                    if user_id is None or event.get(filter_key) == user_id:
                        yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(self._conf.heartbeat)
        finally:
            self.client.unsubscribe(channel)
