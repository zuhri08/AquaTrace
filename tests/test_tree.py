import pytest

from app.ds.tree import DecisionNode, DecisionTree, Tree, hitung_tercemar


def test_general_tree_traversals_height_and_parent_lookup():
    tree = Tree("Provinsi")
    tree.add_node("Provinsi", "Kota A")
    tree.add_node("Provinsi", "Kota B")
    tree.add_node("Kota A", "Desa A1")

    assert tree.pre_order() == ["Provinsi", "Kota A", "Desa A1", "Kota B"]
    assert tree.level_order() == ["Provinsi", "Kota A", "Kota B", "Desa A1"]
    assert tree.height() == 3
    assert tree.find("Desa A1").value == "Desa A1"
    assert tree.find("Tidak ada") is None
    with pytest.raises(ValueError):
        tree.add_node("Tidak ada", "Anak")


def test_recursive_contamination_count():
    tree = Tree({"nama": "root", "tercemar": False})
    tree.add_node(tree.root.value, {"nama": "child-1", "tercemar": True})
    tree.add_node(tree.root.value, {"nama": "child-2", "tercemar": False})
    tree.add_node({"nama": "child-1", "tercemar": True}, {"nama": "leaf", "tercemar": True})

    contaminated = lambda region: region["tercemar"]
    assert tree.hitung_tercemar(contaminated) == 2
    assert hitung_tercemar(tree.root, contaminated) == 2


def test_decision_tree_evaluates_recursively_with_readable_trace():
    clean = DecisionNode(verdict="BERSIH", message="Hasil screening: BERSIH")
    warning = DecisionNode(verdict="WASPADA", message="Hasil screening: WASPADA")
    root = DecisionNode(
        feature="ph",
        operator="<",
        threshold=6.5,
        when_true=warning,
        when_false=DecisionNode(
            feature="turbidity",
            operator=">",
            threshold=5,
            when_true=warning,
            when_false=clean,
        ),
    )
    tree = DecisionTree(root)

    verdict, trace = tree.evaluate({"ph": 7.0, "turbidity": 8})
    assert verdict == "WASPADA"
    assert trace == [
        "ph 7.0 < 6.5 (tidak terpenuhi)",
        "turbidity 8 > 5 (terpenuhi)",
        "Hasil screening: WASPADA",
    ]
    assert tree.evaluate({"ph": 6.0, "turbidity": 1})[0] == "WASPADA"
    with pytest.raises(KeyError):
        tree.evaluate({"ph": 7.0})


def test_decision_condition_requires_two_branches():
    with pytest.raises(ValueError):
        DecisionNode(feature="ph", operator="<", threshold=6.5)
