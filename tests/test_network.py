import math
import re

import pytest

from app import create_app, db
from app.models import RiverEdge, User, WaterSource
from app.services.jaringan import (
    add_river_edge,
    build_source_graph,
    nearest_clean_source,
    remove_river_edge,
    trace_downstream,
)
from seed import seed_database


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "network-test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'network.db'}",
        }
    )
    with application.app_context():
        db.create_all()
        seed_database()
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


def _login(client, email):
    response = client.get("/login")
    token = re.search(
        r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)
    ).group(1)
    return client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": email,
            "password": "AquaTraceDemo123!",
        },
    )


def test_downstream_trace_uses_shortest_distance_and_sorted_results(app):
    with app.app_context():
        sources = WaterSource.query.order_by(WaterSource.id).all()
        sources[1].status_terakhir = "TIDAK_LAYAK"
        sources[2].status_terakhir = "BERSIH"
        sources[3].status_terakhir = "WASPADA"
        db.session.commit()

        impacted = trace_downstream(sources[0].id)
        assert [item["source"].id for item in impacted[:3]] == [
            sources[1].id,
            sources[2].id,
            sources[3].id,
        ]
        assert [item["distance_km"] for item in impacted[:3]] == [0.5, 1.25, 2.25]
        assert impacted[1]["route"] == [sources[0].id, sources[1].id, sources[2].id]

        branch = add_river_edge(sources[0].id, sources[3].id, 0.25)
        impacted = trace_downstream(sources[0].id)
        closest = next(item for item in impacted if item["source"].id == sources[3].id)
        assert closest["distance_km"] == 0.25
        assert closest["route"] == [sources[0].id, sources[3].id]
        assert remove_river_edge(branch.id) is not None


def test_nearest_clean_source_and_no_reachable_path(app):
    with app.app_context():
        sources = WaterSource.query.order_by(WaterSource.id).all()
        for source in sources:
            source.status_terakhir = "WASPADA"
        sources[1].status_terakhir = "TIDAK_LAYAK"
        sources[2].status_terakhir = "BERSIH"
        db.session.commit()

        nearest = nearest_clean_source(sources[0].id)
        assert nearest["source"].id == sources[2].id
        assert nearest["distance_km"] == 1.25
        assert [source.id for source in nearest["route_sources"]] == [
            sources[0].id,
            sources[1].id,
            sources[2].id,
        ]
        assert nearest_clean_source(sources[14].id) is None


def test_edge_validation_duplicate_and_removal(app):
    with app.app_context():
        sources = WaterSource.query.order_by(WaterSource.id).all()
        graph = build_source_graph()
        assert graph.neighbors(sources[0].id)
        edge = add_river_edge(sources[14].id, sources[0].id, 0.2)
        assert RiverEdge.query.filter_by(
            dari_source_id=sources[14].id, ke_source_id=sources[0].id
        ).count() == 1
        with pytest.raises(ValueError, match="sudah ada"):
            add_river_edge(sources[14].id, sources[0].id, 0.3)
        with pytest.raises(ValueError, match="diri sendiri"):
            add_river_edge(sources[0].id, sources[0].id, 1)
        for invalid in ("0", "-1", "nan", "inf", "not-a-number"):
            with pytest.raises(ValueError):
                add_river_edge(sources[14].id, sources[1].id, invalid)
        assert remove_river_edge(edge.id).id == edge.id
        assert remove_river_edge(edge.id) is None


def test_real_osm_network_traces_downstream_and_uses_verified_distances(app):
    with app.app_context():
        mlirip = WaterSource.query.filter_by(
            nama="Kali Surabaya · simpul OSM di sisi Mlirip"
        ).one()
        jagir = WaterSource.query.filter_by(
            nama="Kali Jagir · simpang OSM dengan Kali Surabaya"
        ).one()
        ngagel = WaterSource.query.filter_by(
            nama="Kali Jagir · simpul OSM di Ngagel"
        ).one()
        mas_end = WaterSource.query.filter_by(
            nama="Kali Mas · simpul OSM 320089529"
        ).one()

        edge = RiverEdge.query.filter_by(
            dari_source_id=mlirip.id, ke_source_id=jagir.id
        ).one()
        assert edge.sumber_jarak == "geometri_osm"
        assert edge.terverifikasi is True
        assert edge.jarak_km == pytest.approx(42.255, abs=0.001)

        impacted = trace_downstream(mlirip.id)
        jagir_result = next(item for item in impacted if item["source"].id == jagir.id)
        assert jagir_result["route"] == [mlirip.id, jagir.id]
        assert jagir_result["distance_km"] == edge.jarak_km

        graph = build_source_graph()
        distances, previous = graph.dijkstra(mlirip.id)
        assert distances[ngagel.id] == pytest.approx(
            edge.jarak_km
            + RiverEdge.query.filter_by(
                dari_source_id=jagir.id, ke_source_id=ngagel.id
            ).one().jarak_km
        )
        assert previous[ngagel.id] == jagir.id
        assert distances[mas_end.id] == pytest.approx(
            edge.jarak_km
            + RiverEdge.query.filter_by(
                dari_source_id=jagir.id, ke_source_id=mas_end.id
            ).one().jarak_km
        )
        assert previous[mas_end.id] == jagir.id
        assert trace_downstream(mas_end.id) == []
        reverse_distances, _ = graph.dijkstra(mas_end.id)
        assert math.isinf(reverse_distances[mlirip.id])


def test_network_routes_enforce_admin_role_and_render_simple_pages(app):
    client = app.test_client()
    assert _login(client, "warga@aquatrace.test").status_code == 302
    assert client.get("/admin/jaringan").status_code == 403
    assert client.get("/petugas/lacak-dampak").status_code == 403
    assert client.get("/warga/terdekat").status_code == 200

    client.post("/logout", data={"csrf_token": _csrf(client)})
    assert _login(client, "admin@aquatrace.test").status_code == 302
    assert client.get("/admin/jaringan").status_code == 200
    network_page = client.get("/admin/jaringan").get_data(as_text=True)
    assert "© OpenStreetMap contributors" in network_page
    assert "Data nyata (sumber: GEOMETRI OSM)" in network_page
    assert client.get("/petugas/lacak-dampak").status_code == 200


def _csrf(client):
    response = client.get("/")
    return re.search(
        r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)
    ).group(1)
