import csv
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import io
import requests as req
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template, abort, Response

load_dotenv(Path(__file__).parent.parent / ".env")
from db import (
    init_db, get_all_jobs, get_job, create_job, update_job, delete_job,
    get_summary, get_overdue_followups,
    upsert_scraped_job, get_scraped_job, get_scraped_jobs, mark_scraped_added,
    dismiss_scraped_job, get_scraper_run_stats,
)


def create_app():
    app = Flask(__name__)

    with app.app_context():
        init_db()

    @app.route("/")
    def index():
        return render_template("index.html")

    _JOB_COLS = {"company", "role", "status", "date_applied", "date_updated", "follow_up_date"}

    @app.route("/api/jobs", methods=["GET"])
    def api_list_jobs():
        status = request.args.get("status")
        sort_col = request.args.get("sort", "date_updated")
        sort_dir = request.args.get("dir", "desc").lower()
        if sort_col not in _JOB_COLS:
            sort_col = "date_updated"
        if sort_dir not in ("asc", "desc"):
            sort_dir = "desc"
        return jsonify(get_all_jobs(status=status, order_by=sort_col, order_dir=sort_dir))

    @app.route("/api/jobs", methods=["POST"])
    def api_create_job():
        data = request.get_json()
        if not data or not data.get("company") or not data.get("role"):
            abort(400, "company and role are required")
        return jsonify(create_job(data)), 201

    @app.route("/api/jobs/<int:job_id>", methods=["GET"])
    def api_get_job(job_id):
        job = get_job(job_id)
        if not job:
            abort(404)
        return jsonify(job)

    @app.route("/api/jobs/<int:job_id>", methods=["PUT"])
    def api_update_job(job_id):
        if not get_job(job_id):
            abort(404)
        data = request.get_json()
        return jsonify(update_job(job_id, data))

    @app.route("/api/jobs/<int:job_id>", methods=["DELETE"])
    def api_delete_job(job_id):
        if not get_job(job_id):
            abort(404)
        delete_job(job_id)
        return jsonify({"ok": True})

    @app.route("/api/summary", methods=["GET"])
    def api_summary():
        return jsonify(get_summary())

    @app.route("/api/followups", methods=["GET"])
    def api_followups():
        return jsonify(get_overdue_followups())

    @app.route("/api/scraped", methods=["GET"])
    def api_list_scraped():
        _SCRAPED_COLS = {"company", "role", "scraped_at"}
        sort_col = request.args.get("sort", "scraped_at")
        sort_dir = request.args.get("dir", "desc").lower()
        if sort_col not in _SCRAPED_COLS:
            sort_col = "scraped_at"
        if sort_dir not in ("asc", "desc"):
            sort_dir = "desc"
        return jsonify(get_scraped_jobs(order_by=sort_col, order_dir=sort_dir))

    @app.route("/api/scraped", methods=["POST"])
    def api_ingest_scraped():
        data = request.get_json()
        if not data or not data.get("external_id") or not data.get("role"):
            abort(400, "external_id and role required")
        upsert_scraped_job(data)
        return jsonify({"ok": True}), 201

    @app.route("/api/scraped/<external_id>/dismiss", methods=["POST"])
    def api_dismiss_scraped(external_id):
        if not get_scraped_job(external_id):
            abort(404)
        dismiss_scraped_job(external_id)
        return jsonify({"ok": True})

    @app.route("/api/export/sources", methods=["GET"])
    def api_export_sources():
        jobs = get_scraped_jobs()
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=[
            "role", "company", "location", "source", "scraped_at", "url", "in_tracker"
        ])
        writer.writeheader()
        for job in jobs:
            writer.writerow({
                "role": job["role"],
                "company": job["company"] or "",
                "location": job["location"] or "",
                "source": job["source"] or "",
                "scraped_at": job["scraped_at"],
                "url": job["url"] or "",
                "in_tracker": "Yes" if job["tracker_id"] else "No",
            })
        return Response(
            buf.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=job_sources.csv"}
        )

    @app.route("/api/export/tracker", methods=["GET"])
    def api_export_tracker():
        jobs = get_all_jobs()
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=[
            "company", "role", "status", "date_applied", "follow_up_date",
            "source", "contact", "url", "notes"
        ])
        writer.writeheader()
        for job in jobs:
            writer.writerow({
                "company": job["company"],
                "role": job["role"],
                "status": job["status"],
                "date_applied": job["date_applied"] or "",
                "follow_up_date": job["follow_up_date"] or "",
                "source": job["source"] or "",
                "contact": job["contact"] or "",
                "url": job["url"] or "",
                "notes": job["notes"] or "",
            })
        return Response(
            buf.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=job_tracker.csv"}
        )

    @app.route("/api/block-domain", methods=["POST"])
    def api_block_domain():
        data = request.get_json()
        url = (data or {}).get("url", "").strip()
        if not url:
            abort(400, "url is required")
        domain = urlparse(url).netloc.lower().lstrip("www.")
        if not domain:
            abort(400, "could not extract domain from url")
        blocklist = Path(__file__).parent.parent / "filters" / "blocked_domains.txt"
        existing = set()
        if blocklist.exists():
            existing = {l.strip() for l in blocklist.read_text().splitlines() if l.strip()}
        if domain not in existing:
            with blocklist.open("a") as f:
                f.write(domain + "\n")
        return jsonify({"ok": True, "domain": domain})

    @app.route("/api/config", methods=["GET"])
    def api_get_config():
        config_path = Path(__file__).parent.parent / "filters" / "scraper_config.json"
        queries = []
        linkedin_location = ""
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
                queries = config.get("search_queries", [])
                linkedin_location = config.get("linkedin_location", "")
            except Exception:
                pass
        return jsonify({
            "search_queries": queries,
            "linkedin_location": linkedin_location,
            "run_stats": get_scraper_run_stats(),
        })

    @app.route("/api/config", methods=["POST"])
    def api_set_config():
        data = request.get_json()
        if not data or not isinstance(data.get("search_queries"), list):
            abort(400, "search_queries must be a list")
        queries = data["search_queries"]
        if len(queries) > 8:
            abort(400, "search_queries may contain at most 8 items")
        for item in queries:
            if not isinstance(item, str) or not item.strip():
                abort(400, "each search query must be a non-empty string")
        clean = [item.strip() for item in queries]
        linkedin_location = ""
        if isinstance(data.get("linkedin_location"), str):
            linkedin_location = data["linkedin_location"].strip()
        config_path = Path(__file__).parent.parent / "filters" / "scraper_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"search_queries": clean}
        if linkedin_location:
            payload["linkedin_location"] = linkedin_location
        config_path.write_text(json.dumps(payload, indent=2))
        return jsonify({"ok": True, "search_queries": clean, "linkedin_location": linkedin_location})

    @app.route("/api/test-jsearch", methods=["POST"])
    def api_test_jsearch():
        api_key = os.getenv("JSEARCH_API_KEY", "")
        if not api_key:
            return jsonify({"ok": False, "error": "JSEARCH_API_KEY not set in .env"})
        config_path = Path(__file__).parent.parent / "filters" / "scraper_config.json"
        test_query = "IT support"
        if config_path.exists():
            try:
                queries = json.loads(config_path.read_text()).get("search_queries", [])
                if queries:
                    test_query = queries[0]
            except Exception:
                pass
        try:
            resp = req.get(
                "https://jsearch.p.rapidapi.com/search",
                headers={
                    "x-rapidapi-key": api_key,
                    "x-rapidapi-host": "jsearch.p.rapidapi.com",
                },
                params={"query": test_query, "num_pages": "1"},
                timeout=15,
            )
            resp.raise_for_status()
            count = len(resp.json().get("data") or [])
            return jsonify({"ok": True, "count": count, "query": test_query})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)})

    @app.route("/api/scraped/<external_id>/add", methods=["POST"])
    def api_add_scraped_to_tracker(external_id):
        scraped = get_scraped_job(external_id)
        if not scraped:
            abort(404)
        if scraped["tracker_id"]:
            return jsonify({"ok": True, "tracker_id": scraped["tracker_id"], "already_added": True})
        job = create_job({
            "company": scraped["company"] or "Unknown",
            "role": scraped["role"],
            "url": scraped["url"],
            "source": scraped["source"],
            "status": "watchlist",
            "notes": "Added from job finder",
        })
        mark_scraped_added(external_id, job["id"])
        return jsonify({"ok": True, "tracker_id": job["id"]})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5002, debug=True)
