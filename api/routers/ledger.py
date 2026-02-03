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
