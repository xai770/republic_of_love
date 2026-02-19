"""
Taro — The yogi name generator & guardian.

Taro is the yogi master who helps new yogis choose their identity.
Names are generated algorithmically from curated word pools — no LLM needed.
Fast, deterministic, no hallucination risk.

Validation layers (A+B+C+D):
    A) UX nudge — clear labels (handled in frontend i18n)
    B) Pattern detection — common names, titles, particles, "looks real" heuristic
    C) Pseudonym generator — one-click suggestions from curated pools
    D) Hard-block — email, phone, address patterns

Privacy: We NEVER store real names. Google OAuth display_name is read
transiently for validation only, then discarded. EU-compliant.

Flow:
    1. Generate 5+ candidate names
    2. Filter out taken names (case-insensitive)
    3. Present to yogi: pick one or type your own
    4. Validate: format → hard-block → reserved → common-name → real-name → unique
    5. Return (ok, warning_or_error, severity)

Usage:
    from core.taro import suggest_names, validate_yogi_name

    # Generate suggestions
    suggestions = suggest_names(conn, count=6)

    # Validate a chosen name
    ok, msg, severity = validate_yogi_name("Storm", real_name="Max Müller", conn=conn)
    # severity: None (ok), "error" (blocked), "warning" (soft, let user confirm)
"""
import random
import re
from typing import List, Optional, Tuple

from core.logging_config import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────
# Word pools — curated for pleasant sound, gender-neutral,
# culturally safe, and easy to type/remember
# ─────────────────────────────────────────────────────────

_NATURE = [
    'Oak', 'Cedar', 'Ember', 'Sage', 'Fern', 'Ivy', 'Moss',
    'Birch', 'Linden', 'Maple', 'Alder', 'Hazel', 'Thorn',
    'Heath', 'Glen', 'Dale', 'Wren', 'Lark', 'Raven', 'Heron',
    'Falcon', 'Finch', 'Robin', 'Crane', 'Bloom', 'Petal',
    'Briar', 'Clover', 'Laurel', 'Willow', 'Aspen',
]

_SKY = [
    'Nova', 'Luna', 'Sol', 'Astra', 'Orion', 'Zenith',
    'Aurora', 'Vega', 'Lyra', 'Stella', 'Comet', 'Nimbus',
    'Cirrus', 'Dusk', 'Dawn', 'Twilight', 'Halo', 'Solstice',
    'Equinox', 'Eclipse', 'Polaris', 'Sirius', 'Andromeda',
]

_WATER = [
    'River', 'Brook', 'Wave', 'Tide', 'Coral', 'Marina',
    'Reed', 'Cove', 'Bay', 'Fjord', 'Reef', 'Shore',
    'Delta', 'Cascade', 'Mist', 'Dew', 'Rain', 'Storm',
    'Drift', 'Current', 'Ripple', 'Harbor', 'Lagoon',
]

_EARTH = [
    'Flint', 'Onyx', 'Jade', 'Amber', 'Quartz', 'Ridge',
    'Summit', 'Peak', 'Mesa', 'Canyon', 'Cliff', 'Stone',
    'Basalt', 'Slate', 'Cobalt', 'Iron', 'Copper', 'Silver',
    'Opal', 'Garnet', 'Topaz', 'Jasper', 'Obsidian',
]

_SPIRIT = [
    'Phoenix', 'Echo', 'Zen', 'Atlas', 'Pixel', 'Nova',
    'Spark', 'Arrow', 'Quest', 'Rune', 'Myth', 'Valor',
    'Crest', 'Shield', 'Beacon', 'Compass', 'Anchor', 'Helm',
    'Vigil', 'Sage', 'Oracle', 'Wanderer', 'Pioneer', 'Nomad',
]

# All single-word pools combined (for simple names)
_ALL_SINGLES = _NATURE + _SKY + _WATER + _EARTH + _SPIRIT

# ─────────────────────────────────────────────────────────
# German (DE) word pools — same categories, native words
# ─────────────────────────────────────────────────────────

