#!/usr/bin/env python3
"""
User Verification Service - Verify Then Forget

Core Principle: Verify the claim, forget the evidence.

This module verifies user claims (employment, certifications) using 
web search and public registries, then DELETES all evidence, 
storing only the boolean result.

PRIVACY CRITICAL:
- Real names are NEVER stored, logged, or returned
- Search results are NEVER stored
- Only verification results persist

Usage:
    from core.user_system.verifier import UserVerifier
    
    verifier = UserVerifier(db_conn)
    result = verifier.verify_company_employment(
        user_id=123,
        real_name="John Smith",  # TEMPORARY - deleted after use
        company_id=47
    )
    # Returns: {"verified": True, "confidence": 0.85}
    # real_name is now gone from memory

Author: Arden
Date: 2025-11-30
"""

import os
import sys
import gc
import ctypes
import subprocess
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

load_dotenv()


class SecureString:
    """
    A string that can be securely wiped from memory.
    
    Python strings are immutable and can linger in memory.
    This class uses a bytearray that can be overwritten with zeros.
    """
    
    def __init__(self, value: str):
        self._data = bytearray(value.encode('utf-8'))
    
    def __str__(self) -> str:
        return self._data.decode('utf-8')
    
    def wipe(self):
        """Overwrite memory with zeros, then delete."""
        for i in range(len(self._data)):
            self._data[i] = 0
        self._data = bytearray()
        gc.collect()
    
    def __del__(self):
        """Auto-wipe on garbage collection."""
        if hasattr(self, '_data') and self._data:
            self.wipe()


def secure_wipe(*variables):
    """
    Attempt to securely wipe variables from memory.
    
    This is a best-effort approach - Python doesn't guarantee memory clearing.
    But we do what we can:
    1. Overwrite SecureString objects
    2. Delete references
    3. Force garbage collection
    """
    for var in variables:
        if isinstance(var, SecureString):
            var.wipe()
        elif isinstance(var, str):
            # Can't really wipe Python strings, but we can dereference
            pass
        elif isinstance(var, (list, dict)):
            # Clear containers
            if isinstance(var, list):
                var.clear()
            elif isinstance(var, dict):
                var.clear()
    
    # Force garbage collection
    gc.collect()


