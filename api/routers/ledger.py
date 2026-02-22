"""
Ledger API — transparent financials for talent.yoga
"""
from fastapi import APIRouter, Depends
from typing import List, Optional
from datetime import date
from pydantic import BaseModel

from api.deps import get_db

router = APIRouter(prefix="/ledger", tags=["ledger"])


class FounderDebt(BaseModel):
    contributor: str
    initial_investment_cents: int
    repaid_cents: int
    remaining_cents: int
    hours_worked: int
    hourly_rate_cents: int
    repayment_percent: float


class LedgerCurrent(BaseModel):
    month: str
    active_users: int
    revenue_cents: int
    operating_costs_cents: int
    reserve_contribution_cents: int
    founder_repayment_cents: int
    development_fund_cents: int
    founder_debt_total_cents: int
    founder_debt_repaid_cents: int
    founder_debt_remaining_cents: int
    repayment_percent: float
    founders: List[FounderDebt]


class LedgerMonth(BaseModel):
    month: str
    active_users: int
    revenue_cents: int
    operating_costs_cents: int
    reserve_contribution_cents: int
    founder_repayment_cents: int
    development_fund_cents: int
    founder_debt_remaining_cents: int
    notes: Optional[str] = None


@router.get("/current", response_model=LedgerCurrent)
def get_current_ledger(conn=Depends(get_db)):
    """
    Get current month's ledger summary + founder debt status.
    Public endpoint — no auth required (transparency!).
    """
    with conn.cursor() as cur:
        # Get founder debt totals
        cur.execute("""
            SELECT 
                contributor,
                initial_investment_cents,
                repaid_cents,
                (initial_investment_cents - repaid_cents) as remaining_cents,
                hours_worked,
                hourly_rate_cents,
                ROUND(100.0 * repaid_cents / initial_investment_cents, 2) as repayment_percent
            FROM founder_debt
            ORDER BY initial_investment_cents DESC
        """)
        founders = [FounderDebt(**row) for row in cur.fetchall()]
        
        total_invested = sum(f.initial_investment_cents for f in founders)
        total_repaid = sum(f.repaid_cents for f in founders)
        total_remaining = total_invested - total_repaid
        
        # Get current month's ledger (or latest)
        cur.execute("""
            SELECT * FROM ledger_monthly 
            ORDER BY month DESC 
            LIMIT 1
        """)
        ledger = cur.fetchone()
        
        if ledger:
            return LedgerCurrent(
                month=str(ledger['month']),
                active_users=ledger['active_users'],
                revenue_cents=ledger['revenue_cents'],
                operating_costs_cents=ledger['operating_costs_cents'],
                reserve_contribution_cents=ledger['reserve_contribution_cents'],
                founder_repayment_cents=ledger['founder_repayment_cents'],
                development_fund_cents=ledger['development_fund_cents'],
                founder_debt_total_cents=total_invested,
                founder_debt_repaid_cents=total_repaid,
                founder_debt_remaining_cents=total_remaining,
                repayment_percent=round(100.0 * total_repaid / total_invested, 2) if total_invested else 0,
                founders=founders
            )
        else:
            # No ledger entries yet — return founder debt only
            return LedgerCurrent(
                month=str(date.today().replace(day=1)),
                active_users=0,
                revenue_cents=0,
                operating_costs_cents=0,
                reserve_contribution_cents=0,
                founder_repayment_cents=0,
                development_fund_cents=0,
                founder_debt_total_cents=total_invested,
                founder_debt_repaid_cents=total_repaid,
                founder_debt_remaining_cents=total_remaining,
                repayment_percent=round(100.0 * total_repaid / total_invested, 2) if total_invested else 0,
                founders=founders
            )