_DE_NATURE = [
    'Eiche', 'Birke', 'Linde', 'Ahorn', 'Erle', 'Farn', 'Efeu',
    'Moos', 'Hasel', 'Dorn', 'Heide', 'Klee', 'Lorbeer', 'Weide',
    'Espe', 'Salbei', 'Distel', 'Ginster', 'Holunder', 'Mistel',
    'Falke', 'Fink', 'Lerche', 'Rabe', 'Reiher', 'Kranich',
    'Drossel', 'Adler', 'Meise', 'Amsel', 'Schwalbe',
]

_DE_SKY = [
    'Nova', 'Luna', 'Stern', 'Komet', 'Zenit', 'Aurora',
    'Lyra', 'Vega', 'Stella', 'Nimbus', 'Nebel', 'Morgenrot',
    'Abendstern', 'Halo', 'Polaris', 'Sirius', 'Orion',
    'Sonne', 'Mond', 'Finsternis', 'Lichtung', 'Dämmerung',
]

_DE_WATER = [
    'Bach', 'Welle', 'Flut', 'Koralle', 'Schilf', 'Bucht',
    'Riff', 'Küste', 'Fjord', 'Tau', 'Regen', 'Sturm',
    'Brandung', 'Strömung', 'Nebel', 'Hafen', 'Lagune',
    'Quelle', 'Strom', 'Ufer', 'Gischt', 'Fluss', 'See',
]

_DE_EARTH = [
    'Feuerstein', 'Onyx', 'Jade', 'Bernstein', 'Quarz', 'Gipfel',
    'Klippe', 'Stein', 'Basalt', 'Schiefer', 'Kobalt', 'Eisen',
    'Kupfer', 'Silber', 'Opal', 'Granat', 'Topas', 'Jaspis',
    'Obsidian', 'Granit', 'Fels', 'Kiesel', 'Kristall',
]

_DE_SPIRIT = [
    'Phönix', 'Echo', 'Rune', 'Mythos', 'Mut', 'Wappen',
    'Anker', 'Kompass', 'Leuchtturm', 'Wanderer', 'Pionier',
    'Nomade', 'Funke', 'Pfeil', 'Wache', 'Bote', 'Fährte',
    'Lohe', 'Glanz', 'Klang', 'Hort', 'Zuflucht', 'Ruhe',
]

_DE_ALL_SINGLES = _DE_NATURE + _DE_SKY + _DE_WATER + _DE_EARTH + _DE_SPIRIT

# ─────────────────────────────────────────────────────────
# Gendered pools — for onboarding wizard where yogi picks
# masculine, feminine, or neutral style
# ─────────────────────────────────────────────────────────

_FEMININE_SINGLES = [
    'Aurora', 'Luna', 'Stella', 'Lyra', 'Vega', 'Iris', 'Aria',
    'Seraphina', 'Celeste', 'Dahlia', 'Freya', 'Ivy', 'Jasmine',
    'Lavender', 'Marigold', 'Orchid', 'Pearl', 'Rosemary', 'Saffron',
    'Violet', 'Willow', 'Zinnia', 'Coral', 'Marina', 'Opal', 'Amber',
    'Hazel', 'Laurel', 'Bloom', 'Petal', 'Clover', 'Fern', 'Briar',
    'Misty', 'Solara', 'Astra', 'Neve', 'Ember', 'Holly', 'Sage',
]

_MASCULINE_SINGLES = [
    'Atlas', 'Orion', 'Flint', 'Iron', 'Storm', 'Ridge', 'Summit',
    'Falcon', 'Hawk', 'Raven', 'Slate', 'Basalt', 'Cobalt', 'Onyx',
    'Jasper', 'Oak', 'Cedar', 'Thorn', 'Valor', 'Shield', 'Helm',
    'Arrow', 'Beacon', 'Compass', 'Anchor', 'Pioneer', 'Nomad',
    'Cliff', 'Canyon', 'Peak', 'Glen', 'Dale', 'Heath', 'Crest',
    'Forge', 'Granite', 'Blaze', 'Quartz', 'Fjord', 'Sirius', 'Zenith',
]

