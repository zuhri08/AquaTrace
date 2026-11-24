from flask import Blueprint, abort, g, jsonify, request

from app import db
from app.config import thresholds
from app.models import (
    EntryAction,
    IotDevice,
    RiverEdge,
    Sample,
    WaterSource,
)
from app.routes.auth import role_required
from app.services.antrean import build_sample_queue
from app.services.diagnosis import build_decision_tree, evaluate_measurements
from app.services.jaringan import (
    build_source_graph,
    nearest_clean_source,
    trace_downstream,
)
from app.services.riwayat import build_source_history
from app.services.telemetri import (
    build_reading_queue,
    device_is_online,
    latest_readings,
    sensor_series,
)
from app.services.undo import build_undo_stack
from app.services.wilayah import region_dashboard_data

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _response(data, operation, time_complexity, space_complexity):
    return jsonify(
        {
            "data": data,
            "last_operation": operation,
            "complexity": {
                "time": time_complexity,
                "space": space_complexity,
            },
        }
    )


def _sample_item(sample, position=None):
    return {
        "id": sample.id,
        "source_id": sample.source_id,
        "source_name": sample.source.nama,
        "priority": bool(sample.prioritas),
        "origin": sample.asal,
        "status": sample.status,
        "created_at": sample.created_at.isoformat(),
        "position": position,
    }


@api_bp.get("/queue")
@role_required("warga", "petugas_lab", "admin")
def queue_visualization():
    queue = build_sample_queue()
    lanes = queue.display()
    if g.user.role == "warga":
        own_ids = {
            sample.id
            for sample in Sample.query.filter_by(
                diajukan_oleh=g.user.id, status="menunggu"
            ).all()
        }
        all_items = lanes["priority"] + lanes["regular"]
        items = [
            _sample_item(sample, position=index)
            for index, sample in enumerate(all_items, start=1)
            if sample.id in own_ids
        ]
        own_priority = [item for item in items if item["priority"]]
        own_regular = [item for item in items if not item["priority"]]
        data = {
            "priority": own_priority,
            "regular": own_regular,
            "front": items[0] if items else None,
            "rear": items[-1] if items else None,
            "size": len(items),
        }
    else:
        priority = [_sample_item(sample) for sample in lanes["priority"]]
        regular = [_sample_item(sample) for sample in lanes["regular"]]
        data = {
            "priority": priority,
            "regular": regular,
            "front": priority[0] if priority else (regular[0] if regular else None),
            "rear": regular[-1] if regular else (priority[-1] if priority else None),
            "size": queue.size(),
        }
    return _response(
        data,
        f"PriorityAwareQueue dari DB -> {data['size']} sampel tampil",
        "O(n)",
        "O(n)",
    )


@api_bp.get("/stack")
@role_required("petugas_lab", "admin")
def stack_visualization():
    stack = build_undo_stack(g.user.id)
    items = [
        {
            "id": action.id,
            "action": action.aksi,
            "payload": action.payload_json,
            "created_at": action.created_at.isoformat(),
        }
        for action in stack.to_list()
    ]
    return _response(
        {"items": items, "top": items[0] if items else None, "size": len(items)},
        f"UndoStack per user -> {len(items)} aksi",
        "O(n)",
        "O(n)",
    )


@api_bp.get("/linked-list/<int:source_id>")
@role_required("warga", "petugas_lab", "admin")
def linked_list_visualization(source_id):
    source = db.session.get(WaterSource, source_id)
    if source is None:
        abort(404)
    history = build_source_history(source_id)
    entries = history.traverse()
    search_id = request.args.get("search")
    found = None
    operation = f"traverse() -> {len(entries)} hasil"
    complexity = "O(n)"
    if search_id is not None:
        try:
            target_id = int(search_id)
        except ValueError:
            return jsonify({"error": "Parameter search harus integer."}), 422
        result = history.search(target_id)
        found = result.id if result else None
        operation = f"search({target_id}) -> {'ditemukan' if result else 'tidak ditemukan'}"
        complexity = "O(n)"
    data = {
        "source": {"id": source.id, "name": source.nama},
        "head": entries[0].id if entries else None,
        "tail": entries[-1].id if entries else None,
        "length": history.length(),
        "searched_id": found,
        "entries": [
            {
                "id": result.id,
                "ph": result.ph,
                "kekeruhan_ntu": result.kekeruhan_ntu,
                "tds_mgl": result.tds_mgl,
                "status": result.vonis,
                "created_at": result.created_at.isoformat(),
                "jejak": result.jejak_keputusan,
            }
            for result in entries
        ],
    }
    return _response(data, operation, complexity, "O(n)")


