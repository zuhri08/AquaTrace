#!/usr/bin/env python3
"""Refresh cited OSM/BPS snapshots and import publication measurements."""

import argparse
import csv
import json
import math
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "nyata"
USER_AGENT = "AquaTrace/1.0 (public data import)"
OSM_API = "https://api.openstreetmap.org/api/0.6"
BPS_API = "https://sig.bps.go.id/api/v1/kode-relasi"
BPS_PERIOD = "2024_1"
PUM_PERIOD = "2025"
PROVINCE_CODE = "35"
CORRIDOR_REGENCIES = {
    "KAB. GRESIK",
    "KAB. SIDOARJO",
    "KAB. MOJOKERTO",
    "KOTA SURABAYA",
}
KNOWN_WATERWAY_CHAINS = {
    "Kali Surabaya": [934029648, 929541321, 933986461, 696497293, 933968972, 29100243],
    "Kali Jagir": [464034862, 464034861, 309956659],
    "Kali Mas": [309956660, 475190704, 447632039],
}
KNOWN_WAYS = {
    way_id: river_name
    for river_name, way_ids in KNOWN_WATERWAY_CHAINS.items()
    for way_id in way_ids
}
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
OVERPASS_QUERY = r"""
[out:json][timeout:90];
area["name"="Jawa Timur"]["admin_level"="4"]->.jatim;
(
  way(area.jatim)["waterway"~"river|stream"]["name"~"Kali Surabaya|Kali Wonokromo|Kalimas|Kali Tengah|Kali Marmoyo|Kali Jagir|Kali Mas",i];
  relation(area.jatim)["waterway"]["name"~"Kali Surabaya|Kali Wonokromo|Kalimas|Kali Tengah|Kali Marmoyo|Kali Jagir|Kali Mas",i];
  node(area.jatim)["name"~"^(Bendung Mlirip|Hulu Kali Tengah|Muara Kali Tengah|Canggu|Perning|Jrebeng|Cangkir|Bambe|Karangpilang|Sepanjang|Gunungsari|Bendung Jagir|Ngagel)$",i];
  way(area.jatim)["name"~"^(Bendung Mlirip|Hulu Kali Tengah|Muara Kali Tengah|Canggu|Perning|Jrebeng|Cangkir|Bambe|Karangpilang|Sepanjang|Gunungsari|Bendung Jagir|Ngagel)$",i];
);
out body geom;
"""
POINTS_NEEDING_VERIFICATION = (
    "Bendung Mlirip",
    "Hulu Kali Tengah",
    "Muara Kali Tengah",
    "Canggu",
    "Perning",
    "Jrebeng",
    "Cangkir",
    "Bambe",
    "Karangpilang (intake PDAM)",
    "Sepanjang",
    "Gunungsari",
    "Bendung Jagir",
    "Ngagel (intake PDAM)",
    "Kali Wonokromo",
    "Kalimas",
    "Kali Tengah",
    "Kali Marmoyo",
)


def _now_utc():
    return datetime.now(timezone.utc).isoformat()


def _request_json(url, *, data=None, timeout=45):
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    request = Request(url, data=data, headers=headers)
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def fetch_overpass():
    request_body = urlencode({"data": OVERPASS_QUERY}).encode("utf-8")
    failures = []
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = _request_json(endpoint, data=request_body, timeout=120)
            if not isinstance(response.get("elements"), list):
                raise ValueError(f"Respons Overpass tidak berisi elements: {endpoint}")
            return {
                "source": "OpenStreetMap Overpass API",
                "endpoint": endpoint,
                "retrieved_at": _now_utc(),
                "query": OVERPASS_QUERY.strip(),
                "attribution": "© OpenStreetMap contributors",
                "license": "Open Database License (ODbL) 1.0",
                "elements": response["elements"],
            }
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            failures.append(f"{endpoint}: {error}")
    raise RuntimeError("Semua endpoint Overpass gagal: " + " | ".join(failures))


