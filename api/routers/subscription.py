"""
Subscription router — Stripe integration for talent.yoga tiers.

Tiers:
- Free (€0): 10 matches/month, limited Mira
- Standard (€5/mo): Unlimited matches, full Mira, dashboard
- Sustainer (€10+/mo): Everything + supporter recognition

Uses Stripe Checkout (hosted) for payment flows.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime
import os

from api.deps import get_db, require_user
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/subscription", tags=["subscription"])

# ============================================================================
# CONFIGURATION
# ============================================================================

# Stripe keys from environment
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
STRIPE_ENABLED = bool(STRIPE_SECRET_KEY)

# Stripe price IDs (set in Stripe Dashboard)
STRIPE_PRICES = {
    'standard': os.getenv('STRIPE_PRICE_STANDARD'),  # €5/mo
    'sustainer': os.getenv('STRIPE_PRICE_SUSTAINER'),  # €10/mo
}

# Base URL for redirects
BASE_URL = os.getenv('BASE_URL', 'http://localhost:3000')

# Tier definitions
TIERS = {
    'free': {
        'name': 'Free',
        'price_eur': 0,
        'matches_per_month': 10,
        'mira_enabled': True,  # Limited Mira
        'mira_messages_per_day': 5,
        'research_enabled': False,
        'coaching_enabled': False,
    },
    'standard': {
        'name': 'Standard',
        'price_eur': 5,
        'matches_per_month': -1,  # Unlimited
        'mira_enabled': True,
        'mira_messages_per_day': -1,  # Unlimited
        'research_enabled': True,
        'coaching_enabled': True,
    },
    'sustainer': {
        'name': 'Sustainer',
        'price_eur': 10,
        'matches_per_month': -1,
        'mira_enabled': True,
        'mira_messages_per_day': -1,
        'research_enabled': True,
        'coaching_enabled': True,
        'supporter_badge': True,
    },
}


# ============================================================================
# MODELS
# ============================================================================

class SubscriptionStatus(BaseModel):
    tier: str
    tier_name: str
    is_active: bool
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]
    current_period_end: Optional[datetime]
    limits: dict


class CreateCheckoutRequest(BaseModel):
    tier: Literal['standard', 'sustainer']


class CheckoutResponse(BaseModel):
    checkout_url: Optional[str]
    error: Optional[str]


class PortalResponse(BaseModel):
    portal_url: Optional[str]
    error: Optional[str]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_stripe():
    """Get Stripe client, import only if enabled."""
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    return stripe


def get_user_tier(user: dict, conn) -> tuple[str, dict]:
    """Get user's current subscription tier."""
    with conn.cursor() as cur:
        # Check if subscription columns exist
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'subscription_tier'
        """)
        has_subscription_cols = cur.fetchone() is not None
        
        if not has_subscription_cols:
            # Columns not yet added - everyone is free tier
            return 'free', TIERS['free']
        
        cur.execute("""
            SELECT subscription_tier, subscription_status, 
                   stripe_customer_id, stripe_subscription_id,
                   subscription_period_end
            FROM users
            WHERE user_id = %s
        """, (user['user_id'],))
        row = cur.fetchone()
        
        if not row:
            return 'free', TIERS['free']
        
        tier = row['subscription_tier'] or 'free'
        status = row['subscription_status']
        
        # Check if subscription is active
        if tier != 'free' and status != 'active':
            # Downgrade to free if subscription lapsed
            tier = 'free'
        
        return tier, TIERS.get(tier, TIERS['free'])


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/status", response_model=SubscriptionStatus)
def get_subscription_status(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Get current subscription status and tier limits."""
    tier, tier_info = get_user_tier(user, conn)
    
    with conn.cursor() as cur:
        # Check if subscription columns exist
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'stripe_customer_id'
        """)
        has_stripe_cols = cur.fetchone() is not None
        
        stripe_customer_id = None
        stripe_subscription_id = None
        period_end = None
        
        if has_stripe_cols:
            cur.execute("""
                SELECT stripe_customer_id, stripe_subscription_id, 
                       subscription_status, subscription_period_end
                FROM users
                WHERE user_id = %s
            """, (user['user_id'],))
            row = cur.fetchone()
            if row:
                stripe_customer_id = row['stripe_customer_id']
                stripe_subscription_id = row['stripe_subscription_id']
                period_end = row['subscription_period_end']
    
    return SubscriptionStatus(
        tier=tier,
        tier_name=tier_info['name'],
        is_active=tier != 'free' or True,  # Free is always "active"
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
        current_period_end=period_end,
        limits={
            'matches_per_month': tier_info['matches_per_month'],
            'mira_messages_per_day': tier_info.get('mira_messages_per_day', -1),
            'research_enabled': tier_info.get('research_enabled', False),
            'coaching_enabled': tier_info.get('coaching_enabled', False),
            'supporter_badge': tier_info.get('supporter_badge', False),
        }
    )


@router.get("/tiers")
def get_tiers():
    """Get available subscription tiers."""
    return {
        'tiers': TIERS,
        'stripe_enabled': STRIPE_ENABLED
    }


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout_session(
    request: CreateCheckoutRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Create a Stripe Checkout session for subscription.
    
    Returns URL to redirect user to Stripe's hosted checkout page.
    """
    if not STRIPE_ENABLED:
        return CheckoutResponse(
            checkout_url=None,
            error="Payments not yet configured"
        )
    
    stripe = get_stripe()
    price_id = STRIPE_PRICES.get(request.tier)
    
    if not price_id:
        return CheckoutResponse(
            checkout_url=None,
            error=f"Price not configured for tier: {request.tier}"
        )
    
    # Get or create Stripe customer
    with conn.cursor() as cur:
        cur.execute("""
            SELECT stripe_customer_id, email
            FROM users
            WHERE user_id = %s
        """, (user['user_id'],))
        row = cur.fetchone()
        
        customer_id = row['stripe_customer_id']
        email = row['email']
        
        if not customer_id:
            # Create Stripe customer
            try:
                customer = stripe.Customer.create(
                    email=email,
                    metadata={'user_id': str(user['user_id'])}
                )
                customer_id = customer.id
                
                # Store customer ID
                cur.execute("""
                    UPDATE users
                    SET stripe_customer_id = %s
                    WHERE user_id = %s
                """, (customer_id, user['user_id']))
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to create Stripe customer: {e}")
                return CheckoutResponse(
                    checkout_url=None,
                    error="Failed to create payment customer"
                )
    
    # Create checkout session
    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card', 'sepa_debit'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=f"{BASE_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{BASE_URL}/subscription/canceled",
            metadata={
                'user_id': str(user['user_id']),
                'tier': request.tier
            }
        )
        
        logger.info(f"Created checkout session {session.id} for user {user['user_id']}, tier {request.tier}")
        
        return CheckoutResponse(checkout_url=session.url)
        
    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        return CheckoutResponse(
            checkout_url=None,
            error="Failed to create checkout session"
        )


