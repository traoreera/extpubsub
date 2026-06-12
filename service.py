from typing import Any, AsyncGenerator, List, Optional

from xcore.services import BaseService, ServiceStatus

from .provider import (HivemqAdapter, MemoryAdapter, PubSubConf,
                       PubSubProvider, RedisAdapter)


class PubSubClient(BaseService):
    """
    Extension PubSub pour XCore.
    Cette classe est instanciée par le ServiceContainer de XCore
    qui lui passe la section 'pubsub' du fichier xcore.yaml.
    """

    name = "pubsub"

    def __init__(self, config: dict) -> None:
        super().__init__()
        self._status = ServiceStatus.INITIALIZING

        self.conf = PubSubConf(**config)
        self.provider: Optional[PubSubProvider] = None

        if self.conf.provider == 'redis':
            self.provider = RedisAdapter(config=self.conf.redis)
        elif self.conf.provider == 'hivemq':
            self.provider = HivemqAdapter(config=self.conf.hivemq)
        elif self.conf.provider == 'memory':
            self.provider = MemoryAdapter(config=self.conf.memory)

        self._status = ServiceStatus.READY

    async def init(self) -> None:
        if self.provider:
            await self.provider.connect()
            self._status = ServiceStatus.READY
        else:
            self._status = ServiceStatus.DEGRADED

    async def shutdown(self) -> None:
        if self.provider:
            await self.provider.close()
        self._status = ServiceStatus.STOPPED

    async def publish(self, channel: str, identified: str, msg: str) -> None:
        """Publie un message sur un channel."""
        if not self.provider:
            raise RuntimeError("PubSub provider non initialisé")
        await self.provider.publish(channel, {"user_id": identified, "text": msg})

    async def stream(
        self,
        channel: str,
        identified: str,
        filter_key: str = "user_id"
    ) -> AsyncGenerator[str, None]:
        """Stream de messages compatible SSE."""
        if not self.provider:
            raise RuntimeError("PubSub provider non initialisé")
        async for chunk in self.provider.stream(channel, identified, filter_key):
            yield chunk

    async def bulk_publish(self, channel: str, identified: List[str], msg: str) -> None:
        """Publie un message à plusieurs destinataires."""
        for user_id in identified:
            await self.publish(channel, user_id, msg)

    def get_status(self) -> dict[str, Any]:
        return {
            "provider": self.conf.provider,
            "status": self._status,
            "is_ready": self.is_ready,
        }

    async def health_check(self) -> tuple[bool, str]:
        if self.provider:
            return True, "service working"
        return False, "service not working"

    def status(self):

        return {
            "provider": self.conf.provider,
            "status": self._status.value
        }