def _clean_way_response(response):
    elements = response.get("elements", [])
    ways = [element for element in elements if element.get("type") == "way"]
    if len(ways) != 1:
        raise ValueError("Respons OSM tidak berisi tepat satu way.")
    way = ways[0]
    expected_name = KNOWN_WAYS[way["id"]]
    if way.get("tags", {}).get("name") != expected_name:
        raise ValueError(
            f"Way {way['id']} tidak lagi bernama {expected_name!r}; "
            "jangan gunakan snapshot lama."
        )
    if way.get("tags", {}).get("waterway") not in {"river", "stream"}:
        raise ValueError(f"Way {way['id']} tidak ditandai sebagai waterway.")
    nodes = {
        element["id"]: {
            "type": "node",
            "id": element["id"],
            "lat": element["lat"],
            "lon": element["lon"],
        }
        for element in elements
        if element.get("type") == "node"
    }
    if any(node_id not in nodes for node_id in way.get("nodes", [])):
        raise ValueError(f"Way {way['id']} kehilangan koordinat salah satu node.")
    return {
        "type": "way",
        "id": way["id"],
        "tags": {
            key: value
            for key, value in way.get("tags", {}).items()
            if key in {"name", "waterway"}
        },
        "nodes": way["nodes"],
    }, nodes


def _haversine_km(first, second):
    radius_km = 6371.0088
    lat1 = math.radians(first["lat"])
    lat2 = math.radians(second["lat"])
    delta_lat = lat2 - lat1
    delta_lon = math.radians(second["lon"] - first["lon"])
    term = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(term))


def _chain_geometry(way_ids, ways, nodes):
    ordered_node_ids = []
    distance_km = 0.0
    for way_id in way_ids:
        way = ways[way_id]
        way_nodes = way["nodes"]
        if ordered_node_ids and ordered_node_ids[-1] != way_nodes[0]:
            raise ValueError(
                f"Geometri tidak tersambung: node {ordered_node_ids[-1]} "
                f"tidak cocok dengan awal way {way_id} ({way_nodes[0]})."
            )
        for index in range(len(way_nodes) - 1):
            distance_km += _haversine_km(
                nodes[way_nodes[index]], nodes[way_nodes[index + 1]]
            )
        if not ordered_node_ids:
            ordered_node_ids.extend(way_nodes)
        else:
            ordered_node_ids.extend(way_nodes[1:])
    return ordered_node_ids, distance_km


def _unverified_points():
    overpass_path = DATA_DIR / "osm_overpass.json"
    elements = []
    if overpass_path.exists():
        with overpass_path.open(encoding="utf-8") as file:
            elements = json.load(file).get("elements", [])
    aliases = {
        "Karangpilang (intake PDAM)": {"Karangpilang"},
        "Ngagel (intake PDAM)": {"Ngagel"},
    }
    points = []
    for name in POINTS_NEEDING_VERIFICATION:
        possible_names = aliases.get(name, {name})
        candidates = [
            {
                "type": element["type"],
                "id": element["id"],
                "name": element.get("tags", {}).get("name"),
                "reference": (
                    f"https://www.openstreetmap.org/{element['type']}/{element['id']}"
                ),
            }
            for element in elements
            if element.get("type") in {"node", "way"}
            and element.get("tags", {}).get("name") in possible_names
        ]
        points.append(
            {
                "name": name,
                "lat": None,
                "lng": None,
                "distance_km": None,
                "upstream_order": None,
                "osm_candidates": candidates,
                "todo": (
                    "Objek bernama ditemukan di OSM, tetapi belum membuktikan "
                    "lokasi titik pantau, intake, bendung, atau posisi pada alur sungai."
                    if candidates
                    else (
                        "Tidak ditemukan objek OSM bernama persis; koordinat, "
                        "urutan, dan jarak belum terverifikasi."
                    )
                ),
            }
        )
    return points


