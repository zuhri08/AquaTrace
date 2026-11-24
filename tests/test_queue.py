from app.ds.queue import PriorityAwareQueue, Queue


def test_queue_fifo_and_empty_state():
    queue = Queue()
    assert queue.dequeue() is None
    assert queue.peek() is None

    queue.enqueue(1)
    queue.enqueue(2)
    assert queue.peek() == 1
    assert queue.display() == [1, 2]
    assert queue.dequeue() == 1
    assert queue.dequeue() == 2
    assert queue.dequeue() is None
    assert queue.is_empty()


def test_enqueue_after_dequeue_to_empty_preserves_head_and_tail():
    queue = Queue()
    queue.enqueue("old")
    assert queue.dequeue() == "old"
    queue.enqueue("new")
    assert queue.peek() == "new"
    assert queue.dequeue() == "new"
    assert queue.size() == 0


def test_priority_queue_preserves_fifo_within_each_lane():
    queue = PriorityAwareQueue()
    queue.enqueue("regular-1")
    queue.enqueue("priority-1", priority=True)
    queue.enqueue("regular-2")
    queue.enqueue("priority-2", priority=True)

    assert queue.size() == 4
    assert queue.display() == {
        "priority": ["priority-1", "priority-2"],
        "regular": ["regular-1", "regular-2"],
    }
    assert [queue.dequeue() for _ in range(4)] == [
        "priority-1",
        "priority-2",
        "regular-1",
        "regular-2",
    ]