def _decision_node(node):
    if node.verdict is not None:
        return {
            "type": "verdict",
            "verdict": node.verdict,
            "message": node.message or node.verdict,
        }
    return {
        "type": "condition",
        "feature": node.feature,
        "operator": node.operator,
        "threshold": node.threshold,
        "true": _decision_node(node.when_true),
        "false": _decision_node(node.when_false),
    }


@api_bp.get("/tree/decision")
@role_required("petugas_lab", "admin")
def decision_tree_visualization():
    decision_tree = build_decision_tree()
    data = {
        "root": _decision_node(decision_tree.root),
        "thresholds": {
            "ph_min": thresholds.PH_MIN,
            "ph_max": thresholds.PH_MAX,
            "kekeruhan_max_ntu": thresholds.KEKERUHAN_MAX_NTU,
            "tds_max_mgl": thresholds.TDS_MAX_MGL,
            "is_example": thresholds.IS_EXAMPLE,
            "regulation_source": thresholds.REGULATION_SOURCE,
        },
        "evaluation": None,
    }
    fields = ("ph", "kekeruhan_ntu", "tds_mgl")
    present = [field in request.args for field in fields]
    operation = "build_decision_tree() dari thresholds.py"
    if any(present) and not all(present):
        return jsonify({"error": "Kirim ph, kekeruhan_ntu, dan tds_mgl bersama-sama."}), 422
    if all(present):
        try:
            measurements = {field: float(request.args[field]) for field in fields}
            verdict, trace = evaluate_measurements(measurements)
        except (ValueError, KeyError) as error:
            return jsonify({"error": str(error)}), 422
        data["evaluation"] = {"verdict": verdict, "trace": trace}
        operation = f"evaluate(data) -> {verdict}"
    return _response(data, operation, "O(h)", "O(h)")


@api_bp.get("/tree/regions")
@role_required("admin")
def region_tree_visualization():
    tree, contaminated = region_dashboard_data()
    return _response(
        {"root": tree, "contaminated_sources": contaminated},
        f"hitung_tercemar(root) -> {contaminated} sumber",
        "O(V)",
        "O(V)",
    )


def _graph_data(highlight_nodes=None, highlight_edges=None, result=None):
    sources = WaterSource.query.order_by(WaterSource.id).all()
    edges = RiverEdge.query.order_by(RiverEdge.id).all()
    return {
        "nodes": [
            {
                "id": source.id,
                "name": source.nama,
                "status": source.status_terakhir,
                "sensor_status": source.status_sensor,
                "lat": source.lat,
                "lng": source.lng,
            }
            for source in sources
        ],
        "edges": [
            {
                "id": edge.id,
                "from": edge.dari_source_id,
                "to": edge.ke_source_id,
                "distance_km": edge.jarak_km,
            }
            for edge in edges
        ],
        "highlight_nodes": highlight_nodes or [],
        "highlight_edges": highlight_edges or [],
        "result": result,
    }


def _route_edges(route):
    return [
        {"from": route[index], "to": route[index + 1]}
        for index in range(len(route) - 1)
    ]


@api_bp.get("/graph")
@role_required("warga", "petugas_lab", "admin")
def graph_visualization():
    graph = build_source_graph()
    data = _graph_data()
    return _response(
        data,
        f"build_source_graph() -> {len(graph.nodes())} node, {sum(len(graph.neighbors(node)) for node in graph.nodes())} edge",
        "O(V+E)",
        "O(V+E)",
    )


@api_bp.get("/graph/trace/<int:source_id>")
@role_required("petugas_lab", "admin")
def graph_trace_visualization(source_id):
    try:
        impacted = trace_downstream(source_id)
    except LookupError:
        abort(404)
    routes = [item["route"] for item in impacted]
    highlighted_nodes = sorted(
        {node for route in routes for node in route}
    )
    highlighted_edges = []
    seen_edges = set()
    for route in routes:
        for edge in _route_edges(route):
            key = (edge["from"], edge["to"])
            if key not in seen_edges:
                seen_edges.add(key)
                highlighted_edges.append(edge)
    data = _graph_data(
        highlighted_nodes,
        highlighted_edges,
        {
            "impacted": [
                {
                    "id": item["source"].id,
                    "name": item["source"].nama,
                    "distance_km": item["distance_km"],
                    "route": item["route"],
                    "status": item["source"].status_terakhir,
                }
                for item in impacted
            ]
        },
    )
    return _response(
        data,
        f"bfs()+dijkstra({source_id}) -> {len(impacted)} sumber hilir",
        "O((V+E) log V)",
        "O(V+E)",
    )