def refresh_osm_ways():
    ways = {}
    nodes = {}
    for index, way_id in enumerate(KNOWN_WAYS):
        response = _request_json(
            f"{OSM_API}/way/{way_id}/full.json",
            timeout=45,
        )
        way, way_nodes = _clean_way_response(response)
        ways[way_id] = way
        for node_id, node in way_nodes.items():
            previous = nodes.get(node_id)
            if previous is not None and (
                previous["lat"] != node["lat"] or previous["lon"] != node["lon"]
            ):
                raise ValueError(f"Koordinat node OSM {node_id} tidak konsisten.")
            nodes[node_id] = node
        if index + 1 < len(KNOWN_WAYS):
            time.sleep(1)

    main_chain = KNOWN_WATERWAY_CHAINS["Kali Surabaya"]
    jagir_chain = KNOWN_WATERWAY_CHAINS["Kali Jagir"]
    mas_chain = KNOWN_WATERWAY_CHAINS["Kali Mas"]
    main_nodes, main_distance = _chain_geometry(main_chain, ways, nodes)
    jagir_nodes, jagir_distance = _chain_geometry(jagir_chain[:2], ways, nodes)
    mas_nodes, mas_distance = _chain_geometry(mas_chain, ways, nodes)
    if main_nodes[0] != 6537680329 or main_nodes[-1] != 312077143:
        raise ValueError("Titik ujung Kali Surabaya berubah; tinjau ulang rute.")
    if jagir_nodes[0] != 312077143 or jagir_nodes[-1] != 4592052456:
        raise ValueError("Sambungan Kali Jagir berubah; tinjau ulang rute.")
    if mas_nodes[0] != 312077143:
        raise ValueError("Sambungan Kali Mas berubah; tinjau ulang rute.")

    osm_node_urls = {
        node_id: f"https://www.openstreetmap.org/node/{node_id}"
        for node_id in (6537680329, 312077143, 4592052456, mas_nodes[-1])
    }
    way_urls = {
        way_id: f"https://www.openstreetmap.org/way/{way_id}" for way_id in ways
    }
    references = lambda way_ids: [way_urls[way_id] for way_id in way_ids]
    overpass_path = DATA_DIR / "osm_overpass.json"
    overpass_summary = None
    unconnected_waterways = []
    if overpass_path.exists():
        with overpass_path.open(encoding="utf-8") as file:
            overpass = json.load(file)
        known_node_ids = set(nodes)
        overpass_summary = {
            "source": overpass["source"],
            "endpoint": overpass.get("endpoint"),
            "retrieved_at": overpass["retrieved_at"],
            "snapshot": "osm_overpass.json",
        }
        for element in overpass["elements"]:
            tags = element.get("tags", {})
            if (
                element.get("type") != "way"
                or tags.get("waterway") not in {"river", "stream"}
                or element["id"] in ways
            ):
                continue
            if not known_node_ids.intersection(element.get("nodes", [])):
                unconnected_waterways.append(
                    {
                        "osm_way_id": element["id"],
                        "name": tags.get("name"),
                        "waterway": tags["waterway"],
                        "reference": f"https://www.openstreetmap.org/way/{element['id']}",
                        "todo": (
                            "Tidak memiliki node OSM bersama dengan rantai yang "
                            "terverifikasi; tidak dihubungkan ke graf."
                        ),
                    }
                )
    source_nodes = [
        {
            "key": "mlirip",
            "name": "Kali Surabaya · simpul OSM di sisi Mlirip",
            "type": "sungai",
            "osm_node_id": 6537680329,
            "lat": nodes[6537680329]["lat"],
            "lng": nodes[6537680329]["lon"],
            "region_code": None,
            "source_data": "osm",
            "is_simulated": False,
            "referensi": [osm_node_urls[6537680329], *references([934029648])],
            "catatan": (
                "Simpul geometri sungai OSM yang berada di sisi Mlirip; "
                "bukan verifikasi lokasi Bendung Mlirip."
            ),
        },
        {
            "key": "jagir-junction",
            "name": "Kali Jagir · simpang OSM dengan Kali Surabaya",
            "type": "sungai",
            "osm_node_id": 312077143,
            "lat": nodes[312077143]["lat"],
            "lng": nodes[312077143]["lon"],
            "region_code": None,
            "source_data": "osm",
            "is_simulated": False,
            "referensi": [
                osm_node_urls[312077143],
                *references([29100243, 464034862, 309956660]),
            ],
            "catatan": "Simpang alur OSM; bukan lokasi intake atau bendung terverifikasi.",
        },
        {
            "key": "jagir-ngagel",
            "name": "Kali Jagir · simpul OSM di Ngagel",
            "type": "sungai",
            "osm_node_id": 4592052456,
            "lat": nodes[4592052456]["lat"],
            "lng": nodes[4592052456]["lon"],
            "region_code": None,
            "source_data": "osm",
            "is_simulated": False,
            "referensi": [osm_node_urls[4592052456], *references([464034861])],
            "catatan": "Titik di alur OSM; bukan verifikasi intake PDAM Ngagel.",
        },
        {
            "key": "kali-mas-end",
            "name": f"Kali Mas · simpul OSM {mas_nodes[-1]}",
            "type": "sungai",
            "osm_node_id": mas_nodes[-1],
            "lat": nodes[mas_nodes[-1]]["lat"],
            "lng": nodes[mas_nodes[-1]]["lon"],
            "region_code": None,
            "source_data": "osm",
            "is_simulated": False,
            "referensi": [osm_node_urls[mas_nodes[-1]], *references(mas_chain)],
            "catatan": "Nama OSM tercatat sebagai 'Kali Mas'; alias 'Kalimas' belum diverifikasi.",
        },
    ]
    edge_rows = [
        {
            "from": "mlirip",
            "to": "jagir-junction",
            "jarak_km": round(main_distance, 3),
            "sumber_jarak": "geometri_osm",
            "terverifikasi": True,
            "referensi": references(main_chain),
        },
        {
            "from": "jagir-junction",
            "to": "jagir-ngagel",
            "jarak_km": round(jagir_distance, 3),
            "sumber_jarak": "geometri_osm",
            "terverifikasi": True,
            "referensi": references(jagir_chain[:2]),
        },
        {
            "from": "jagir-junction",
            "to": "kali-mas-end",
            "jarak_km": round(mas_distance, 3),
            "sumber_jarak": "geometri_osm",
            "terverifikasi": True,
            "referensi": references(mas_chain),
        },
    ]
    payload = {
        "source": "OpenStreetMap API 0.6",
        "retrieved_at": _now_utc(),
        "attribution": "© OpenStreetMap contributors",
        "license": "Open Database License (ODbL) 1.0",
        "overpass_snapshot": overpass_summary,
        "method": (
            "Koordinat diambil dari node OSM. Jarak adalah jumlah jarak great-circle "
            "antar-node pada geometri way berurutan; urutan way dipastikan dengan "
            "ID node ujung yang sama. Arah waterway=river mengikuti urutan node OSM "
            "yang didokumentasikan sebagai arah hilir."
        ),
        "method_reference": "https://wiki.openstreetmap.org/wiki/Tag:waterway%3Driver",
        "osm_nodes": list(nodes.values()),
        "osm_ways": list(ways.values()),
        "sources": source_nodes,
        "edges": edge_rows,
        "unconnected_waterway_ways": unconnected_waterways,
        "unverified_points": _unverified_points(),
        "osm_references": {
            "node": osm_node_urls,
            "way": way_urls,
            "nominatim_searches": [
                "https://nominatim.openstreetmap.org/search?q=Kali+Surabaya%2C+Jawa+Timur&format=jsonv2&limit=40",
                "https://nominatim.openstreetmap.org/search?q=Kali+Jagir%2C+Surabaya&format=jsonv2&limit=20",
            ],
        },
    }
    _write_json(DATA_DIR / "osm_river_geometry.json", payload)
    _write_json(
        DATA_DIR / "titik_pantau.json",
        {
            "source": "OpenStreetMap API 0.6",
            "retrieved_at": payload["retrieved_at"],
            "attribution": payload["attribution"],
            "license": payload["license"],
            "verified_osm_nodes": source_nodes,
            "unverified_points": payload["unverified_points"],
        },
    )
    print(
        f"Snapshot OSM disimpan: {len(ways)} way, {len(source_nodes)} simpul nyata, "
        f"{len(edge_rows)} edge terverifikasi."
    )


