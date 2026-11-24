import math

from sqlalchemy.exc import IntegrityError

from app import db
from app.ds.graph import Graph
from app.models import RiverEdge, WaterSource


def build_source_graph():
    """Build the directed weighted graph from persisted sources and edges."""
    graph = Graph()
    for source_id, in db.session.query(WaterSource.id).order_by(WaterSource.id):
        graph.add_node(source_id)
    for edge in RiverEdge.query.order_by(RiverEdge.id).all():
        graph.add_edge(edge.dari_source_id, edge.ke_source_id, edge.jarak_km)
    return graph


def _route_to(target, previous):
    route = []
    current = target
    while current is not None:
        route.append(current)
        current = previous.get(current)
    route.reverse()
    return route


def trace_downstream(source_id):
    """Return all reachable downstream sources ordered by shortest km distance."""
    source = db.session.get(WaterSource, source_id)
    if source is None:
        raise LookupError("Sumber air tidak ditemukan.")
    graph = build_source_graph()
    distances, previous = graph.dijkstra(source_id)
    reachable = graph.bfs(source_id)
    impacted = []
    for target_id in reachable:
        if target_id == source_id:
            continue
        target = db.session.get(WaterSource, target_id)
        impacted.append(
            {
                "source": target,
                "distance_km": distances[target_id],
                "route": _route_to(target_id, previous),
            }
        )
    impacted.sort(key=lambda item: (item["distance_km"], item["source"].id))
    return impacted


def nearest_clean_source(source_id):
    """Find the reachable lab-clean source with minimum Dijkstra distance."""
    source = db.session.get(WaterSource, source_id)
    if source is None:
        raise LookupError("Sumber air tidak ditemukan.")
    graph = build_source_graph()
    distances, previous = graph.dijkstra(source_id)
    candidates = []
    for candidate_id, distance in distances.items():
        if candidate_id == source_id or not math.isfinite(distance):
            continue
        candidate = db.session.get(WaterSource, candidate_id)
        if candidate is not None and candidate.status_terakhir == "BERSIH":
            candidates.append((distance, candidate.id, candidate))
    if not candidates:
        return None
    distance, _, candidate = min(candidates, key=lambda item: (item[0], item[1]))
    route = _route_to(candidate.id, previous)
    return {
        "source": candidate,
        "distance_km": distance,
        "route": route,
        "route_sources": [db.session.get(WaterSource, item) for item in route],
    }


def add_river_edge(source_id, target_id, distance_km):
    """Validate and persist one directed weighted edge."""
    try:
        distance = float(distance_km)
    except (TypeError, ValueError) as error:
        raise ValueError("Jarak harus berupa angka positif.") from error
    if not math.isfinite(distance) or distance <= 0:
        raise ValueError("Jarak harus berupa angka positif.")
    if source_id == target_id:
        raise ValueError("Edge ke diri sendiri tidak diizinkan.")
    if db.session.get(WaterSource, source_id) is None:
        raise ValueError("Sumber asal tidak ditemukan.")
    if db.session.get(WaterSource, target_id) is None:
        raise ValueError("Sumber tujuan tidak ditemukan.")
    if RiverEdge.query.filter_by(
        dari_source_id=source_id, ke_source_id=target_id
    ).first():
        raise ValueError("Edge dengan arah tersebut sudah ada.")
    edge = RiverEdge(
        dari_source_id=source_id,
        ke_source_id=target_id,
        jarak_km=distance,
    )
    db.session.add(edge)
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise ValueError("Edge tidak valid atau sudah ada.") from error
    return edge


def remove_river_edge(edge_id):
    """Delete an edge by id; return None if it does not exist."""
    edge = db.session.get(RiverEdge, edge_id)
    if edge is None:
        return None
    db.session.delete(edge)
    db.session.commit()
    return edge


def network_snapshot():
    """Return database-backed node and edge rows for simple graph pages."""
    sources = WaterSource.query.order_by(WaterSource.id).all()
    edges = RiverEdge.query.order_by(RiverEdge.id).all()
    return sources, edges
