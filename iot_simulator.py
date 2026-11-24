import argparse
import json
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def build_payload(code, scenario, index, timestamp=None):
    """Create one deterministic simulation reading for a selected scenario."""
    if scenario == "normal":
        measurements = {"ph": 7.2, "kekeruhan_ntu": 1.8, "tds_mgl": 145.0}
    elif scenario == "tercemar":
        measurements = {"ph": 4.0, "kekeruhan_ntu": 20.0, "tds_mgl": 600.0}
    elif scenario == "drift":
        measurements = {
            "ph": min(8.4, 7.0 + index * 0.1),
            "kekeruhan_ntu": 1.0 + index * 1.5,
            "tds_mgl": 120.0 + index * 35.0,
        }
    else:
        raise ValueError(f"Skenario tidak dikenal: {scenario}")
    return {
        "kode": code,
        **measurements,
        "ts": timestamp or datetime.now(timezone.utc).isoformat(),
    }


def send_reading(url, api_key, payload, timeout=10):
    """POST one sensor reading and return parsed JSON plus HTTP status."""
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"Tidak dapat menghubungi endpoint ingest: {error}") from error


def main(argv=None):
    parser = argparse.ArgumentParser(description="Simulator sensor AquaTrace")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--kode", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument(
        "--skenario",
        choices=("normal", "tercemar", "drift"),
        default="normal",
    )
    parser.add_argument("--jumlah", type=int, default=1)
    args = parser.parse_args(argv)
    if args.interval < 0:
        parser.error("--interval tidak boleh negatif.")
    if args.jumlah < 1:
        parser.error("--jumlah harus minimal 1.")

    url = args.base_url.rstrip("/") + "/api/iot/ingest"
    for index in range(args.jumlah):
        payload = build_payload(args.kode, args.skenario, index)
        try:
            status, response = send_reading(url, args.api_key, payload)
        except RuntimeError as error:
            print(str(error), file=sys.stderr)
            return 1
        print(f"HTTP {status}: {json.dumps(response, ensure_ascii=False)}")
        if index + 1 < args.jumlah:
            time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