def _title_name(name):
    if name.startswith("KAB. "):
        return "Kabupaten " + name[5:].title()
    if name.startswith("KOTA "):
        return "Kota " + name[5:].title()
    return name.title()


def refresh_administrative_regions():
    period_mapping = _request_json(f"{BPS_API}/period-mapping")
    if not any(
        item.get("periode_bps") == BPS_PERIOD
        and item.get("periode_kl") == PUM_PERIOD
        and item.get("id_bridging") == 1
        for item in period_mapping
    ):
        raise ValueError("Periode BPS/Kemendagri yang diminta tidak tersedia.")

    params = urlencode({"periode_bps": BPS_PERIOD, "periode_pum": PUM_PERIOD})
    provinces = _request_json(f"{BPS_API}/provinces?{params}")
    province = next(
        (row for row in provinces if row.get("kode_bps") == PROVINCE_CODE), None
    )
    if province is None:
        raise ValueError("Kode provinsi Jawa Timur tidak ditemukan di API BPS.")

    regencies = _request_json(
        f"{BPS_API}/regencies/{PROVINCE_CODE}?{params}"
    )
    selected = [
        row for row in regencies if row.get("nama_bps") in CORRIDOR_REGENCIES
    ]
    missing = CORRIDOR_REGENCIES - {row.get("nama_bps") for row in selected}
    if missing:
        raise ValueError(f"Wilayah BPS tidak ditemukan: {sorted(missing)}")

    regions = [
        {
            "kode_bps": province["kode_bps"],
            "nama": "Jawa Timur",
            "level": "provinsi",
            "parent_code": None,
            "kode_pum": province.get("kode_pum"),
        }
    ]
    for regency in selected:
        level = "kota" if regency["nama_bps"].startswith("KOTA ") else "kabupaten"
        regions.append(
            {
                "kode_bps": regency["kode_bps"],
                "nama": _title_name(regency["nama_bps"]),
                "level": level,
                "parent_code": province["kode_bps"],
                "kode_pum": regency.get("kode_pum"),
            }
        )
        districts = _request_json(
            f"{BPS_API}/districts/{regency['kode_bps']}?{params}"
        )
        for district in districts:
            regions.append(
                {
                    "kode_bps": district["kode_bps"],
                    "nama": district["nama_bps"].title(),
                    "level": "kecamatan",
                    "parent_code": regency["kode_bps"],
                    "kode_pum": district.get("kode_pum"),
                }
            )

    payload = {
        "source": "BPS WebGIS Kode Relasi Wilayah",
        "source_url": "https://sig.bps.go.id/kode-relasi",
        "api_base": BPS_API,
        "retrieved_at": _now_utc(),
        "period_bps": BPS_PERIOD,
        "period_kemendagri": PUM_PERIOD,
        "province_code": PROVINCE_CODE,
        "attribution": "Badan Pusat Statistik (BPS) dan Kementerian Dalam Negeri",
        "regions": regions,
    }
    _write_json(DATA_DIR / "wilayah_administratif.json", payload)
    print(f"Snapshot wilayah BPS disimpan: {len(regions)} entri administratif.")


