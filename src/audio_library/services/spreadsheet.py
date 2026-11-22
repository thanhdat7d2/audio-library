"""Spreadsheet (.csv, .tsv, .xlsx) parsing, preview, batch import, and template export."""

import csv
import datetime
import os
import re

from . import songs as songs_service

COLUMN_ALIASES = {
    "song_name": ("song_name", "song", "title", "song_title", "track", "track_name", "name"),
    "file_path": ("file_path", "audio_file", "audio_path", "audio", "file", "path"),
    "main_artists": ("main_artists", "main_artist", "artists", "artist"),
    "featured_artists": ("featured_artists", "featured_artist", "feat_artists", "featured", "feat", "featuring"),
    "album": ("album", "album_name", "album_slug"),
    "track_number": ("track_number", "track_no", "track_num", "track_#"),
    "genres": ("genres", "genre"),
    "tags": ("tags", "tag"),
    "ai_generated": ("ai_generated", "is_ai", "ai", "ai_gen"),
    "key": ("key", "musical_key", "key_name"),
    "scale": ("scale", "scale_name", "mode"),
    "tempo": ("tempo", "bpm"),
    "release_date": ("release_date", "date", "year"),
    "project_path": ("project_path", "project", "daw_project", "project_link"),
    "project_name": ("project_name",),
}

TEMPLATE_HEADERS = [
    "song_name", "main_artists", "featured_artists", "album", "track_number",
    "genres", "tags", "ai_generated", "key", "scale", "tempo",
    "release_date", "file_path", "project_path", "project_name",
]


def _normalize_header(header) -> str:
    text = str(header or "").strip().lower()
    text = re.sub(r"[\s\-/]+", "_", text)
    text = re.sub(r"[^a-z0-9_#]", "", text)
    return text.strip("_")


def _split_multi_value(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in re.split(r"[;,]", text) if part.strip()]


def _parse_bool_flag(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value or "").strip().lower() in ("1", "true", "yes", "y", "ai", "x")


def _stringify_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def read_spreadsheet_rows(file_path: str) -> tuple[list[str], list[dict]]:
    """Reads headers and row dicts from a .csv, .tsv, or .xlsx file."""
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError("Spreadsheet file not found")

    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".csv", ".tsv"):
        with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
            sample = f.read(4096)
            f.seek(0)
            delimiter = "\t" if ext == ".tsv" else ","
            if ext == ".csv" and sample:
                try:
                    delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
                except csv.Error:
                    delimiter = ","
            reader = csv.DictReader(f, delimiter=delimiter)
            headers = [h for h in (reader.fieldnames or []) if h is not None]
            rows = []
            for row in reader:
                clean = {k: _stringify_cell(v) for k, v in row.items() if k is not None}
                if any(clean.values()):
                    rows.append(clean)
            return headers, rows

    if ext == ".xlsx":
        try:
            import openpyxl
        except ImportError as exc:
            raise RuntimeError("openpyxl is required to import .xlsx files. Install it with: pip install openpyxl") from exc

        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        try:
            ws = wb.active
            row_iter = ws.iter_rows(values_only=True)
            try:
                raw_headers = next(row_iter)
            except StopIteration:
                return [], []
            headers = [_stringify_cell(h) for h in raw_headers]
            rows = []
            for raw_row in row_iter:
                row_dict = {}
                for idx, header in enumerate(headers):
                    if not header:
                        continue
                    val = raw_row[idx] if idx < len(raw_row) else None
                    row_dict[header] = _stringify_cell(val)
                if any(row_dict.values()):
                    rows.append(row_dict)
            return [h for h in headers if h], rows
        finally:
            wb.close()

    raise ValueError(f"Unsupported spreadsheet format: {ext}. Use .csv, .tsv, or .xlsx")


def build_header_map(headers: list[str]) -> dict[str, str]:
    normalized_to_raw = {_normalize_header(h): h for h in headers}
    mapped = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized_to_raw:
                mapped[canonical] = normalized_to_raw[alias]
                break
    return mapped