_FEMININE_PREFIXES = [
    'Silver', 'Rose', 'Moon', 'Star', 'Snow', 'Dawn', 'Bright',
    'Crystal', 'Golden', 'Misty', 'Silk', 'Velvet',
]

_FEMININE_SUFFIXES = [
    'Song', 'Bloom', 'Light', 'Leaf', 'Haven', 'Dream', 'Grace',
    'Wing', 'Rain', 'Star', 'Fern', 'Dew',
]

_MASCULINE_PREFIXES = [
    'Iron', 'Storm', 'Fire', 'Night', 'Dark', 'Steel', 'Thunder',
    'Bold', 'Wild', 'Stone', 'Swift', 'Deep',
]

_MASCULINE_SUFFIXES = [
    'Wolf', 'Bear', 'Hawk', 'Fox', 'Stone', 'Ridge', 'Fire',
    'Gate', 'Run', 'Forge', 'Watch', 'Guard',
]

# Prefixes and suffixes for compound names
_PREFIXES = [
    'Blue', 'Red', 'Gold', 'Silver', 'Iron', 'Quiet',
    'Swift', 'Bright', 'Wild', 'True', 'Clear', 'Deep',
    'Star', 'Sun', 'Moon', 'Sky', 'Sea', 'Storm',
    'Night', 'Light', 'Snow', 'Fire', 'Wind', 'Cloud',
]

_SUFFIXES = [
    'Fox', 'Wolf', 'Bear', 'Hawk', 'Deer', 'Owl',
    'Wave', 'Fire', 'Wind', 'Stone', 'Light', 'Star',
    'Wood', 'Field', 'Ridge', 'Lake', 'Run', 'Trail',
    'Song', 'Leaf', 'Frost', 'Gate', 'Path', 'Haven',
]

# ─────────────────────────────────────────────────────────
# German gendered & compound pools
# ─────────────────────────────────────────────────────────

_DE_FEMININE_SINGLES = [
    'Aurora', 'Luna', 'Stella', 'Lyra', 'Vega', 'Iris', 'Freya',
    'Dahlie', 'Efeu', 'Jasmin', 'Lavendel', 'Orchidee', 'Perle',
    'Rosmarin', 'Safran', 'Veilchen', 'Weide', 'Zinnie', 'Koralle',
    'Marina', 'Opal', 'Bernstein', 'Hasel', 'Lorbeer', 'Blüte',
    'Farn', 'Nelke', 'Lilie', 'Rose', 'Amsel', 'Schwalbe',
    'Lerche', 'Meise', 'Taube', 'Heide', 'Distel', 'Mistel',
    'Quelle', 'Lichtung', 'Morgenröte',
]

_DE_MASCULINE_SINGLES = [
    'Falke', 'Adler', 'Sturm', 'Fels', 'Stahl', 'Donner',
    'Blitz', 'Eisen', 'Granit', 'Basalt', 'Wolf', 'Bär',
    'Hirsch', 'Rabe', 'Eber', 'Orion', 'Sirius', 'Zenit',
    'Eiche', 'Dorn', 'Kiesel', 'Obsidian', 'Kobalt', 'Onyx',
    'Gipfel', 'Klippe', 'Anker', 'Wappen', 'Kompass', 'Pfeil',
    'Fjord', 'Feuerstein', 'Jaspis', 'Schiefer', 'Quarz',
    'Forst', 'Flint', 'Lohe', 'Wache', 'Pionier',
]

_DE_FEMININE_PREFIXES = [
    'Silber', 'Rosen', 'Mond', 'Stern', 'Schnee', 'Morgen',
    'Kristall', 'Gold', 'Samt', 'Seiden', 'Licht', 'Perlen',
]

