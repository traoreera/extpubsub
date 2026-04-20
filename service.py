from .provider import (
    HivemqAdapter, 
    RedisAdapter, 
    MemoryAdapter, 
    PubSubConf, 
    PubSubProvider
)
from xcore.services import BaseService, ServiceStatus
from typing import Any, List, Optional


class PubSubclient(BaseService):
    """
    Extension PubSub pour XCore.
    Cette classe est instanciée par le ServiceContainer de XCore
    qui lui passe la section 'pubsub' du fichier xcore.yaml.
    """

    name = "pubsub" # Nom standard pour l'accès via xcore.services.pubsub

    def __init__(self, config: dict) -> None:
        super().__init__()
        self._status = ServiceStatus.INITIALIZING
        
        # Validation via Pydantic de la section de config passée par xcore
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

    async def shutdown(self) -> None:
        if self.provider:
            await self.provider.close()
            self._status = ServiceStatus.STOPPED

    
    async def publish(self, channel: str, identified: str, msg: str):
        """Action exposée pour publier un message"""
        if self.provider:
            await self.provider.publish(channel, {"user_id": identified, "text": msg})

    
    async def stream(self, channel: str, identified: str, filter_key: str = "user_id"):
        """Action exposée pour streamer des messages (compatible SSE)"""
        if self.provider:
            return self.provider.stream(channel, identified, filter_key)

    
    async def bulk_publish(self, channel: str, identified: List[str], msg: str):
        """Action exposée pour l'envoi groupé"""
        if self.provider:
            for u in identified:
                await self.publish(channel, u, msg)
