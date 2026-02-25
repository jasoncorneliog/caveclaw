"""Tests for the async message bus."""

from caveclaw.bus import Attachment, InboundMessage, MessageBus, OutboundMessage


def test_attachment_fields():
    att = Attachment(path="/tmp/f.png", filename="f.png", content_type="image/png", size=1024)
    assert att.path == "/tmp/f.png"
    assert att.filename == "f.png"
    assert att.content_type == "image/png"
    assert att.size == 1024


def test_inbound_message_defaults():
    msg = InboundMessage(channel="cli", sender_id="u", chat_id="s", content="hi")
    assert msg.agent_name == "claw"
    assert msg.attachments == []


def test_inbound_message_custom_agent():
    msg = InboundMessage(channel="cli", sender_id="u", chat_id="s", content="hi", agent_name="shadow")
    assert msg.agent_name == "shadow"


def test_inbound_message_with_attachments(sample_attachment):
    msg = InboundMessage(
        channel="cli", sender_id="u", chat_id="s",
        content="look at this", attachments=[sample_attachment],
    )
    assert len(msg.attachments) == 1
    assert msg.attachments[0].filename == "photo.png"


async def test_bus_inbound_round_trip(bus):
    msg = InboundMessage(channel="test", sender_id="u", chat_id="s", content="hello")
    await bus.publish_inbound(msg)
    got = await bus.consume_inbound()
    assert got is msg


async def test_bus_outbound_round_trip(bus):
    msg = OutboundMessage(channel="test", chat_id="s", content="reply")
    await bus.publish_outbound(msg)
    got = await bus.consume_outbound()
    assert got is msg


async def test_bus_fifo_order(bus):
    msgs = [InboundMessage(channel="test", sender_id="u", chat_id="s", content=str(i)) for i in range(3)]
    for m in msgs:
        await bus.publish_inbound(m)
    for m in msgs:
        assert await bus.consume_inbound() is m
