import pytest
import asyncio
from uuid import uuid4
from codecouncil.events.bus import EventBus
from codecouncil.events.websocket import WebSocketPublisher
from codecouncil.events.sse import SSEPublisher
from codecouncil.models.events import Event, EventType, Phase


@pytest.mark.asyncio
async def test_event_bus_subscribe_and_emit():
    bus = EventBus()
    run_id = uuid4()
    received = []

    async def collector():
        async for event in bus.subscribe(run_id):
            received.append(event)
            if len(received) >= 2:
                break

    event1 = Event(run_id=run_id, agent="system", event_type=EventType.RUN_STARTED, phase=Phase.INGESTING, content="Run started")
    event2 = Event(run_id=run_id, agent="archaeologist", event_type=EventType.AGENT_ACTIVATED, phase=Phase.ANALYSING, content="Activated")

    task = asyncio.create_task(collector())
    await asyncio.sleep(0.01)
    await bus.emit(event1)
    await bus.emit(event2)
    await task

    assert len(received) == 2
    assert received[0].event_type == EventType.RUN_STARTED
    assert received[1].agent == "archaeologist"


@pytest.mark.asyncio
async def test_event_sequence_auto_increments():
    bus = EventBus()
    run_id = uuid4()

    e1 = Event(run_id=run_id, agent="system", event_type=EventType.RUN_STARTED, phase=Phase.INGESTING, content="Start")
    e2 = Event(run_id=run_id, agent="system", event_type=EventType.PHASE_STARTED, phase=Phase.ANALYSING, content="Analyse")

    await bus.emit(e1)
    await bus.emit(e2)

    assert e1.sequence == 1
    assert e2.sequence == 2


@pytest.mark.asyncio
async def test_event_bus_multiple_subscribers():
    bus = EventBus()
    run_id = uuid4()
    received_a, received_b = [], []

    async def sub_a():
        async for event in bus.subscribe(run_id):
            received_a.append(event)
            if len(received_a) >= 1:
                break

    async def sub_b():
        async for event in bus.subscribe(run_id):
            received_b.append(event)
            if len(received_b) >= 1:
                break

    task_a = asyncio.create_task(sub_a())
    task_b = asyncio.create_task(sub_b())
    await asyncio.sleep(0.01)

    event = Event(run_id=run_id, agent="system", event_type=EventType.RUN_STARTED, phase=Phase.INGESTING, content="Start")
    await bus.emit(event)

    await task_a
    await task_b
    assert len(received_a) == 1
    assert len(received_b) == 1


@pytest.mark.asyncio
async def test_event_replay():
    bus = EventBus()
    run_id = uuid4()

    for i in range(5):
        e = Event(run_id=run_id, agent="system", event_type=EventType.PHASE_STARTED, phase=Phase.INGESTING, content=f"Event {i}")
        await bus.emit(e)

    # Replay all
    all_events = await bus.replay(run_id)
    assert len(all_events) == 5

    # Replay after sequence 3
    partial = await bus.replay(run_id, after_sequence=3)
    assert len(partial) == 2
    assert partial[0].sequence == 4


@pytest.mark.asyncio
async def test_event_bus_handler():
    bus = EventBus()
    run_id = uuid4()
    handled = []

    async def handler(event: Event):
        handled.append(event)

    bus.add_handler(handler)

    event = Event(run_id=run_id, agent="system", event_type=EventType.RUN_STARTED, phase=Phase.INGESTING, content="Start")
    await bus.emit(event)

    assert len(handled) == 1
    assert handled[0].content == "Start"


@pytest.mark.asyncio
async def test_event_bus_clear_run():
    bus = EventBus()
    run_id = uuid4()

    event = Event(run_id=run_id, agent="system", event_type=EventType.RUN_STARTED, phase=Phase.INGESTING, content="Start")
    await bus.emit(event)

    assert bus.get_sequence(run_id) == 1
    bus.clear_run(run_id)
    assert bus.get_sequence(run_id) == 0


def test_websocket_publisher_connection_count():
    pub = WebSocketPublisher()
    assert pub.get_connection_count() == 0


def test_sse_publisher_add_remove():
    pub = SSEPublisher()
    run_id = uuid4()
    queue = pub.add_subscriber(run_id)
    assert queue is not None
    pub.remove_subscriber(run_id, queue)