_DE_FEMININE_SUFFIXES = [
    'lied', 'blüte', 'licht', 'blatt', 'traum', 'glanz',
    'tau', 'stern', 'farn', 'herz', 'hauch', 'flügel',
]

_DE_MASCULINE_PREFIXES = [
    'Eisen', 'Sturm', 'Feuer', 'Nacht', 'Stahl', 'Donner',
    'Wild', 'Stein', 'Wald', 'Frost', 'Fels', 'Grau',
]

_DE_MASCULINE_SUFFIXES = [
    'wolf', 'bär', 'falke', 'fuchs', 'stein', 'berg',
    'feuer', 'tor', 'lauf', 'wacht', 'schild', 'hort',
]

_DE_PREFIXES = [
    'Blau', 'Rot', 'Gold', 'Silber', 'Eisen', 'Still',
    'Schnell', 'Hell', 'Wild', 'Treu', 'Klar', 'Tief',
    'Stern', 'Mond', 'See', 'Sturm', 'Nacht', 'Licht',
    'Schnee', 'Feuer', 'Wind', 'Wolken', 'Wald', 'Berg',
]

_DE_SUFFIXES = [
    'fuchs', 'wolf', 'bär', 'falke', 'hirsch', 'eule',
    'welle', 'feuer', 'wind', 'stein', 'licht', 'stern',
    'wald', 'feld', 'berg', 'see', 'lauf', 'pfad',
    'lied', 'blatt', 'frost', 'tor', 'hafen', 'herz',
]

# Names that are explicitly blocked (system names, offensive, etc.)
_BLOCKED_NAMES = {
    'admin', 'mira', 'doug', 'adele', 'taro', 'nate', 'clara',
    'system', 'bot', 'test', 'null', 'undefined', 'root',
    'talent', 'yoga', 'talentyoga', 'talent.yoga',
    'anonymous', 'anon', 'nobody', 'user', 'guest',
    'moderator', 'mod', 'staff', 'support', 'help',
}

_YOGI_NAME_PATTERN = re.compile(
    r'^[a-zA-Z0-9äöüÄÖÜß][a-zA-Z0-9äöüÄÖÜß._\- ]{0,28}[a-zA-Z0-9äöüÄÖÜß]$'
)

# ─────────────────────────────────────────────────────────
# B) Generic real-name detection — no PII stored
# ─────────────────────────────────────────────────────────

# Common first names (DE top-50 + EN top-50, lowercased)
_COMMON_FIRST_NAMES = {
    # German male
    'peter', 'thomas', 'michael', 'andreas', 'stefan', 'markus', 'christian',
    'martin', 'jürgen', 'klaus', 'wolfgang', 'hans', 'werner', 'karl',
    'heinrich', 'matthias', 'frank', 'bernhard', 'rolf', 'dieter',
    'helmut', 'gerhard', 'manfred', 'günter', 'uwe', 'rainer', 'bernd',
    'jens', 'alexander', 'tobias', 'florian', 'sebastian', 'daniel',
    'philipp', 'jan', 'lukas', 'jonas', 'felix', 'leon', 'maximilian',
    'moritz', 'fritz', 'friedrich', 'otto', 'max', 'paul', 'emil',
    # German female
    'maria', 'anna', 'elisabeth', 'margarete', 'monika', 'ursula', 'renate',
    'christine', 'helga', 'sabine', 'petra', 'brigitte', 'andrea', 'claudia',
    'susanne', 'birgit', 'heike', 'karin', 'gabriele', 'eva', 'ingrid',
    'gertrud', 'anja', 'nicole', 'julia', 'katharina', 'sarah', 'laura',
    'lisa', 'sophie', 'emma', 'hannah', 'mia', 'lena', 'marie', 'johanna',
    # English common
    'james', 'john', 'robert', 'david', 'william', 'richard', 'joseph',
    'charles', 'christopher', 'matthew', 'anthony', 'mark', 'donald',
    'steven', 'andrew', 'joshua', 'kevin', 'brian', 'george', 'edward',
    'mary', 'patricia', 'jennifer', 'linda', 'barbara', 'susan', 'jessica',
    'sarah', 'karen', 'nancy', 'betty', 'margaret', 'sandra', 'ashley',
    'dorothy', 'kimberly', 'emily', 'donna', 'michelle', 'carol', 'amanda',
    'melissa', 'deborah', 'stephanie', 'rebecca', 'sharon', 'cynthia',
    'kathleen', 'amy', 'angela', 'rachel', 'samantha', 'catherine', 'virginia',
    # Turkish (common in DE)
    'mehmet', 'mustafa', 'ahmet', 'ali', 'hasan', 'fatma', 'ayse', 'emine',
    'hatice', 'zeynep', 'elif', 'yusuf', 'ibrahim', 'kemal', 'murat',
}

