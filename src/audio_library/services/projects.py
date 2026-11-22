"""Music production project link CRUD and OS shell opening."""

import os
import subprocess
import sys

from .. import database


def ensure_project_link(conn, entity_type: str, entity_id: str, project_path, project_name=None, notes=None):
    """Creates a project link if project_path is non-empty and not already linked to the entity."""
    if not project_path:
        return None
    project_path = str(project_path).strip()
    if not project_path:
        return None

    existing = conn.execute(
        "SELECT id FROM projects WHERE entity_type = ? AND entity_id = ? AND project_path = ?",
        (entity_type, entity_id, project_path),
    ).fetchone()
    if existing:
        return existing["id"]

    clean_name = str(project_name or "").strip()
    if not clean_name:
        clean_name = os.path.basename(project_path.rstrip("\\/")) or project_path

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO projects (project_name, project_path, entity_type, entity_id, notes) "
        "VALUES (?, ?, ?, ?, ?)",
        (clean_name, project_path, entity_type, entity_id, (notes or "").strip() or None),
    )
    return cursor.lastrowid


def _validate_project_payload(project_data: dict):
    entity_type = str(project_data.get("entity_type", "")).strip().lower()
    entity_id = str(project_data.get("entity_id", "")).strip()
    project_path = str(project_data.get("project_path", "")).strip()
    project_name = str(project_data.get("project_name", "")).strip()
    notes = str(project_data.get("notes", "")).strip()

    if entity_type not in ("song", "artist", "album"):
        return None, "Entity type must be song, artist, or album"
    if not entity_id:
        return None, "Target entity is required"
    if not project_path:
        return None, "Project path is required"
    if not project_name:
        project_name = os.path.basename(project_path.rstrip("\\/")) or project_path

    return (project_name, project_path, entity_type, entity_id, notes or None), None


def create_project(db_path: str, project_data: dict) -> dict:
    validated, error = _validate_project_payload(project_data)
    if error:
        return {"status": "error", "message": error}

    project_name, project_path, entity_type, entity_id, notes = validated
    conn = database.get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO projects (project_name, project_path, entity_type, entity_id, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (project_name, project_path, entity_type, entity_id, notes),
        )
        conn.commit()
        return {"status": "success", "id": cursor.lastrowid, "project_name": project_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def update_project(db_path: str, project_id, project_data: dict) -> dict:
    validated, error = _validate_project_payload(project_data)
    if error:
        return {"status": "error", "message": error}

    project_name, project_path, entity_type, entity_id, notes = validated
    conn = database.get_db_connection(db_path)
    try:
        conn.execute(
            "UPDATE projects SET project_name = ?, project_path = ?, entity_type = ?, entity_id = ?, notes = ? "
            "WHERE id = ?",
            (project_name, project_path, entity_type, entity_id, notes, int(project_id)),
        )
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def delete_project(db_path: str, project_id) -> dict:
    conn = database.get_db_connection(db_path)
    try:
        conn.execute("DELETE FROM projects WHERE id = ?", (int(project_id),))
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def get_projects(db_path: str, entity_type=None, entity_id=None) -> list[dict]:
    conn = database.get_db_connection(db_path)
    try:
        clauses, params = [], []
        if entity_type:
            clauses.append("p.entity_type = ?")
            params.append(entity_type)
        if entity_id:
            clauses.append("p.entity_id = ?")
            params.append(entity_id)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"""
            SELECT p.id, p.project_name, p.project_path, p.entity_type, p.entity_id,
                   p.notes, p.created_at,
                   CASE p.entity_type
                       WHEN 'song' THEN (SELECT s.song_name FROM songs s WHERE s.song_file = p.entity_id)
                       WHEN 'artist' THEN (SELECT a.real_name FROM artists a WHERE a.slug = p.entity_id)
                       WHEN 'album' THEN (SELECT al.album_name FROM albums al WHERE al.slug = p.entity_id)
                   END as entity_label
            FROM projects p
            {where_sql}
            ORDER BY p.created_at DESC, p.id DESC
        """
        rows = conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["entity_label"] = item["entity_label"] or item["entity_id"]
            item["path_exists"] = bool(item["project_path"] and os.path.exists(item["project_path"]))
            results.append(item)
        return results
    finally:
        conn.close()


def open_project_path(project_path: str) -> dict:
    if not project_path:
        return {"status": "error", "message": "Project path is empty"}
    if not os.path.exists(project_path):
        return {"status": "error", "message": f"Path not found on disk: {project_path}"}
    try:
        if sys.platform.startswith("win"):
            os.startfile(project_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", project_path])
        else:
            subprocess.Popen(["xdg-open", project_path])
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