def map_row(raw_row: dict, header_map: dict, base_dir: str) -> tuple[str | None, dict]:
    def get_field(name: str) -> str:
        col = header_map.get(name)
        return raw_row.get(col, "").strip() if col else ""

    file_path = get_field("file_path")
    if file_path and not os.path.isabs(file_path):
        candidate = os.path.join(base_dir, file_path)
        if os.path.exists(candidate):
            file_path = candidate

    tags = _split_multi_value(get_field("tags"))
    if _parse_bool_flag(get_field("ai_generated")) and not any(t.lower() == "ai generated" for t in tags):
        tags.append("AI Generated")

    song_data = {
        "song_name": get_field("song_name"),
        "main_artists": _split_multi_value(get_field("main_artists")),
        "featured_artists": _split_multi_value(get_field("featured_artists")),
        "album_slug": get_field("album") or None,
        "track_number": get_field("track_number") or None,
        "genres": _split_multi_value(get_field("genres")),
        "tags": tags,
        "key": get_field("key") or None,
        "scale": get_field("scale") or None,
        "tempo": get_field("tempo") or None,
        "release_date": get_field("release_date") or None,
        "project_path": get_field("project_path") or None,
        "project_name": get_field("project_name") or None,
    }
    return (file_path or None), song_data


def preview_spreadsheet(file_path: str) -> dict:
    try:
        headers, rows = read_spreadsheet_rows(file_path)
        header_map = build_header_map(headers)
        base_dir = os.path.dirname(os.path.abspath(file_path))

        preview = []
        for idx, raw_row in enumerate(rows[:10], start=2):
            audio_path, song_data = map_row(raw_row, header_map, base_dir)
            preview.append(
                {
                    "row": idx,
                    "song_name": song_data["song_name"] or (os.path.splitext(os.path.basename(audio_path))[0] if audio_path else ""),
                    "main_artists": ", ".join(song_data["main_artists"]),
                    "album": song_data["album_slug"] or "",
                    "genres": ", ".join(song_data["genres"]),
                    "tags": ", ".join(song_data["tags"]),
                    "has_audio": bool(audio_path),
                    "audio_exists": bool(audio_path and os.path.exists(audio_path)),
                    "project_path": song_data["project_path"] or "",
                }
            )

        return {
            "status": "success",
            "file_name": os.path.basename(file_path),
            "headers": headers,
            "mapped_columns": header_map,
            "total_rows": len(rows),
            "preview_rows": preview,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def import_songs_from_spreadsheet(db_path: str, library_path: str, file_path: str) -> dict:
    try:
        headers, rows = read_spreadsheet_rows(file_path)
        header_map = build_header_map(headers)
        if "song_name" not in header_map and "file_path" not in header_map:
            return {
                "status": "error",
                "message": "Spreadsheet must include at least a 'song_name' (or 'title') or 'file_path' column.",
            }

        base_dir = os.path.dirname(os.path.abspath(file_path))
        imported = with_audio = without_audio = 0
        errors = []

        for row_num, raw_row in enumerate(rows, start=2):
            audio_path, song_data = map_row(raw_row, header_map, base_dir)
            res = songs_service.import_song(db_path, library_path, audio_path, song_data)
            if res.get("status") == "success":
                imported += 1
                if res.get("has_audio"):
                    with_audio += 1
                else:
                    without_audio += 1
            else:
                errors.append({"row": row_num, "message": res.get("message", "Unknown error")})

        return {
            "status": "success",
            "total_rows": len(rows),
            "imported": imported,
            "with_audio": with_audio,
            "without_audio": without_audio,
            "failed": len(errors),
            "errors": errors,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def write_template_csv(dest_path: str) -> dict:
    try:
        with open(dest_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(TEMPLATE_HEADERS)
            writer.writerow([
                "Neon Horizon", "Synth Collective", "Guest Vocalist", "Night Drive", "1",
                "Synthwave, Electronic", "AI Generated, Demo", "true", "A", "Minor", "118",
                "2026-01-15", "", "D:\\Projects\\Neon_Horizon", "Neon Horizon Ableton Project",
            ])
            writer.writerow([
                "Clair de Lune", "Claude Debussy", "", "Suite Bergamasque", "3",
                "Classical", "Instrumental", "false", "D#", "Minor", "66",
                "1905-01-01", "C:\\Music\\clair_de_lune.wav", "", "",
            ])
        return {"status": "success", "path": dest_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}
