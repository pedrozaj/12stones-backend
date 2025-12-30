#!/usr/bin/env python3
"""Generate API-ENDPOINTS.md from FastAPI routes."""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Set minimal environment to allow import
import os
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/dummy")
os.environ.setdefault("JWT_SECRET", "dummy")
os.environ.setdefault("R2_ACCOUNT_ID", "dummy")
os.environ.setdefault("R2_ACCESS_KEY_ID", "dummy")
os.environ.setdefault("R2_SECRET_ACCESS_KEY", "dummy")
os.environ.setdefault("R2_BUCKET_NAME", "dummy")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")


def generate_api_docs() -> str:
    """Generate API documentation from FastAPI app."""
    from app.main import app

    lines = [
        "# API Endpoints",
        "",
        "> Auto-generated from FastAPI routes. DO NOT EDIT MANUALLY.",
        "",
        "Base URL: `https://api.12stones.app` (production) or `http://localhost:8000` (development)",
        "",
    ]

    # Group routes by tag
    routes_by_tag: dict[str, list] = {}

    for route in app.routes:
        if not hasattr(route, "methods"):
            continue

        tags = getattr(route, "tags", ["Other"])
        tag = tags[0] if tags else "Other"

        if tag not in routes_by_tag:
            routes_by_tag[tag] = []

        for method in route.methods:
            if method in ("HEAD", "OPTIONS"):
                continue

            routes_by_tag[tag].append({
                "method": method,
                "path": route.path,
                "summary": getattr(route, "summary", None) or route.name or "",
                "description": getattr(route, "description", "") or "",
            })

    # Generate markdown for each tag
    for tag, routes in sorted(routes_by_tag.items()):
        lines.append(f"## {tag}")
        lines.append("")

        for route in sorted(routes, key=lambda r: (r["path"], r["method"])):
            method = route["method"]
            path = route["path"]
            summary = route["summary"]

            lines.append(f"### `{method} {path}`")
            lines.append("")
            if summary:
                lines.append(summary)
                lines.append("")

    return "\n".join(lines)


def main():
    """Generate API-ENDPOINTS.md file."""
    docs_dir = backend_dir.parent / "12stones-docs"
    output_path = docs_dir / "API-ENDPOINTS.md"

    api_docs = generate_api_docs()

    output_path.write_text(api_docs)
    print(f"Generated {output_path}")


if __name__ == "__main__":
    main()
