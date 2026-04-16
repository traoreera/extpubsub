from pydantic import BaseModel, Field
from typing import Literal, Optional


class ProviderConfig(BaseModel):
    url: str
    heartbeat: float = 0.01


class RedisConfig(ProviderConfig):
    url: str = "redis://localhost:6379/0"


class HivemqConfig(ProviderConfig):
    url: str = "mqtt://localhost:1883"
    username: Optional[str] = None
    password: Optional[str] = None


class MemoryConfig(BaseModel):
    heartbeat: float = 0.01


class PubSubConf(BaseModel):
    provider: Literal['redis', 'hivemq', 'memory'] = 'redis'
    url: Optional[str] = None
    heartbeat: float = 0.01
    redis: Optional[RedisConfig] = Field(default_factory=RedisConfig)
    hivemq: Optional[HivemqConfig] = None
    memory: Optional[MemoryConfig] = Field(default_factory=MemoryConfig)
