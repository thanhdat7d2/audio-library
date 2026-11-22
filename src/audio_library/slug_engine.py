import os
import re
import unicodedata

# Transliteration map for Cyrillic characters to ASCII approximations
CYRILLIC_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'j', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts',
    'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu',
    'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh',
    'З': 'Z', 'И': 'I', 'Й': 'J', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O',
    'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts',
    'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu',
    'Я': 'Ya',
}


def transliterate_cyrillic(text: str) -> str:
    """Converts Cyrillic characters to their Latin/ASCII approximations."""
    return "".join(CYRILLIC_MAP.get(char, char) for char in text)


def slugify(text: str) -> str:
    """
    Converts input text (from any language) into a filesystem-safe slug.
    Allowed characters: A-Z, a-z, 0-9, _
    """
    if not text:
        return "empty"

    # Step 1: Handle Cyrillic transliteration
    text = transliterate_cyrillic(text)

    # Step 2: Normalize unicode (decomposes accents and Vietnamese diacritics)
    text = text.replace('đ', 'd').replace('Đ', 'D')
    normalized = unicodedata.normalize('NFKD', text)

    # Step 3: Filter characters; encode non-ASCII (e.g. CJK) as hex code points
    result_chars = []
    for char in normalized:
        if unicodedata.category(char) == 'Mn':
            continue

        ascii_val = ord(char)
        if 48 <= ascii_val <= 57 or 65 <= ascii_val <= 90 or 97 <= ascii_val <= 122:
            result_chars.append(char)
        elif char.isspace() or char in ['-', '_', '.', '/']:
            result_chars.append('_')
        elif ascii_val > 127:
            result_chars.append(f"u{ascii_val:x}")

    slug = "".join(result_chars)

    # Step 4: Collapse duplicate underscores and trim edges
    slug = re.sub(r'_{2,}', '_', slug)
    slug = slug.strip('_')

    return slug or "unknown"


def generate_unique_slug(base_name: str, target_dir: str, extension: str = "") -> str:
    """
    Generates a slug, checks target_dir to avoid collisions (case-insensitive),
    and appends a numeric suffix if a duplicate exists.

    When `extension` is provided (e.g., ".mp3"), collision checks test
    `{candidate}{extension}` against existing filenames while still returning
    only the stem slug.
    """
    slug = slugify(base_name)

    if not os.path.exists(target_dir):
        return slug

    existing_items = {item.lower() for item in os.listdir(target_dir)}

    candidate = slug
    counter = 1
    while f"{candidate}{extension}".lower() in existing_items:
        candidate = f"{slug}_{counter}"
        counter += 1

    return candidate
