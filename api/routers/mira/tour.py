"""
Mira router — tour endpoint for new yogi onboarding.
"""
from fastapi import APIRouter, Depends

from api.deps import require_user
from api.routers.mira.models import TourStep, TourResponse

router = APIRouter()


@router.get("/tour", response_model=TourResponse)
async def get_tour(
    uses_du: bool = True,
    user: dict = Depends(require_user)
):
    """
    Get tour steps for new yogi onboarding.

    Tour explains:
    1. What talent.yoga does
    2. How to upload profile
    3. Where matches appear
    4. How to chat with Mira
    """
    if uses_du:
        steps = [
            TourStep(
                step_id="welcome",
                title="Willkommen bei talent.yoga! 🧘",
                message="Ich bin Mira, deine persönliche Begleiterin bei der Jobsuche. Lass mich dir kurz zeigen, wie alles funktioniert.",
                target=None
            ),
            TourStep(
                step_id="profile",
                title="Dein Profil 📋",
                message="Hier kannst du deinen Lebenslauf hochladen oder deine Skills manuell eingeben. Je mehr wir über dich wissen, desto bessere Matches finden wir.",
                target="#profile-section",
                action="click"
            ),
            TourStep(
                step_id="matches",
                title="Deine Matches 🎯",
                message="Hier erscheinen Jobs, die zu deinem Profil passen. Du musst nicht aktiv suchen – wir finden die Jobs für dich!",
                target="#matches-section"
            ),
            TourStep(
                step_id="journey",
                title="Deine Reise 🗺️",
                message="Hier siehst du, wo du bei jeder Bewerbung stehst – von 'entdeckt' bis 'eingestellt'. Wie ein Brettspiel!",
                target="#journey-board"
            ),
            TourStep(
                step_id="chat",
                title="Ich bin immer da 💬",
                message="Du findest mich immer hier unten rechts. Frag mich alles über talent.yoga, deine Matches, oder wenn du nicht weiterkommst.",
                target="#mira-chat-button"
            ),
            TourStep(
                step_id="ready",
                title="Los geht's! 🚀",
                message="Das war's schon! Möchtest du jetzt dein Profil hochladen, oder willst du dich erst mal umschauen?",
                action="choose"
            ),
        ]
    else:
        steps = [
            TourStep(
                step_id="welcome",
                title="Willkommen bei talent.yoga! 🧘",
                message="Ich bin Mira, Ihre persönliche Begleiterin bei der Jobsuche. Lassen Sie mich Ihnen kurz zeigen, wie alles funktioniert.",
                target=None
            ),
            TourStep(
                step_id="profile",
                title="Ihr Profil 📋",
                message="Hier können Sie Ihren Lebenslauf hochladen oder Ihre Skills manuell eingeben. Je mehr wir über Sie wissen, desto bessere Matches finden wir.",
                target="#profile-section",
                action="click"
            ),
            TourStep(
                step_id="matches",
                title="Ihre Matches 🎯",
                message="Hier erscheinen Jobs, die zu Ihrem Profil passen. Sie müssen nicht aktiv suchen – wir finden die Jobs für Sie!",
                target="#matches-section"
            ),
            TourStep(
                step_id="journey",
                title="Ihre Reise 🗺️",
                message="Hier sehen Sie, wo Sie bei jeder Bewerbung stehen – von 'entdeckt' bis 'eingestellt'. Wie ein Brettspiel!",
                target="#journey-board"
            ),
            TourStep(
                step_id="chat",
                title="Ich bin immer da 💬",
                message="Sie finden mich immer hier unten rechts. Fragen Sie mich alles über talent.yoga, Ihre Matches, oder wenn Sie nicht weiterkommen.",
                target="#mira-chat-button"
            ),
            TourStep(
                step_id="ready",
                title="Los geht's! 🚀",
                message="Das war's schon! Möchten Sie jetzt Ihr Profil hochladen, oder wollen Sie sich erst mal umschauen?",
                action="choose"
            ),
        ]

    return TourResponse(steps=steps, total_steps=len(steps))
