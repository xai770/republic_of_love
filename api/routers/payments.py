"""
Payment router — Stripe one-time top-ups + Sustainer recurring.

Top-ups: €5 / €10 / €20 packs via Stripe Checkout (hosted).
Sustainer: Monthly recurring, choose-your-amount (€10+).

Flow:
  1. POST /payments/topup  → Stripe Checkout → redirect back
  2. POST /payments/webhook → credit_balance updated
  3. POST /payments/sustainer → Stripe Checkout (subscription) → redirect back

Uses same Stripe keys as subscription.py.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import os

from api.deps import get_db, require_user
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])

# ── Configuration ────────────────────────────────────────────────────────

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET_PAYMENTS = os.getenv('STRIPE_WEBHOOK_SECRET_PAYMENTS', os.getenv('STRIPE_WEBHOOK_SECRET'))
STRIPE_ENABLED = bool(STRIPE_SECRET_KEY)

BASE_URL = os.getenv('BASE_URL', 'https://talent.yoga')

# Top-up packs (amount in cents)
TOPUP_PACKS = {
    500:  {'label': '€5.00',  'cents': 500},
    1000: {'label': '€10.00', 'cents': 1000},
    2000: {'label': '€20.00', 'cents': 2000},
}

# Sustainer minimum (cents)
SUSTAINER_MIN_CENTS = 1000  # €10/month


# ── Models ───────────────────────────────────────────────────────────────

class TopupRequest(BaseModel):
    amount_cents: int  # 500, 1000, or 2000


class SustainerRequest(BaseModel):
    amount_cents: int  # ≥1000 (€10+/mo), choose your amount


class CheckoutResponse(BaseModel):
    checkout_url: Optional[str] = None
    error: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────

def _get_stripe():
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    return stripe


def _get_or_create_customer(stripe, conn, user: dict) -> str:
    """Get existing Stripe customer ID or create one."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT stripe_customer_id, email FROM users WHERE user_id = %s",
            (user['user_id'],),
        )
        row = cur.fetchone()

    customer_id = row['stripe_customer_id'] if row else None
    if customer_id:
        return customer_id

    email = row['email'] if row else None
    customer = stripe.Customer.create(
        email=email,
        metadata={'user_id': str(user['user_id'])},
    )
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET stripe_customer_id = %s WHERE user_id = %s",
            (customer.id, user['user_id']),
        )
    conn.commit()
    return customer.id


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("/status")
def payment_status():
    """Check if payments are enabled."""
    return {"stripe_enabled": STRIPE_ENABLED, "topup_packs": TOPUP_PACKS}


@router.post("/topup", response_model=CheckoutResponse)
def create_topup_session(
    req: TopupRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Create a Stripe Checkout session for a one-time credit top-up.
    Returns the checkout URL to redirect the user to.
    """
    if not STRIPE_ENABLED:
        return CheckoutResponse(error="Payments not yet configured")

    if req.amount_cents not in TOPUP_PACKS:
        return CheckoutResponse(error=f"Invalid amount. Choose from: {list(TOPUP_PACKS.keys())}")

    stripe = _get_stripe()
    pack = TOPUP_PACKS[req.amount_cents]

    try:
        customer_id = _get_or_create_customer(stripe, conn, user)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card', 'sepa_debit'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'unit_amount': pack['cents'],
                    'product_data': {
                        'name': f'talent.yoga Credit Top-Up ({pack["label"]})',
                        'description': f'{pack["label"]} added to your talent.yoga credit balance',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{BASE_URL}/account?topup=success&amount={pack['cents']}",
            cancel_url=f"{BASE_URL}/account?topup=canceled",
            metadata={
                'user_id': str(user['user_id']),
                'type': 'topup',
                'amount_cents': str(pack['cents']),
            },
        )

        logger.info(f"Topup checkout {session.id} for user {user['user_id']}, {pack['label']}")
        return CheckoutResponse(checkout_url=session.url)

    except Exception as e:
        logger.error(f"Topup checkout failed: {e}")
        return CheckoutResponse(error="Failed to create checkout session")


@router.post("/sustainer", response_model=CheckoutResponse)
def create_sustainer_session(
    req: SustainerRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Create a Stripe Checkout session for a Sustainer subscription.
    Monthly recurring, choose-your-amount (€10+ /mo).
    """
    if not STRIPE_ENABLED:
        return CheckoutResponse(error="Payments not yet configured")

    if req.amount_cents < SUSTAINER_MIN_CENTS:
        return CheckoutResponse(error=f"Minimum Sustainer amount is €{SUSTAINER_MIN_CENTS / 100:.2f}/month")

    stripe = _get_stripe()

    try:
        customer_id = _get_or_create_customer(stripe, conn, user)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card', 'sepa_debit'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'unit_amount': req.amount_cents,
                    'recurring': {'interval': 'month'},
                    'product_data': {
                        'name': 'talent.yoga Sustainer',
                        'description': f'Monthly Sustainer — €{req.amount_cents / 100:.2f}/mo. Unlimited AI + sponsor a free user.',
                    },
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{BASE_URL}/account?sustainer=success",
            cancel_url=f"{BASE_URL}/account?sustainer=canceled",
            metadata={
                'user_id': str(user['user_id']),
                'type': 'sustainer',
                'amount_cents': str(req.amount_cents),
            },
        )

        logger.info(f"Sustainer checkout {session.id} for user {user['user_id']}, €{req.amount_cents / 100:.2f}/mo")
        return CheckoutResponse(checkout_url=session.url)

    except Exception as e:
        logger.error(f"Sustainer checkout failed: {e}")
        return CheckoutResponse(error="Failed to create checkout session")