@api_bp.get("/graph/nearest/<int:source_id>")
@role_required("warga", "petugas_lab", "admin")
def graph_nearest_visualization(source_id):
    try:
        nearest = nearest_clean_source(source_id)
    except LookupError:
        abort(404)
    route = nearest["route"] if nearest else []
    result = (
        {
            "id": nearest["source"].id,
            "name": nearest["source"].nama,
            "distance_km": nearest["distance_km"],
            "route": route,
        }
        if nearest
        else None
    )
    data = _graph_data(route, _route_edges(route), result)
    return _response(
        data,
        f"dijkstra({source_id}) -> {nearest['source'].nama if nearest else 'tidak ada jalur'}",
        "O((V+E) log V)",
        "O(V+E)",
    )


@api_bp.get("/telemetry/latest")
@role_required("warga", "petugas_lab", "admin")
def telemetry_latest_visualization():
    readings = latest_readings()
    items = []
    for reading in readings:
        triggered_sample = (
            Sample.query.filter(
                Sample.source_id == reading.source_id,
                Sample.asal == "iot",
                Sample.prioritas.is_(True),
                Sample.created_at >= reading.diterima_at,
            )
            .order_by(Sample.created_at.asc(), Sample.id.asc())
            .first()
        )
        items.append(
            {
                "id": reading.id,
                "device_code": reading.device.kode,
                "source_name": reading.source.nama,
                "ph": reading.ph,
                "kekeruhan_ntu": reading.kekeruhan_ntu,
                "tds_mgl": reading.tds_mgl,
                "status": reading.vonis,
                "received_at": reading.diterima_at.isoformat(),
                "priority_sample": triggered_sample is not None,
                "priority_sample_id": (
                    triggered_sample.id if triggered_sample is not None else None
                ),
            }
        )
    return _response(
        {"items": items},
        f"latest_readings() -> {len(readings)} bacaan",
        "O(n log n)",
        "O(n)",
    )


@api_bp.get("/telemetry/queue")
@role_required("warga", "petugas_lab", "admin")
def telemetry_queue_visualization():
    queue = build_reading_queue()
    items = [
        {
            "id": reading.id,
            "device_code": reading.device.kode,
            "source_name": reading.source.nama,
            "received_at": reading.diterima_at.isoformat(),
        }
        for reading in queue.to_list()
    ]
    return _response(
        {"items": items, "size": queue.size()},
        f"ReadingQueue -> {queue.size()} bacaan antri",
        "O(n)",
        "O(n)",
    )


@api_bp.get("/public/graph")
def public_graph_visualization():
    data = _graph_data()
    return _response(
        data,
        f"public graph -> {len(data['nodes'])} sumber, {len(data['edges'])} edge",
        "O(V+E)",
        "O(V+E)",
    )


@api_bp.get("/public/telemetry/latest")
def public_telemetry_visualization():
    readings = latest_readings(20)
    return _response(
        {
            "items": [
                {
                    "id": reading.id,
                    "device_code": reading.device.kode,
                    "source_name": reading.source.nama,
                    "ph": reading.ph,
                    "kekeruhan_ntu": reading.kekeruhan_ntu,
                    "tds_mgl": reading.tds_mgl,
                    "status": reading.vonis,
                    "received_at": reading.diterima_at.isoformat(),
                }
                for reading in readings
            ]
        },
        f"latest public readings -> {len(readings)} bacaan",
        "O(n log n)",
        "O(n)",
    )


@api_bp.get("/public/telemetry/series/<int:device_id>")
def public_sensor_series(device_id):
    device = db.session.get(IotDevice, device_id)
    if device is None:
        abort(404)
    return _response(
        {
            "device_id": device.id,
            "device_code": device.kode,
            "online": device_is_online(device),
            "items": [
                {
                    "id": reading.id,
                    "ph": reading.ph,
                    "kekeruhan_ntu": reading.kekeruhan_ntu,
                    "tds_mgl": reading.tds_mgl,
                    "status": reading.vonis,
                    "received_at": reading.diterima_at.isoformat(),
                }
                for reading in sensor_series(device_id).traverse()
            ],
        },
        "LinkedList.insert_tail() -> jendela sensor",
        "O(n)",
        "O(n)",
    )
