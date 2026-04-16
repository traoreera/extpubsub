from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Any

class PubSubProvider(ABC):
    
    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def publish(self, channel: str, event: dict) -> None:
        pass

    @abstractmethod
    async def stream(
        self, 
        channel: str, 
        user_id: Optional[str] = None, 
        filter_key: str = "user_id"
    ) -> AsyncGenerator[str, None]:
        pass
