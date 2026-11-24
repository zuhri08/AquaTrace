import pytest

from app.ds.stack import Stack


def test_stack_operations_are_lifo_and_to_list_starts_at_top():
    stack = Stack()
    stack.push("first")
    stack.push("second")

    assert stack.size() == 2
    assert stack.peek() == "second"
    assert stack.to_list() == ["second", "first"]
    assert stack.pop() == "second"
    assert stack.pop() == "first"
    assert stack.is_empty()
    assert stack.size() == 0


def test_empty_stack_access_raises_index_error():
    stack = Stack()
    with pytest.raises(IndexError):
        stack.pop()
    with pytest.raises(IndexError):
        stack.peek()