def _parse_publication_csv(path):
    required = {
        "titik",
        "tanggal",
        "ph",
        "kekeruhan_ntu",
        "tds_mgl",
        "sumber",
        "referensi",
    }
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(
                "CSV harus memiliki kolom: "
                + ", ".join(sorted(required))
            )
        rows = []
        seen = set()
        for line_number, row in enumerate(reader, start=2):
            try:
                point = row["titik"].strip()
                measured_on = date.fromisoformat(row["tanggal"].strip())
                measurements = {
                    "ph": float(row["ph"]),
                    "kekeruhan_ntu": float(row["kekeruhan_ntu"]),
                    "tds_mgl": float(row["tds_mgl"]),
                }
                source_name = row["sumber"].strip()
                reference = row["referensi"].strip()
            except (AttributeError, TypeError, ValueError) as error:
                raise ValueError(f"Baris {line_number}: format kolom tidak valid.") from error
            limits = {"ph": (0, 14), "kekeruhan_ntu": (0, 1000), "tds_mgl": (0, 5000)}
            if not point or not source_name or not reference:
                raise ValueError(
                    f"Baris {line_number}: titik, sumber, dan referensi wajib diisi."
                )
            for field, value in measurements.items():
                lower, upper = limits[field]
                if not math.isfinite(value) or not lower <= value <= upper:
                    raise ValueError(
                        f"Baris {line_number}: {field} di luar rentang fisik."
                    )
            key = (point.casefold(), measured_on, source_name.casefold(), reference)
            if key in seen:
                raise ValueError(f"Baris {line_number}: duplikat di dalam CSV.")
            seen.add(key)
            rows.append(
                {
                    "point": point,
                    "date": measured_on,
                    "measurements": measurements,
                    "source_name": source_name,
                    "reference": reference,
                }
            )
    return rows


