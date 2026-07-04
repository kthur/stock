"""P3: REST API endpoints for serving prediction results as JSON.

Dash uses Flask under the hood. We register additional routes on
``server`` (the Flask app exposed by dashboard.py) so the same process
serves both the interactive dashboard UI and a machine-readable API.

Endpoints
---------
GET /api/v1/predictions/latest      – pipeline_result.jsonl (regression)
GET /api/v1/surge/latest            – surge_predictions.jsonl
GET /api/v1/vcp/latest              – vcp_patterns.txt  (parsed)
GET /api/v1/lead_lag/latest         – lead_lag_predictions.txt (parsed)
GET /api/v1/health                  – system health / last-run info

All endpoints return JSON with the schema::

    {
        "status": "ok" | "no_data",
        "generated_at": "<ISO-8601 timestamp of file>",
        "count": <number of records>,
        "data": [ ... ]
    }

Error responses::

    {"status": "error", "message": "..."}
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper: locate result directory
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent  # src/web/

def _result_dir() -> Path:
    """Return the pipeline result directory (trading_system/result/)."""
    candidates = [
        _HERE / ".." / ".." / "result",                        # src/web/../../result
        _HERE / ".." / ".." / ".." / "trading_system" / "result",  # from project root
        Path("trading_system") / "result",
    ]
    for c in candidates:
        p = c.resolve()
        if p.exists():
            return p
    return candidates[0].resolve()  # fallback (may not exist)


def _file_ts(path: Path) -> Optional[str]:
    """Return ISO-8601 mtime of *path*, or None if missing."""
    try:
        mtime = path.stat().st_mtime
        return datetime.fromtimestamp(mtime).isoformat()
    except OSError:
        return None


def _ok(data: List[Any], path: Path) -> Dict:
    return {
        "status": "ok",
        "generated_at": _file_ts(path),
        "count": len(data),
        "data": data,
    }


def _no_data(filename: str) -> Dict:
    return {"status": "no_data", "message": f"{filename} not found or empty"}


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _load_jsonl(path: Path) -> List[Dict]:
    """Load JSON-Lines file and return list of dicts."""
    records = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except OSError:
        pass
    return records


def _parse_vcp_txt(path: Path) -> List[Dict]:
    """Parse vcp_patterns.txt into a list of structured dicts."""
    results: List[Dict] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return results

    # Each entry looks like:
    #   N. [MARKET] CODE (Name)
    #      Score: X/100 | ...
    pattern = re.compile(
        r"\d+\.\s+\[(\w+)\]\s+(\S+)\s+\(([^)]+)\)\s*\n"
        r"\s+Score:\s*([\d.]+)/100\s*\|([^\n]+)"
    )
    for m in pattern.finditer(text):
        market, symbol, name, score, rest = m.groups()
        entry = {
            "market": market,
            "symbol": symbol,
            "name": name.strip(),
            "score": float(score),
        }
        # Parse extra flags from rest line
        for flag in ("Above MA50", "Above MA200", "Near high", "Volume declining"):
            entry[flag.lower().replace(" ", "_")] = "✓" in rest.split(flag)[-1][:5] if flag in rest else None
        results.append(entry)
    return results


def _parse_lead_lag_txt(path: Path) -> List[Dict]:
    """Parse lead_lag_predictions.txt into list of dicts."""
    results: List[Dict] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return results

    # Lines like:  N. [MARKET] CODE (Name): 45.32%
    pattern = re.compile(r"\d+\.\s+\[(\w+)\]\s+(\S+)\s+\(([^)]+)\):\s*([\d.]+)%")
    for m in pattern.finditer(text):
        market, symbol, name, score = m.groups()
        results.append({
            "market": market,
            "symbol": symbol,
            "name": name.strip(),
            "lead_lag_score_pct": float(score),
        })
    return results


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def register_api_routes(flask_server) -> None:
    """Register REST API routes on the Flask server used by Dash.

    Call this once after ``app = dash.Dash(...)`` and before ``app.run()``.

    Example::

        from src.web.api import register_api_routes
        register_api_routes(app.server)
    """

    @flask_server.route("/api/v1/health")
    def api_health():
        from flask import jsonify
        rdir = _result_dir()
        pipeline_path = rdir / "pipeline_result.txt"
        last_run = None
        total_symbols = None
        try:
            if pipeline_path.exists():
                header = pipeline_path.read_text(encoding="utf-8")[:400]
                dm = re.search(r"Date:\s*(.+)", header)
                sm = re.search(r"Total symbols analyzed:\s*(\d+)", header)
                if dm:
                    last_run = dm.group(1).strip()
                if sm:
                    total_symbols = int(sm.group(1))
        except Exception:
            pass
        return jsonify({
            "status": "ok",
            "last_pipeline_run": last_run,
            "total_symbols_analyzed": total_symbols,
            "result_dir": str(rdir),
            "server_time": datetime.utcnow().isoformat() + "Z",
        })

    @flask_server.route("/api/v1/predictions/latest")
    def api_predictions_latest():
        from flask import jsonify, request
        rdir = _result_dir()
        path = rdir / "pipeline_result.jsonl"
        if not path.exists():
            return jsonify(_no_data("pipeline_result.jsonl")), 404
        records = _load_jsonl(path)
        # Optional query filters: ?market=KOSPI&horizon=1&limit=50
        market = request.args.get("market", "").upper()
        try:
            horizon = int(request.args.get("horizon", 0))
        except ValueError:
            horizon = 0
        try:
            limit = min(int(request.args.get("limit", 500)), 5000)
        except ValueError:
            limit = 500
        if market:
            records = [r for r in records if r.get("market", "").upper() == market]
        if horizon:
            records = [r for r in records if horizon in r or str(horizon) in r]
        records = records[:limit]
        return jsonify(_ok(records, path))

    @flask_server.route("/api/v1/surge/latest")
    def api_surge_latest():
        from flask import jsonify, request
        rdir = _result_dir()
        path = rdir / "surge_predictions.jsonl"
        if not path.exists():
            return jsonify(_no_data("surge_predictions.jsonl")), 404
        records = _load_jsonl(path)
        market = request.args.get("market", "").upper()
        try:
            limit = min(int(request.args.get("limit", 200)), 2000)
        except ValueError:
            limit = 200
        if market:
            records = [r for r in records if r.get("market", "").upper() == market]
        records = records[:limit]
        return jsonify(_ok(records, path))

    @flask_server.route("/api/v1/vcp/latest")
    def api_vcp_latest():
        from flask import jsonify
        rdir = _result_dir()
        path = rdir / "vcp_patterns.txt"
        if not path.exists():
            return jsonify(_no_data("vcp_patterns.txt")), 404
        records = _parse_vcp_txt(path)
        return jsonify(_ok(records, path))

    @flask_server.route("/api/v1/lead_lag/latest")
    def api_lead_lag_latest():
        from flask import jsonify
        rdir = _result_dir()
        path = rdir / "lead_lag_predictions.txt"
        if not path.exists():
            return jsonify(_no_data("lead_lag_predictions.txt")), 404
        records = _parse_lead_lag_txt(path)
        return jsonify(_ok(records, path))

    logger.info(
        "Registered REST API routes: /api/v1/health, /api/v1/predictions/latest, "
        "/api/v1/surge/latest, /api/v1/vcp/latest, /api/v1/lead_lag/latest"
    )
