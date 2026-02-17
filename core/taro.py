"""
Taro — The yogi name generator.

Taro is the yogi master who helps new yogis choose their identity.
Names are generated algorithmically from curated word pools — no LLM needed.
Fast, deterministic, no hallucination risk.

Flow:
    1. Generate 5 candidate names
    2. Filter out taken names (case-insensitive)
    3. Present to yogi: pick one or type your own
    4. Validate: not real name, not reserved, unique

Usage:
    from core.taro import suggest_names, validate_yogi_name_full

    # Generate suggestions
    suggestions = suggest_names(conn, count=5)

    # Validate a chosen name (includes real-name guard)
    ok, error = validate_yogi_name_full("Storm", real_name="Max Müller", conn=conn)
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

# Names that are explicitly blocked (system names, offensive, etc.)
_BLOCKED_NAMES = {
    'admin', 'mira', 'doug', 'adele', 'taro', 'nate', 'clara',
    'system', 'bot', 'test', 'null', 'undefined', 'root',
    'talent', 'yoga', 'talentyoga', 'talent.yoga',
    'anonymous', 'anon', 'nobody', 'user', 'guest',
    'moderator', 'mod', 'staff', 'support', 'help',
}

_YOGI_NAME_PATTERN = re.compile(
    r'^[a-zA-Z0-9äöüÄÖÜß][a-zA-Z0-9äöüÄÖÜß._\- ]{0,18}[a-zA-Z0-9äöüÄÖÜß]$'
)


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


def suggest_names(conn=None, count: int = 5) -> List[str]:
    """
    Generate `count` unique yogi name suggestions.

    Mix: ~60% single words, ~40% compounds.
    Filters out taken names if conn is provided.

    Returns:
        List of suggested names (may be fewer than count if pool is exhausted)
    """
    taken = _get_taken_names(conn) if conn else set()
    taken.update(n.lower() for n in _BLOCKED_NAMES)

    candidates = []
    attempts = 0
    max_attempts = count * 10  # avoid infinite loop

    while len(candidates) < count and attempts < max_attempts:
        attempts += 1
        if random.random() < 0.6:
            name = _generate_single()
        else:
            name = _generate_compound()

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


def validate_yogi_name_full(
    name: str,
    real_name: str = None,
    email: str = None,
    conn=None
) -> Tuple[bool, Optional[str]]:
    """
    Full validation of a yogi name.

    Checks:
    1. Format (length, characters)
    2. Not a reserved/blocked name
    3. Not the yogi's real name or part of it
    4. Unique (case-insensitive)

    Args:
        name: Proposed yogi name
        real_name: display_name from Google OAuth (if known)
        email: email from Google OAuth (if known)
        conn: DB connection for uniqueness check

    Returns:
        (is_valid, error_message) — error_message is None if valid
    """
    if not name or not name.strip():
        return False, "Name cannot be empty"

    name = name.strip()

    # 1. Format check
    if len(name) < 2:
        return False, "Name must be at least 2 characters"
    if len(name) > 20:
        return False, "Name must be 20 characters or fewer"
    if not _YOGI_NAME_PATTERN.match(name):
        return False, "Name can only contain letters, numbers, dots, hyphens, and spaces"

    # 2. Blocked names
    if name.lower() in _BLOCKED_NAMES:
        return False, "That name is reserved"

    # 3. Real-name guard
    if real_name or email:
        real_parts = _extract_name_parts(real_name, email)
        name_lower = name.lower()

        # Exact match with full name
        if name_lower in real_parts:
            return False, (
                "That looks like your real name. "
                "Your yogi name protects your identity — please pick something different."
            )

        # Starts with a real-name part (≥4 chars to avoid false positives)
        for part in real_parts:
            if len(part) >= 4 and name_lower.startswith(part):
                return False, (
                    "That looks like part of your real name. "
                    "Your yogi name protects your identity — please pick something different."
                )

    # 4. Uniqueness check
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM users WHERE LOWER(yogi_name) = LOWER(%s) LIMIT 1",
                    (name,)
                )
                if cur.fetchone():
                    return False, "That name is already taken"
        except Exception as e:
            logger.warning(f"Uniqueness check failed: {e}")
            # Don't block on DB error — let it through, the unique index will catch it

    return True, None