@router.get("/history", response_model=List[LedgerMonth])
def get_ledger_history(
    limit: int = 12,
    conn=Depends(get_db)
):
    """
    Get ledger history (last N months).
    Public endpoint.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT * FROM ledger_monthly 
            ORDER BY month DESC 
            LIMIT %s
        """, (limit,))
        
        return [LedgerMonth(
            month=str(row['month']),
            active_users=row['active_users'],
            revenue_cents=row['revenue_cents'],
            operating_costs_cents=row['operating_costs_cents'],
            reserve_contribution_cents=row['reserve_contribution_cents'],
            founder_repayment_cents=row['founder_repayment_cents'],
            development_fund_cents=row['development_fund_cents'],
            founder_debt_remaining_cents=row['founder_debt_remaining_cents'],
            notes=row.get('notes')
        ) for row in cur.fetchall()]


@router.get("/founder-debt", response_model=List[FounderDebt])
def get_founder_debt(conn=Depends(get_db)):
    """
    Get founder debt breakdown.
    Public endpoint.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                contributor,
                initial_investment_cents,
                repaid_cents,
                (initial_investment_cents - repaid_cents) as remaining_cents,
                hours_worked,
                hourly_rate_cents,
                ROUND(100.0 * repaid_cents / initial_investment_cents, 2) as repayment_percent
            FROM founder_debt
            ORDER BY initial_investment_cents DESC
        """)
        return [FounderDebt(**row) for row in cur.fetchall()]


# Real compute costs per event (from billing_assumptions.yaml Section D)
_COMPUTE_COST_CENTS = {
    'mira_message':  0.3,
    'cv_extraction': 5.0,
    'cover_letter':  3.0,
    'match_report':  2.0,
    'profile_embed': 0.2,
}

# Fixed monthly infrastructure costs (from billing_assumptions.yaml Sections B+C)
_MONTHLY_INFRA_CENTS = {
    'gpu_server_amortization': 6944,   # €69.44
    'electricity':             3000,   # €30.00
    'backup_storage':          500,    # €5.00
    'domain_ssl':              300,    # €3.00
    'vpn':                     1000,   # €10.00
    'pipeline_compute':        1500,   # €15.00
}


@router.get("/compute-transparency")
def get_compute_transparency(conn=Depends(get_db)):
    """
    System-wide compute and infrastructure cost transparency.
    Public endpoint — shows real costs for shared stewardship.

    Returns: monthly infra costs, total AI compute this month,
    active yogi count, and average compute cost per yogi.
    """
    with conn.cursor() as cur:
        # This month's AI events by type
        cur.execute("""
            SELECT event_type, COUNT(*) as cnt
            FROM usage_events
            WHERE created_at >= date_trunc('month', CURRENT_DATE)
            GROUP BY event_type
        """)
        event_rows = cur.fetchall()

        # Active yogis this month
        cur.execute("""
            SELECT COUNT(DISTINCT user_id) as active
            FROM usage_events
            WHERE created_at >= date_trunc('month', CURRENT_DATE)
        """)
        active_row = cur.fetchone()
        active_yogis = active_row['active'] if active_row else 0

    # Calculate total compute cost
    ai_breakdown = []
    total_ai_cents = 0.0
    for r in event_rows:
        et = r['event_type']
        cnt = r['cnt']
        cost_each = _COMPUTE_COST_CENTS.get(et, 0)
        subtotal = round(cost_each * cnt, 2)
        total_ai_cents += subtotal
        ai_breakdown.append({
            'event_type': et,
            'count': cnt,
            'compute_cost_cents': round(subtotal, 2),
        })

    total_infra_cents = sum(_MONTHLY_INFRA_CENTS.values())
    total_cost_cents = round(total_infra_cents + total_ai_cents, 2)
    avg_per_yogi_cents = round(total_cost_cents / active_yogis, 2) if active_yogis > 0 else 0

    return {
        'month': str(date.today().replace(day=1)),
        'infrastructure': {
            'breakdown': [{'item': k, 'cents': v} for k, v in _MONTHLY_INFRA_CENTS.items()],
            'total_cents': total_infra_cents,
        },
        'ai_compute': {
            'breakdown': ai_breakdown,
            'total_cents': round(total_ai_cents, 2),
        },
        'total_monthly_cost_cents': total_cost_cents,
        'active_yogis': active_yogis,
        'avg_cost_per_yogi_cents': avg_per_yogi_cents,
    }
