"""Message bus — async queues connecting channels to the agent."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass
class InboundMessage:
    channel: str
    sender_id: str
    chat_id: str
    content: str
    agent_name: str = "claw"


@dataclass
class OutboundMessage:
    channel: str
    chat_id: str
    content: str


class MessageBus:
    def __init__(self) -> None:
        self._inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()

    async def publish_inbound(self, msg: InboundMessage) -> None:
        await self._inbound.put(msg)

    async def consume_inbound(self) -> InboundMessage:
        return await self._inbound.get()

    async def publish_outbound(self, msg: OutboundMessage) -> None:
        await self._outbound.put(msg)

    async def consume_outbound(self) -> OutboundMessage:
        return await self._outbound.get()