# Title prefixes that indicate a real name follows
_TITLE_PREFIXES = {'dr', 'prof', 'herr', 'frau', 'dipl', 'ing', 'mag'}

# Name particles (nobiliary/family)
_NAME_PARTICLES = {'von', 'van', 'de', 'di', 'del', 'der', 'den', 'la', 'le',
                   'al', 'el', 'bin', 'ibn', 'ben', 'zu', 'auf', 'vom'}

# D) Hard-block patterns — email, phone, address
_EMAIL_PATTERN = re.compile(r'[@]|[a-z0-9_.+-]+@[a-z0-9-]+\.[a-z]{2,}', re.I)
_PHONE_PATTERN = re.compile(
    r'(?:\+?\d{1,3}[\s\-]?)?\(?\d{2,5}\)?[\s\-]?\d{3,10}[\s\-]?\d{0,8}'
)
_ADDRESS_PATTERN = re.compile(
    r'(?:str\.|straße|strasse|weg|platz|allee|gasse|ring|damm|ufer)\s*\d',
    re.I
)
# German postal code + city pattern
_PLZ_PATTERN = re.compile(r'\b\d{5}\s+[A-ZÄÖÜ]', re.U)


# ─────────────────────────────────────────────────────────
# Name generation
# ─────────────────────────────────────────────────────────

def _generate_single() -> str:
    """Pick a single word from the pools."""
    return random.choice(_ALL_SINGLES)


def _generate_compound() -> str:
    """Combine a prefix + suffix into a compound name."""
    return random.choice(_PREFIXES) + random.choice(_SUFFIXES)


def _deduplicate(names: list) -> list:
    """Remove duplicates while preserving order."""
    seen = set()
    result = []
    for name in names:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            result.append(name)
    return result


def _get_taken_names(conn) -> set:
    """Load all taken yogi names (lowercase) from the database."""
    taken = set()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT LOWER(yogi_name) FROM users WHERE yogi_name IS NOT NULL")
            for row in cur:
                val = row[0] if isinstance(row, (list, tuple)) else list(row.values())[0]
                if val:
                    taken.add(val)
    except Exception as e:
        logger.warning(f"Failed to load taken names: {e}")
    return taken


