from app.ds.tree import Tree, TreeNode, hitung_tercemar
from app.models import Region, TestResult, WaterSource


def build_region_tree():
    """Build a hierarchy tree with recursive contaminated-source totals."""
    regions = Region.query.order_by(Region.id).all()
    sources = WaterSource.query.order_by(WaterSource.id).all()
    latest_results = {}
    for result in TestResult.query.order_by(
        TestResult.created_at.desc(), TestResult.id.desc()
    ).all():
        latest_results.setdefault(result.source_id, result)
    root = TreeNode(
        {
            "type": "root",
            "id": None,
            "nama": "Wilayah",
            "level": "root",
            "tercemar": False,
            "jumlah_tercemar": 0,
        }
    )
    tree = Tree(root)
    nodes = {}
    for region in regions:
        nodes[region.id] = TreeNode(
            {
                "type": "region",
                "id": region.id,
                "nama": region.nama,
                "level": region.level,
                "tercemar": False,
                "jumlah_tercemar": 0,
            }
        )
    for region in regions:
        parent = nodes.get(region.parent_id, root)
        parent.children.append(nodes[region.id])

    for source in sources:
        region_node = nodes.get(source.region_id, tree.root)
        latest_result = latest_results.get(source.id)
        if latest_result is not None:
            status = latest_result.vonis or "belum_diklasifikasikan"
        elif source.is_simulated:
            status = source.status_terakhir
        else:
            status = "belum_ada"
        region_node.children.append(
            TreeNode(
                {
                    "type": "source",
                    "id": source.id,
                    "nama": source.nama,
                    "level": "sumber",
                    "tercemar": status == "TIDAK_LAYAK",
                    "status": status,
                    "sumber_data": source.sumber_data,
                    "is_simulated": source.is_simulated,
                    "region_known": source.region_id in nodes,
                    "jumlah_tercemar": 0,
                }
            )
        )

    def annotate(node):
        """Set a subtree total post-order with one recursive tree walk."""
        count = int(node.value["tercemar"])
        for child in node.children:
            count += annotate(child)
        if node.value["type"] in {"root", "region"}:
            node.value["jumlah_tercemar"] = count
        return count

    total = annotate(tree.root)
    # Keep the Tree API's recursive count as an independent structural result.
    recursive_total = hitung_tercemar(
        tree.root, lambda value: value["type"] == "source" and value["tercemar"]
    )
    if recursive_total != total:
        raise RuntimeError("Perhitungan rekursif sumber tercemar tidak konsisten.")
    return tree, total


def region_dashboard_data():
    """Return nested serializable data and total count for dashboard display."""
    tree, total = build_region_tree()

    def serialize(node):
        return {
            **node.value,
            "children": [serialize(child) for child in node.children],
        }

    return serialize(tree.root), total
