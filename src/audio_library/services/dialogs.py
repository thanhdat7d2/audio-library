"""Native pywebview file and folder dialog wrappers."""

import webview


def select_folder():
    active_window = webview.active_window()
    if not active_window:
        return None
    result = active_window.create_file_dialog(webview.FOLDER_DIALOG)
    return result[0] if result else None


def select_import_file():
    active_window = webview.active_window()
    if not active_window:
        return None
    file_types = (
        "All files (*.*)",
        "Audio files (*.mp3;*.wav;*.flac;*.ogg)",
        "Images (*.jpg;*.jpeg;*.png;*.webp)",
    )
    result = active_window.create_file_dialog(webview.OPEN_DIALOG, file_types=file_types)
    return result[0] if result else None


def select_project_file():
    active_window = webview.active_window()
    if not active_window:
        return None
    file_types = (
        "All files (*.*)",
        "DAW Projects (*.flp;*.als;*.rpp;*.cpr;*.ptx;*.logicx;*.mmpz;*.mmp;*.song;*.reason)",
    )
    result = active_window.create_file_dialog(webview.OPEN_DIALOG, file_types=file_types)
    return result[0] if result else None


def select_spreadsheet_file():
    active_window = webview.active_window()
    if not active_window:
        return None
    file_types = (
        "Spreadsheets (*.csv;*.tsv;*.xlsx)",
        "All files (*.*)",
    )
    result = active_window.create_file_dialog(webview.OPEN_DIALOG, file_types=file_types)
    return result[0] if result else None


def save_csv_file(default_filename: str = "songs_import_template.csv"):
    active_window = webview.active_window()
    if not active_window:
        return None
    result = active_window.create_file_dialog(
        webview.SAVE_DIALOG,
        save_filename=default_filename,
        file_types=("CSV files (*.csv)",),
    )
    if not result:
        return None
    return result[0] if isinstance(result, (list, tuple)) else result