def suggest_names(conn=None, count: int = 5, gender: str = 'neutral',
                  language: str = 'en') -> List[str]:
    """
    Generate `count` unique yogi name suggestions.

    Mix: ~60% single words, ~40% compounds.
    Filters out taken names if conn is provided.

    Args:
        conn: DB connection for uniqueness filtering
        count: Number of suggestions to generate
        gender: 'masculine', 'feminine', or 'neutral' — picks from styled pools
        language: 'de' for German pools, anything else for English

    Returns:
        List of suggested names (may be fewer than count if pool is exhausted)
    """
    taken = _get_taken_names(conn) if conn else set()
    taken.update(n.lower() for n in _BLOCKED_NAMES)

    de = language == 'de'

    # Select pools based on gender preference + language
    if gender == 'feminine':
        singles = _DE_FEMININE_SINGLES if de else _FEMININE_SINGLES
        prefixes = _DE_FEMININE_PREFIXES if de else _FEMININE_PREFIXES
        suffixes = _DE_FEMININE_SUFFIXES if de else _FEMININE_SUFFIXES
    elif gender == 'masculine':
        singles = _DE_MASCULINE_SINGLES if de else _MASCULINE_SINGLES
        prefixes = _DE_MASCULINE_PREFIXES if de else _MASCULINE_PREFIXES
        suffixes = _DE_MASCULINE_SUFFIXES if de else _MASCULINE_SUFFIXES
    else:
        singles = _DE_ALL_SINGLES if de else _ALL_SINGLES
        prefixes = _DE_PREFIXES if de else _PREFIXES
        suffixes = _DE_SUFFIXES if de else _SUFFIXES

    candidates = []
    attempts = 0
    max_attempts = count * 10  # avoid infinite loop

    while len(candidates) < count and attempts < max_attempts:
        attempts += 1
        if random.random() < 0.6:
            name = random.choice(singles)
        else:
            name = random.choice(prefixes) + random.choice(suffixes)

        if name.lower() not in taken:
            candidates.append(name)
            taken.add(name.lower())  # prevent duplicates within batch

    return _deduplicate(candidates)


# ─────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────

def _extract_name_parts(display_name: str = None, email: str = None) -> set:
    """
    Extract recognizable name parts from Google OAuth data.
    These are used transiently — NEVER stored.

    "Gershon Pollatschek" → {"gershon", "pollatschek"}
    "gershon.pollatschek@gmail.com" → {"gershon", "pollatschek"}
    """
    parts = set()

    if display_name:
        for part in display_name.split():
            cleaned = part.strip().lower()
            if len(cleaned) >= 2:
                parts.add(cleaned)
        # Also the full name as one unit
        full = display_name.strip().lower()
        if full:
            parts.add(full)

    if email:
        # Take the local part before @
        local = email.split('@')[0].lower()
        # Split on dots, hyphens, underscores
        for part in re.split(r'[.\-_]', local):
            if len(part) >= 2:
                parts.add(part)

    return parts


def _check_hard_block(name: str) -> Optional[str]:
    """
    D) Hard-block: email, phone, address patterns.
    Returns error message or None.
    """
    if _EMAIL_PATTERN.search(name):
        return "contains_email"
    if _ADDRESS_PATTERN.search(name):
        return "contains_address"
    if _PLZ_PATTERN.search(name):
        return "contains_address"
    # Phone: only trigger if mostly digits (avoid false positives like "Agent007")
    digits = sum(1 for c in name if c.isdigit())
    if digits >= 5 and _PHONE_PATTERN.search(name):
        return "contains_phone"
    return None


def _check_looks_like_real_name(name: str) -> Optional[str]:
    """
    B) Generic real-name heuristics — no PII needed.
    Returns warning key or None.
    """
    words = name.split()

    # Two+ capitalized words → "Max Mustermann" pattern
    if len(words) >= 2:
        capitalized = sum(1 for w in words if w[0].isupper() and w[1:].islower()
                         and len(w) >= 2 and w.lower() not in _NAME_PARTICLES)
        if capitalized >= 2:
            # Extra check: are any of them common first names?
            for w in words:
                if w.lower() in _COMMON_FIRST_NAMES:
                    return "looks_like_full_name"
            # Even without common-name hit, two capitalized words is suspicious
            return "looks_like_full_name"

    # Contains title prefix: "Dr Müller", "Prof Schmidt"
    first_word = words[0].rstrip('.').lower() if words else ''
    if first_word in _TITLE_PREFIXES and len(words) >= 2:
        return "contains_title"

    # Contains name particle in multi-word: "von Weizsäcker"
    if len(words) >= 2:
        for w in words:
            if w.lower() in _NAME_PARTICLES:
                return "contains_particle"

    # Single word that's a very common first name
    if len(words) == 1 and words[0].lower() in _COMMON_FIRST_NAMES:
        return "common_first_name"

    return None


