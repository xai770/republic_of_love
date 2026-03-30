"""
core/mira_contexts.py — Per-screen Mira context configuration.

Defines quick-action pills, greetings, and illustration per page/tab.
Served to the frontend as JSON via /api/mira/context endpoint.
"""

# Each context has:
#   greeting_en, greeting_de_du, greeting_de_sie — screen-specific greeting
#   illustration — filename in /static/images/Mira/
#   quick_actions — list of { label_en, label_de, message }

MIRA_CONTEXTS = {
    # ── Search tabs ─────────────────────────────────────────────
    "/search:situation": {
        "greeting_en": "Let's figure out your situation first.",
        "greeting_de_du": "Lass uns erstmal deine Situation klären.",
        "greeting_de_sie": "Lassen Sie uns zuerst Ihre Situation klären.",
        "illustration": "mira_pointing_center.png",
        "quick_actions": [
            {"label_en": "What do the cards mean?", "label_de": "Was bedeuten die Karten?", "message": "explain_cards"},
            {"label_en": "Can I skip this?", "label_de": "Kann ich das überspringen?", "message": "skip_situation"},
        ],
    },
    "/search:direction": {
        "greeting_en": "Sort fields by how interesting they are to you.",
        "greeting_de_du": "Sortiere die Berufsfelder nach deinem Interesse.",
        "greeting_de_sie": "Sortieren Sie die Berufsfelder nach Ihrem Interesse.",
        "illustration": "mira_sorting_cards.png",
        "quick_actions": [
            {"label_en": "How does the Kanban work?", "label_de": "Wie funktioniert das Kanban?", "message": "explain_kanban"},
            {"label_en": "What if I'm not sure?", "label_de": "Was, wenn ich unsicher bin?", "message": "unsure_field"},
        ],
    },
    "/search:level": {
        "greeting_en": "Pick the levels that match your experience.",
        "greeting_de_du": "Wähl die Stufen, die zu deiner Erfahrung passen.",
        "greeting_de_sie": "Wählen Sie die Stufen, die zu Ihrer Erfahrung passen.",
        "illustration": "mira_star_badge.png",
        "quick_actions": [
            {"label_en": "What do the levels mean?", "label_de": "Was bedeuten die Stufen?", "message": "explain_levels"},
            {"label_en": "Skip — show everything", "label_de": "Überspringen — alles zeigen", "message": "skip_qualification"},
        ],
    },
    "/search:location": {
        "greeting_en": "Pick where you want to work.",
        "greeting_de_du": "Wähl aus, wo du arbeiten möchtest.",
        "greeting_de_sie": "Wählen Sie aus, wo Sie arbeiten möchten.",
        "illustration": "mira_map.png",
        "quick_actions": [
            {"label_en": "How does the map work?", "label_de": "Wie funktioniert die Karte?", "message": "explain_map"},
            {"label_en": "Can I search all of Germany?", "label_de": "Kann ich ganz Deutschland durchsuchen?", "message": "search_all_germany"},
        ],
    },
    "/search:opportunities": {
        "greeting_en": "Here are the postings that match your search.",
        "greeting_de_du": "Hier sind die Stellen, die zu deiner Suche passen.",
        "greeting_de_sie": "Hier sind die Stellen, die zu Ihrer Suche passen.",
        "illustration": "mira_postings.png",
        "quick_actions": [
            {"label_en": "How is the match score calculated?", "label_de": "Wie wird der Match-Score berechnet?", "message": "explain_match_score"},
            {"label_en": "What do the status labels mean?", "label_de": "Was bedeuten die Status-Labels?", "message": "explain_posting_status"},
        ],
    },
    "/search:power": {
        "greeting_en": "This is Power Search — all controls on one screen.",
        "greeting_de_du": "Das ist die Power-Suche — alle Filter auf einem Bildschirm.",
        "greeting_de_sie": "Das ist die Power-Suche — alle Filter auf einem Bildschirm.",
        "illustration": "mira_pointing_left.png",
        "quick_actions": [
            {"label_en": "How is this different from step-by-step?", "label_de": "Was ist anders als Schritt für Schritt?", "message": "explain_power_search"},
        ],
    },

    # ── Non-search pages ────────────────────────────────────────
    "/overview": {
        "greeting_en": "Welcome to your overview — here's where you are in your job search.",
        "greeting_de_du": "Willkommen in deiner Übersicht — hier siehst du, wo du in deiner Jobsuche stehst.",
        "greeting_de_sie": "Willkommen in Ihrer Übersicht — hier sehen Sie, wo Sie in Ihrer Jobsuche stehen.",
        "illustration": "mira_checklist_flow.png",
        "quick_actions": [
            {"label_en": "What's the journey flowchart?", "label_de": "Was zeigt die Reise-Übersicht?", "message": "explain_journey"},
            {"label_en": "How do I download my log?", "label_de": "Wie lade ich mein Protokoll herunter?", "message": "explain_log_download"},
        ],
    },
    "/profile": {
        "greeting_en": "Ready to build your profile?",
        "greeting_de_du": "Bereit, dein Profil aufzubauen?",
        "greeting_de_sie": "Bereit, Ihr Profil aufzubauen?",
        "illustration": "mira_clipboard.png",
        "quick_actions": [
            {"label_en": "What's the fastest way?", "label_de": "Was ist der schnellste Weg?", "message": "fastest_profile"},
            {"label_en": "Why does this matter?", "label_de": "Warum ist das wichtig?", "message": "why_profile"},
        ],
    },
    "/messages": {
        "greeting_en": "This is your inbox.",
        "greeting_de_du": "Das ist dein Postfach.",
        "greeting_de_sie": "Das ist Ihr Postfach.",
        "illustration": "mira_speech_bubbles.png",
        "quick_actions": [
            {"label_en": "Who can message me?", "label_de": "Wer kann mir schreiben?", "message": "explain_messages"},
            {"label_en": "What are Clara and Doug?", "label_de": "Wer sind Clara und Doug?", "message": "explain_actors"},
        ],
    },
    "/matches": {
        "greeting_en": "Your matches — postings that fit your profile.",
        "greeting_de_du": "Deine Matches — Stellen, die zu deinem Profil passen.",
        "greeting_de_sie": "Ihre Matches — Stellen, die zu Ihrem Profil passen.",
        "illustration": "mira_crystal_ball.png",
        "quick_actions": [
            {"label_en": "How does matching work?", "label_de": "Wie funktioniert das Matching?", "message": "explain_matching"},
            {"label_en": "What does Doug research?", "label_de": "Was recherchiert Doug?", "message": "explain_doug"},
        ],
    },
    "/account": {
        "greeting_en": "This is where you manage your account.",
        "greeting_de_du": "Hier verwaltest du dein Konto.",
        "greeting_de_sie": "Hier verwalten Sie Ihr Konto.",
        "illustration": "mira_gear.png",
        "quick_actions": [
            {"label_en": "How do credits work?", "label_de": "Wie funktionieren Credits?", "message": "explain_credits"},
            {"label_en": "How do I delete my data?", "label_de": "Wie lösche ich meine Daten?", "message": "explain_data_deletion"},
        ],
    },
}


def get_context(path: str, tab: str | None = None) -> dict | None:
    """
    Look up the MIRA_CONTEXT for a given URL path and optional tab.
    Returns the context dict or None if no match.
    """
    if tab:
        key = f"{path}:{tab}"
        if key in MIRA_CONTEXTS:
            return MIRA_CONTEXTS[key]
    if path in MIRA_CONTEXTS:
        return MIRA_CONTEXTS[path]
    return None