@router.get("/portal", response_model=PortalResponse)
def get_billing_portal(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Get URL to Stripe's hosted billing portal.
    
    Users can manage their subscription, update payment method, etc.
    """
    if not STRIPE_ENABLED:
        return PortalResponse(
            portal_url=None,
            error="Payments not yet configured"
        )
    
    stripe = get_stripe()
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT stripe_customer_id
            FROM users
            WHERE user_id = %s
        """, (user['user_id'],))
        row = cur.fetchone()
        
        if not row or not row['stripe_customer_id']:
            return PortalResponse(
                portal_url=None,
                error="No billing account found"
            )
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=row['stripe_customer_id'],
            return_url=f"{BASE_URL}/dashboard"
        )
        
        return PortalResponse(portal_url=session.url)
        
    except Exception as e:
        logger.error(f"Failed to create portal session: {e}")
        return PortalResponse(
            portal_url=None,
            error="Failed to access billing portal"
        )


@router.post("/webhook")
async def stripe_webhook(request: Request, conn=Depends(get_db)):
    """
    Handle Stripe webhook events.
    
    Events:
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_failed
    """
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    stripe = get_stripe()
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event_type = event['type']
    data = event['data']['object']
    
    logger.info(f"Received Stripe webhook: {event_type}")
    
    with conn.cursor() as cur:
        if event_type == 'customer.subscription.created':
            # New subscription
            customer_id = data['customer']
            subscription_id = data['id']
            status = data['status']
            period_end = datetime.fromtimestamp(data['current_period_end'])
            
            # Determine tier from price
            tier = 'standard'  # Default
            if data.get('items', {}).get('data'):
                price_id = data['items']['data'][0].get('price', {}).get('id')
                if price_id == STRIPE_PRICES.get('sustainer'):
                    tier = 'sustainer'
            
            cur.execute("""
                UPDATE users
                SET subscription_tier = %s,
                    subscription_status = %s,
                    stripe_subscription_id = %s,
                    subscription_period_end = %s,
                    updated_at = NOW()
                WHERE stripe_customer_id = %s
            """, (tier, status, subscription_id, period_end, customer_id))
            
            logger.info(f"Subscription created for customer {customer_id}: {tier}")
            
        elif event_type == 'customer.subscription.updated':
            # Subscription changed (upgrade/downgrade, renewal)
            customer_id = data['customer']
            subscription_id = data['id']
            status = data['status']
            period_end = datetime.fromtimestamp(data['current_period_end'])
            
            # Determine tier
            tier = 'standard'
            if data.get('items', {}).get('data'):
                price_id = data['items']['data'][0].get('price', {}).get('id')
                if price_id == STRIPE_PRICES.get('sustainer'):
                    tier = 'sustainer'
            
            cur.execute("""
                UPDATE users
                SET subscription_tier = %s,
                    subscription_status = %s,
                    subscription_period_end = %s,
                    updated_at = NOW()
                WHERE stripe_customer_id = %s
            """, (tier, status, period_end, customer_id))
            
            logger.info(f"Subscription updated for customer {customer_id}: {tier}, status={status}")
            
        elif event_type == 'customer.subscription.deleted':
            # Subscription canceled
            customer_id = data['customer']
            
            cur.execute("""
                UPDATE users
                SET subscription_tier = 'free',
                    subscription_status = 'canceled',
                    stripe_subscription_id = NULL,
                    subscription_period_end = NULL,
                    updated_at = NOW()
                WHERE stripe_customer_id = %s
            """, (customer_id,))
            
            logger.info(f"Subscription canceled for customer {customer_id}")
            
        elif event_type == 'invoice.payment_failed':
            # Payment failed
            customer_id = data['customer']
            
            cur.execute("""
                UPDATE users
                SET subscription_status = 'past_due',
                    updated_at = NOW()
                WHERE stripe_customer_id = %s
            """, (customer_id,))
            
            logger.warning(f"Payment failed for customer {customer_id}")
        
        conn.commit()
    
    return {"status": "ok"}


# ============================================================================
# TIER ENFORCEMENT (for use in other routers)
# ============================================================================

def check_tier_limit(user: dict, conn, feature: str) -> bool:
    """
    Check if user's tier allows a feature.
    
    Usage in other routers:
        from api.routers.subscription import check_tier_limit
        if not check_tier_limit(user, conn, 'research_enabled'):
            raise HTTPException(status_code=403, detail="Upgrade to access this feature")
    """
    tier, tier_info = get_user_tier(user, conn)
    return tier_info.get(feature, False)


def get_match_limit(user: dict, conn) -> int:
    """
    Get user's monthly match limit.
    
    Returns -1 for unlimited.
    """
    tier, tier_info = get_user_tier(user, conn)
    return tier_info.get('matches_per_month', 10)


def count_monthly_matches(user: dict, conn) -> int:
    """Count matches used this month."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM profile_posting_matches m
            JOIN profiles p ON m.profile_id = p.profile_id
            WHERE p.user_id = %s
              AND m.computed_at >= DATE_TRUNC('month', NOW())
        """, (user['user_id'],))
        return cur.fetchone()['cnt']
