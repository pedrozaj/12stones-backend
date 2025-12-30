#!/usr/bin/env python3
"""Generate SCHEMA.sql from SQLAlchemy models."""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.schema import CreateTable

from app.database import Base

# Import all models to register them with Base
from app.models import (  # noqa: F401
    User,
    Project,
    ProjectSettings,
    ContentItem,
    ContentAnalysis,
    VoiceProfile,
    Narrative,
    Video,
    Job,
    SocialConnection,
)


def generate_schema() -> str:
    """Generate SQL schema from SQLAlchemy models."""
    # Use PostgreSQL dialect for accurate schema
    engine = create_engine("postgresql://localhost/dummy", echo=False)

    lines = [
        "-- 12 Stones Database Schema",
        "-- Auto-generated from SQLAlchemy models",
        "-- DO NOT EDIT MANUALLY",
        "",
        "-- PostgreSQL 16",
        "",
    ]

    # Generate CREATE TABLE statements
    for table in Base.metadata.sorted_tables:
        create_stmt = str(CreateTable(table).compile(engine))
        lines.append(create_stmt.strip())
        lines.append("")
        lines.append("")

    return "\n".join(lines)


def main():
    """Generate SCHEMA.sql file."""
    docs_dir = backend_dir.parent / "12stones-docs"
    output_path = docs_dir / "SCHEMA.sql"

    schema_sql = generate_schema()

    output_path.write_text(schema_sql)
    print(f"Generated {output_path}")


if __name__ == "__main__":
    main()
