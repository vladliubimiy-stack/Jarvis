"""Conservative, dependency-free parser for explicit home-control commands."""
import re

LIGHT_WORDS = {"свет", "освещение", "лампа", "лампу", "лампы", "лампе"}
SHUTTER_WORDS = {
    # Common spellings and inflections of «ролета/роллета».
    "ролет", "ролета", "ролету", "ролетом", "ролете", "ролеты", "ролетой",
    "роллет", "роллета", "роллету", "роллетом", "роллете", "роллеты", "роллетой",
    "рольставни", "рольставню", "рольставней", "рольставнями",
    "рольставка", "рольставку", "рольставкой", "рольставки", "рольставке",
    "ворота", "воротами", "воротах",
}
OPEN_WORDS = {"открой", "открыть", "открывай", "подними", "поднять"}
CLOSE_WORDS = {"закрой", "закрыть", "закрывай", "опусти", "опустить"}
STOP_WORDS = {"останови", "остановить", "стой"}
ON_WORDS = {"включи", "включить", "включай", "зажги", "зажечь"}
OFF_WORDS = {"выключи", "выключить", "выключай", "погаси", "отключи"}
ACTION_WORDS = OPEN_WORDS | CLOSE_WORDS | STOP_WORDS | ON_WORDS | OFF_WORDS


def extract_wake_command(text: str) -> str | None:
    """Return speech after a leading «Джарвис» wake word, or None without it."""
    normalized = text.lower().replace("ё", "е")
    match = re.match(r"^\s*джарвис\b[\s,!.?:;—-]*", normalized)
    if not match:
        return None
    return normalized[match.end():].strip()


def quick_command(text: str) -> str | None:
    """Return an allowed command, unknown for unsafe/ambiguous phrases,
    or None when the phrase should go to the language-model fallback.
    """
    words = re.findall(r"[а-яa-z]+", text.lower().replace("ё", "е"))
    word_set = set(words)

    if word_set & {"не", "нельзя", "отмени", "отменить"}:
        return "unknown"

    has_light = bool(word_set & LIGHT_WORDS)
    has_shutter = bool(word_set & SHUTTER_WORDS)
    actions = word_set & ACTION_WORDS

    if len(actions) > 1 or (has_light and has_shutter):
        return "unknown"

    if actions and not (has_light or has_shutter):
        return "unknown"

    if not actions:
        # The phrase may use a supported device with a less common verb or
        # word order; let the constrained intent parser inspect it.
        return None

    action = next(iter(actions))
    if has_light:
        if action in ON_WORDS:
            return "light_on"
        if action in OFF_WORDS:
            return "light_off"
        return "unknown"

    if action in OPEN_WORDS:
        return "shutter_open"
    if action in CLOSE_WORDS:
        return "shutter_close"
    if action in STOP_WORDS:
        return "shutter_stop"
    return "unknown"