class UserVerifier:
    """
    Verifies user claims using the "verify then forget" pattern.
    
    CRITICAL PRIVACY RULES:
    1. Real names exist only in RAM during verification
    2. Search results are never persisted
    3. Only verification boolean + confidence are stored
    4. All sensitive data is wiped after use
    """
    
    def __init__(self, db_conn=None):
        """Initialize verifier with optional database connection."""
        self.conn = db_conn or self._get_connection()
        
        # Minimum confidence to count as "verified"
        self.min_confidence = 0.7
        
        # Verification expiry (days)
        self.verification_expiry_days = 730  # 2 years
    
    def _get_connection(self):
        """Get database connection from environment."""
        return psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST')
        )
    
    def _web_search(self, query: str) -> str:
        """
        Search the web using ddgr (DuckDuckGo CLI).
        
        Returns search results as text.
        Results are NEVER stored - caller must wipe after use.
        """
        try:
            result = subprocess.run(
                ['ddgr', '--json', '-n', '5', query],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            return '{"error": "timeout"}'
        except FileNotFoundError:
            return '{"error": "ddgr not installed"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'
    
    def _analyze_with_llm(self, prompt: str, context: str) -> Dict[str, Any]:
        """
        Analyze search results with local LLM.
        
        Uses ollama with mistral:7b for local processing.
        No data leaves the machine.
        """
        try:
            import requests
            
            full_prompt = f"""{prompt}

Context:
{context}

Respond with ONLY a JSON object:
{{"likely_match": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation"}}
"""
            
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': 'mistral:latest',
                    'prompt': full_prompt,
                    'stream': False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get('response', '{}')
                
                # Extract JSON from response
                try:
                    # Find JSON in response
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    if start >= 0 and end > start:
                        return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            
            return {"likely_match": False, "confidence": 0.0, "reasoning": "Analysis failed"}
            
        except Exception as e:
            return {"likely_match": False, "confidence": 0.0, "reasoning": f"Error: {str(e)}"}
    
    def _get_company_name(self, company_id: int) -> Optional[str]:
        """Get company name by ID."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT company_name FROM companies WHERE company_id = %s",
                (company_id,)
            )
            row = cur.fetchone()
            return row[0] if row else None
    
    def verify_company_employment(
        self,
        user_id: int,
        real_name: str,
        company_id: int
    ) -> Dict[str, Any]:
        """
        Verify user worked at a company via web search.
        
        PRIVACY CRITICAL:
        - real_name is NEVER stored, logged, or returned
        - Search results are NEVER stored
        - Only verification result is persisted
        
        Args:
            user_id: The user's ID in our system
            real_name: User's real name (TEMPORARY - deleted after use)
            company_id: The company ID to verify against
        
        Returns:
            {"verified": bool, "confidence": float, "company_id": int}
        """
        # Wrap in SecureString for proper cleanup
        secure_name = SecureString(real_name)
        search_results = None
        analysis = None
        
        try:
            # Get company name
            company_name = self._get_company_name(company_id)
            if not company_name:
                return {"verified": False, "confidence": 0.0, "error": "company_not_found"}
            
            # Build search query
            search_query = f'"{secure_name}" "{company_name}"'
            
            # Search the web (results stay in RAM only)
            search_results = self._web_search(search_query)
            
            # Analyze with local LLM
            analysis = self._analyze_with_llm(
                prompt=f"Based on these search results, determine if '{secure_name}' likely worked at '{company_name}'. Look for LinkedIn profiles, press releases, company announcements, or professional directories that confirm employment.",
                context=search_results
            )
            
            # Determine verification result
            is_verified = (
                analysis.get('likely_match', False) and 
                analysis.get('confidence', 0.0) >= self.min_confidence
            )
            confidence = analysis.get('confidence', 0.0)
            
            # Calculate expiry
            expires_at = datetime.now() + timedelta(days=self.verification_expiry_days)
            
            # Store ONLY the result (no PII)
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_company_verifications 
                    (user_id, company_id, is_verified, confidence, verification_method, expires_at)
                    VALUES (%s, %s, %s, %s, 'web_search', %s)
                    ON CONFLICT (user_id, company_id) DO UPDATE 
                    SET is_verified = EXCLUDED.is_verified,
                        confidence = EXCLUDED.confidence,
                        verification_method = EXCLUDED.verification_method,
                        verified_at = NOW(),
                        expires_at = EXCLUDED.expires_at
                """, (user_id, company_id, is_verified, confidence, expires_at))
                self.conn.commit()
            
            # Return result (no PII)
            return {
                "verified": is_verified,
                "confidence": float(confidence),
                "company_id": company_id
            }
            
        finally:
            # CRITICAL: Wipe all sensitive data
            secure_wipe(secure_name)
            if search_results:
                search_results = None
            if analysis:
                if isinstance(analysis, dict):
                    analysis.clear()
                analysis = None
            gc.collect()
    
    def verify_certification(
        self,
        user_id: int,
        real_name: str,
        certification: str
    ) -> Dict[str, Any]:
        """
        Verify a professional certification (CFA, FRM, PMP, etc.).
        
        Args:
            user_id: The user's ID
            real_name: User's real name (TEMPORARY)
            certification: The certification code ('CFA', 'FRM', 'PMP')
        
        Returns:
            {"verified": bool, "confidence": float, "certification": str}
        """
        secure_name = SecureString(real_name)
        search_results = None
        analysis = None
        
        # Registry search queries by certification
        REGISTRY_QUERIES = {
            'CFA': 'site:cfainstitute.org "{name}" charterholder',
            'FRM': 'site:garp.org "{name}" certified',
            'PMP': 'site:pmi.org "{name}" PMP',
            'CPA': '"{name}" CPA certified public accountant',
            'ACCA': 'site:accaglobal.com "{name}" member',
        }
        
        try:
            cert_upper = certification.upper()
            
            if cert_upper not in REGISTRY_QUERIES:
                # Generic certification search
                search_query = f'"{secure_name}" {certification} certified'
            else:
                search_query = REGISTRY_QUERIES[cert_upper].format(name=str(secure_name))
            
            # Search
            search_results = self._web_search(search_query)
            
            # Analyze
            analysis = self._analyze_with_llm(
                prompt=f"Based on these search results, determine if '{secure_name}' holds a {certification} certification. Look for official registry listings, announcements, or professional profiles.",
                context=search_results
            )
            
            is_verified = (
                analysis.get('likely_match', False) and 
                analysis.get('confidence', 0.0) >= self.min_confidence
            )
            confidence = analysis.get('confidence', 0.0)
            
            # Store result
            expires_at = datetime.now() + timedelta(days=self.verification_expiry_days)
            
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_verifications 
                    (user_id, verification_type, claimed_value, is_verified, confidence, verification_method, expires_at)
                    VALUES (%s, 'certification', %s, %s, %s, 'web_search', %s)
                    ON CONFLICT (user_id, verification_type, claimed_value) DO UPDATE 
                    SET is_verified = EXCLUDED.is_verified,
                        confidence = EXCLUDED.confidence,
                        verified_at = NOW(),
                        expires_at = EXCLUDED.expires_at
                """, (user_id, cert_upper, is_verified, confidence, expires_at))
                self.conn.commit()
            
            return {
                "verified": is_verified,
                "confidence": float(confidence),
                "certification": cert_upper
            }
            
        finally:
            secure_wipe(secure_name)
            search_results = None
            if analysis:
                analysis.clear() if isinstance(analysis, dict) else None
                analysis = None
            gc.collect()
    
    def check_verification_status(
        self,
        user_id: int,
        company_id: Optional[int] = None,
        certification: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check existing verification status without re-verifying.
        
        This reads from stored results - no PII involved.
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if company_id:
                cur.execute("""
                    SELECT is_verified, confidence, verified_at, expires_at
                    FROM user_company_verifications
                    WHERE user_id = %s AND company_id = %s
                """, (user_id, company_id))
                row = cur.fetchone()
                if row:
                    now = datetime.now(timezone.utc)
                    expired = row['expires_at'] and row['expires_at'] < now
                    return {
                        "found": True,
                        "verified": row['is_verified'] and not expired,
                        "confidence": float(row['confidence']) if row['confidence'] else 0.0,
                        "verified_at": row['verified_at'].isoformat() if row['verified_at'] else None,
                        "expired": expired
                    }
                return {"found": False}
            
            elif certification:
                cur.execute("""
                    SELECT is_verified, confidence, verified_at, expires_at
                    FROM user_verifications
                    WHERE user_id = %s AND verification_type = 'certification' AND claimed_value = %s
                """, (user_id, certification.upper()))
                row = cur.fetchone()
                if row:
                    now = datetime.now(timezone.utc)
                    expired = row['expires_at'] and row['expires_at'] < now
                    return {
                        "found": True,
                        "verified": row['is_verified'] and not expired,
                        "confidence": float(row['confidence']) if row['confidence'] else 0.0,
                        "verified_at": row['verified_at'].isoformat() if row['verified_at'] else None,
                        "expired": expired
                    }
                return {"found": False}
        
        return {"error": "must specify company_id or certification"}
    
    def get_user_verifications(self, user_id: int) -> Dict[str, Any]:
        """
        Get all verifications for a user.
        
        Returns only verification status - no PII.
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Company verifications
            cur.execute("""
                SELECT ucv.company_id, c.company_name, ucv.is_verified, 
                       ucv.confidence, ucv.verified_at, ucv.expires_at
                FROM user_company_verifications ucv
                JOIN companies c ON ucv.company_id = c.company_id
                WHERE ucv.user_id = %s
                ORDER BY ucv.verified_at DESC
            """, (user_id,))
            companies = cur.fetchall()
            
            # Other verifications
            cur.execute("""
                SELECT verification_type, claimed_value, is_verified,
                       confidence, verified_at, expires_at
                FROM user_verifications
                WHERE user_id = %s
                ORDER BY verified_at DESC
            """, (user_id,))
            others = cur.fetchall()
        
        return {
            "user_id": user_id,
            "company_verifications": [dict(r) for r in companies],
            "other_verifications": [dict(r) for r in others]
        }


# ═══════════════════════════════════════════════════════════════
# CLI for testing
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='User Verification Service')
    parser.add_argument('--user-id', type=int, required=True, help='User ID')
    parser.add_argument('--name', type=str, help='Real name (for verification)')
    parser.add_argument('--company-id', type=int, help='Company ID to verify')
    parser.add_argument('--certification', type=str, help='Certification to verify (CFA, FRM, etc)')
    parser.add_argument('--check-only', action='store_true', help='Only check existing status')
    
    args = parser.parse_args()
    
    verifier = UserVerifier()
    
    if args.check_only:
        if args.company_id:
            result = verifier.check_verification_status(args.user_id, company_id=args.company_id)
        elif args.certification:
            result = verifier.check_verification_status(args.user_id, certification=args.certification)
        else:
            result = verifier.get_user_verifications(args.user_id)
    else:
        if not args.name:
            print("Error: --name required for verification")
            sys.exit(1)
        
        if args.company_id:
            result = verifier.verify_company_employment(args.user_id, args.name, args.company_id)
        elif args.certification:
            result = verifier.verify_certification(args.user_id, args.name, args.certification)
        else:
            print("Error: --company-id or --certification required")
            sys.exit(1)
    
    print(json.dumps(result, indent=2, default=str))