def import_publication_results(path):
    from app import create_app, db
    from app.data_migrations import ensure_phase_d_schema
    from app.models import TestResult, WaterSource

    rows = _parse_publication_csv(path)
    if not rows:
        print("CSV valid; tidak ada hasil uji untuk diimpor.")
        return

    app = create_app()
    with app.app_context():
        db.create_all()
        ensure_phase_d_schema()
        imported = 0
        for row in rows:
            matches = (
                WaterSource.query.filter_by(
                    nama=row["point"], is_simulated=False
                )
                .order_by(WaterSource.id)
                .all()
            )
            if len(matches) != 1 or matches[0].sumber_data not in {
                "osm",
                "publikasi",
                "resmi",
            }:
                raise ValueError(
                    f"Titik {row['point']!r} tidak cocok dengan sumber nyata "
                    "terverifikasi di basis data."
                )
            source = matches[0]
            result_ref = f"{row['source_name']} | {row['reference']}"
            existing = TestResult.query.filter_by(
                source_id=source.id,
                tanggal_pengambilan=row["date"],
                sumber_data="publikasi",
                referensi=result_ref,
            ).first()
            if existing is not None:
                if any(
                    getattr(existing, field) != value
                    for field, value in row["measurements"].items()
                ):
                    raise ValueError(
                        f"Data publikasi duplikat dengan nilai berbeda: {row['point']} "
                        f"{row['date']}."
                    )
                continue
            db.session.add(
                TestResult(
                    sample_id=None,
                    source_id=source.id,
                    **row["measurements"],
                    vonis=None,
                    jejak_keputusan=(
                        "Hasil publikasi; tidak diklasifikasikan dengan ambang "
                        "contoh AquaTrace."
                    ),
                    sumber_data="publikasi",
                    referensi=result_ref,
                    tanggal_pengambilan=row["date"],
                )
            )
            imported += 1
        db.session.commit()
        print(f"Hasil publikasi tersimpan: {imported}; duplikat dilewati.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument(
        "--refresh-overpass",
        action="store_true",
        help="Ambil fitur sungai dan titik bernama dari Overpass API.",
    )
    actions.add_argument(
        "--refresh-osm-ways",
        action="store_true",
        help="Perbarui geometri way OSM yang telah diverifikasi.",
    )
    actions.add_argument(
        "--refresh-regions",
        action="store_true",
        help="Ambil hirarki BPS/Kemendagri untuk koridor sungai.",
    )
    actions.add_argument(
        "--import-results",
        nargs="?",
        const=str(DATA_DIR / "hasil_uji.csv"),
        help="Validasi dan impor hasil publikasi dari CSV.",
    )
    args = parser.parse_args()

    if args.refresh_overpass:
        payload = fetch_overpass()
        _write_json(DATA_DIR / "osm_overpass.json", payload)
        print(f"Data Overpass disimpan: {len(payload['elements'])} fitur.")
    elif args.refresh_osm_ways:
        refresh_osm_ways()
    elif args.refresh_regions:
        refresh_administrative_regions()
    else:
        import_publication_results(Path(args.import_results))


if __name__ == "__main__":
    main()