@router.post("/webhook")
async def payments_webhook(request: Request, conn=Depends(get_db)):
    """
    Handle Stripe webhook events for top-ups and sustainers.

    Events:
    - checkout.session.completed  → credit top-up
    - customer.subscription.created/updated/deleted → sustainer status
    - invoice.payment_failed → sustainer lapse
    """
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    import stripe
    stripe.api_key = STRIPE_SECRET_KEY

    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    if not sig_header or not STRIPE_WEBHOOK_SECRET_PAYMENTS:
        raise HTTPException(status_code=400, detail="Missing signature or webhook secret")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET_PAYMENTS
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event['type']
    data = event['data']['object']
    logger.info(f"Payments webhook: {event_type}")

    with conn.cursor() as cur:
        if event_type == 'checkout.session.completed':
            meta = data.get('metadata', {})

            if meta.get('type') == 'topup':
                # ── One-time top-up completed ──
                user_id = int(meta['user_id'])
                amount = int(meta['amount_cents'])
                pi_id = data.get('payment_intent')

                from lib.credits import topup_credit
                new_bal = topup_credit(
                    conn, user_id, amount,
                    stripe_pi=pi_id,
                    description=f"Top-up €{amount / 100:.2f}",
                    commit=False,
                )
                conn.commit()
                logger.info(f"Topup applied: user {user_id}, +€{amount / 100:.2f}, new balance €{new_bal / 100:.2f}")

            elif meta.get('type') == 'sustainer':
                # ── New sustainer subscription ──
                user_id = int(meta['user_id'])
                subscription_id = data.get('subscription')

                cur.execute(
                    """
                    UPDATE users
                    SET subscription_tier = 'sustainer',
                        subscription_status = 'active',
                        stripe_subscription_id = %s,
                        updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (subscription_id, user_id),
                )
                conn.commit()
                logger.info(f"Sustainer activated: user {user_id}")

        elif event_type in (
            'customer.subscription.updated',
            'customer.subscription.deleted',
        ):
            # Sustainer status changes (already handled by subscription.py,
            # but if using separate webhook endpoints, handle here too)
            customer_id = data.get('customer')
            if not customer_id:
                return {"status": "ok"}

            if event_type == 'customer.subscription.deleted':
                cur.execute(
                    """
                    UPDATE users
                    SET subscription_tier = 'free',
                        subscription_status = 'canceled',
                        stripe_subscription_id = NULL,
                        updated_at = NOW()
                    WHERE stripe_customer_id = %s
                      AND subscription_tier = 'sustainer'
                    """,
                    (customer_id,),
                )
                conn.commit()
                logger.info(f"Sustainer canceled: customer {customer_id}")

        elif event_type == 'invoice.payment_failed':
            customer_id = data.get('customer')
            if customer_id:
                cur.execute(
                    """
                    UPDATE users
                    SET subscription_status = 'past_due',
                        updated_at = NOW()
                    WHERE stripe_customer_id = %s
                      AND subscription_tier = 'sustainer'
                    """,
                    (customer_id,),
                )
                conn.commit()
                logger.warning(f"Sustainer payment failed: customer {customer_id}")

    return {"status": "ok"}
