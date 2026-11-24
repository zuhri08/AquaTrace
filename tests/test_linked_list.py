from app.ds.linked_list import LinkedList


def test_insert_search_delete_and_tail_updates():
    linked = LinkedList()
    linked.insert_head({"id": 2})
    linked.insert_tail({"id": 3})
    linked.insert_head({"id": 1})

    assert linked.length() == 3
    assert linked.traverse() == [{"id": 1}, {"id": 2}, {"id": 3}]
    assert linked.search(2) == {"id": 2}
    assert linked.delete(2) == {"id": 2}
    assert linked.delete(3) == {"id": 3}
    assert linked.tail.value == {"id": 1}
    assert linked.traverse() == [{"id": 1}]
    assert linked.delete(1) == {"id": 1}
    assert linked.head is None
    assert linked.tail is None
    assert linked.delete(404) is None


def test_empty_and_custom_id_getter():
    linked = LinkedList(id_getter=lambda item: item["key"])
    assert linked.is_empty()
    assert linked.search("x") is None
    assert linked.remove_head() is None
    linked.insert_tail({"key": "x", "value": 7})
    assert linked.search("x")["value"] == 7
    assert linked.remove_head()["key"] == "x"
    assert linked.length() == 0
