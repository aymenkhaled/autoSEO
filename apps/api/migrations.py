"""Startup migration runner for SQL files in supabase/migrations."""
from __future__ import annotations

from pathlib import Path
from typing import List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "supabase" / "migrations"


def _split_sql_statements(script: str) -> List[str]:
    """Split a PostgreSQL SQL script into executable statements."""
    statements: List[str] = []
    current: List[str] = []
    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False
    dollar_tag: str | None = None
    i = 0
    length = len(script)

    while i < length:
        char = script[i]
        next_char = script[i + 1] if i + 1 < length else ""

        if in_line_comment:
            current.append(char)
            if char == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            current.append(char)
            if char == "*" and next_char == "/":
                current.append(next_char)
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if dollar_tag:
            if script.startswith(dollar_tag, i):
                current.append(dollar_tag)
                i += len(dollar_tag)
                dollar_tag = None
                continue
            current.append(char)
            i += 1
            continue

        if not in_single and not in_double:
            if char == "-" and next_char == "-":
                current.append(char)
                current.append(next_char)
                in_line_comment = True
                i += 2
                continue
            if char == "/" and next_char == "*":
                current.append(char)
                current.append(next_char)
                in_block_comment = True
                i += 2
                continue
            if char == "$":
                end = i + 1
                while end < length and (script[end].isalnum() or script[end] == "_"):
                    end += 1
                if end < length and script[end] == "$":
                    tag = script[i : end + 1]
                    current.append(tag)
                    dollar_tag = tag
                    i = end + 1
                    continue

        if char == "'" and not in_double:
            current.append(char)
            if in_single and next_char == "'":
                current.append(next_char)
                i += 2
                continue
            in_single = not in_single
            i += 1
            continue

        if char == '"' and not in_single:
            current.append(char)
            in_double = not in_double
            i += 1
            continue

        if char == ";" and not in_single and not in_double:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            i += 1
            continue

        current.append(char)
        i += 1

    trailing = "".join(current).strip()
    if trailing:
        statements.append(trailing)

    return statements


async def run_startup_migrations(engine: AsyncEngine, logger) -> None:
    """Apply SQL migrations once and record them in schema_migrations."""
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        logger.warning("startup_migrations_missing", path=str(MIGRATIONS_DIR))
        return

    async with engine.connect() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        await conn.commit()

        applied_rows = await conn.execute(text("SELECT version FROM schema_migrations"))
        applied = {row[0] for row in applied_rows}

        for migration_path in migration_files:
            version = migration_path.name
            if version in applied:
                continue

            sql = migration_path.read_text(encoding="utf-8").strip()
            if not sql:
                continue

            logger.info("startup_migration_applying", version=version)
            try:
                for statement in _split_sql_statements(sql):
                    await conn.exec_driver_sql(statement)
                await conn.execute(
                    text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                    {"version": version},
                )
                await conn.commit()
            except Exception as exc:
                await conn.rollback()
                logger.error(
                    "startup_migration_failed",
                    version=version,
                    error=str(exc).encode("ascii", "replace").decode("ascii"),
                )
                raise