def validate_yogi_name(
    name: str,
    real_name: str = None,
    email: str = None,
    conn=None,
    current_user_id: int = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Full layered validation of a yogi name (A+B+C+D).

    Privacy: real_name and email are used transiently for comparison
    only — they are NEVER stored, logged, or returned.

    Checks (in order):
    1. Format (length, characters)
    2. D) Hard-block (email, phone, address) → error
    3. Reserved/blocked names → error
    4. B) Generic "looks like a real name" → warning
    5. Real-name guard (OAuth comparison) → error
    6. Uniqueness → error

    Args:
        name: Proposed yogi name
        real_name: display_name from Google OAuth (transient, never stored)
        email: email from Google OAuth (transient, never stored)
        conn: DB connection for uniqueness check
        current_user_id: Exclude this user from uniqueness check (for updates)

    Returns:
        (is_valid, message, severity)
        severity: None (valid), "error" (hard block), "warning" (soft, user can confirm)
    """
    if not name or not name.strip():
        return False, "Name cannot be empty", "error"

    name = name.strip()

    # 1. Format check
    if len(name) < 2:
        return False, "Name must be at least 2 characters", "error"
    if len(name) > 30:
        return False, "Name must be 30 characters or fewer", "error"
    if not _YOGI_NAME_PATTERN.match(name):
        return False, "Name can only contain letters, numbers, dots, hyphens, and spaces", "error"

    # 2. D) Hard-block — email, phone, address
    hard_block = _check_hard_block(name)
    if hard_block:
        return False, hard_block, "error"

    # 3. Blocked/reserved names
    if name.lower() in _BLOCKED_NAMES:
        return False, "reserved", "error"

    # 4. B) Generic "looks like a real name" heuristic
    looks_real = _check_looks_like_real_name(name)
    if looks_real:
        # This is a WARNING, not a hard block — user can override
        return True, looks_real, "warning"

    # 5. Real-name guard (Google OAuth comparison — transient only)
    if real_name or email:
        real_parts = _extract_name_parts(real_name, email)
        name_lower = name.lower()
        name_normalized = re.sub(r"[^a-z0-9äöüß]", "", name_lower)

        for rp in real_parts:
            rp_normalized = re.sub(r"[^a-z0-9äöüß]", "", rp)
            if not rp_normalized or len(rp_normalized) < 3:
                continue
            # Exact match with a real-name fragment
            if name_normalized == rp_normalized:
                return False, "matches_real_name", "error"
            # Real name contained in yogi name (require 4+ chars to avoid short-handle false positives)
            if len(rp_normalized) >= 4 and rp_normalized in name_normalized:
                return False, "contains_real_name", "error"
            # Yogi name contained in real name (short candidate inside long name)
            if len(name_normalized) >= 4 and name_normalized in rp_normalized:
                return False, "subset_of_real_name", "error"

    # 6. Uniqueness check
    if conn:
        try:
            with conn.cursor() as cur:
                if current_user_id:
                    cur.execute(
                        "SELECT 1 FROM users WHERE LOWER(yogi_name) = LOWER(%s) AND user_id != %s LIMIT 1",
                        (name, current_user_id)
                    )
                else:
                    cur.execute(
                        "SELECT 1 FROM users WHERE LOWER(yogi_name) = LOWER(%s) LIMIT 1",
                        (name,)
                    )
                if cur.fetchone():
                    return False, "already_taken", "error"
        except Exception as e:
            logger.warning(f"Uniqueness check failed: {e}")

    return True, None, None


# Backward compat wrapper
def validate_yogi_name_full(
    name: str,
    real_name: str = None,
    email: str = None,
    conn=None
) -> Tuple[bool, Optional[str]]:
    """Legacy wrapper — returns (ok, error_message)."""
    ok, msg, severity = validate_yogi_name(name, real_name, email, conn)
    if severity == "error":
        return False, msg
    return True, None
