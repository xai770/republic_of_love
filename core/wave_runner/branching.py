"""
Branching Logic - Route interactions based on output conditions
Author: Sandy (GitHub Copilot)
Date: November 23, 2025
Target: <50 lines

Evaluates branch conditions from instruction_steps to determine next conversation.
"""

import re
import logging
from typing import Dict, Any, Optional


class BranchEvaluator:
    """Evaluates branching conditions to route workflow steps."""
    
    def __init__(self, db_conn, logger=None):
        """
        Initialize branch evaluator.
        
        Args:
            db_conn: Database connection
            logger: Optional logger
        """
        self.conn = db_conn
        self.logger = logger or logging.getLogger(__name__)
    
    def evaluate_next_conversation(
        self, 
        current_conversation_id: int,
        interaction_output: Dict[str, Any]
    ) -> int:
        """
        Evaluate branching logic to determine next conversation.
        
        Args:
            current_conversation_id: Current conversation/step ID
            interaction_output: Output from completed interaction (JSONB)
            
        Returns:
            Next conversation_id to execute
        """
        cursor = self.conn.cursor()
        
        # Get branching rules for current conversation
        cursor.execute("""
            SELECT 
                default_next_conversation_id,
                branch_condition,
                branch_target_conversation_id
            FROM instruction_steps
            WHERE conversation_id = %s
        """, (current_conversation_id,))
        
        row = cursor.fetchone()
        if not row:
            self.logger.warning(f"No branching rules for conversation {current_conversation_id}")
            return current_conversation_id + 1  # Default: increment
        
        default_next = row['default_next_conversation_id']
        branch_condition = row['branch_condition']
        branch_target = row['branch_target_conversation_id']
        
        # No branching - use default
        if not branch_condition or not branch_target:
            return default_next
        
        # Evaluate branch condition
        if self._evaluate_condition(branch_condition, interaction_output):
            self.logger.info(
                f"Branch condition matched: {current_conversation_id} → {branch_target}"
            )
            return branch_target
        else:
            self.logger.info(
                f"Branch condition failed: {current_conversation_id} → {default_next}"
            )
            return default_next
    
    def _evaluate_condition(
        self, 
        condition: str, 
        output: Dict[str, Any]
    ) -> bool:
        """
        Evaluate branch condition against interaction output.
        
        Supported conditions:
        - "output.status == 'PASS'" - Check JSONB field equality
        - "output.score > 0.8" - Numeric comparison
        - "[PASS]" in output.response - String contains
        
        Args:
            condition: Branch condition string
            output: Interaction output (JSONB)
            
        Returns:
            True if condition matches, False otherwise
        """
        try:
            # Pattern: output.field == 'value'
            if '==' in condition:
                match = re.match(r"output\.(\w+)\s*==\s*'([^']+)'", condition)
                if match:
                    field, expected = match.groups()
                    actual = output.get(field)
                    return actual == expected
            
            # Pattern: output.field > value
            if '>' in condition:
                match = re.match(r"output\.(\w+)\s*>\s*([\d.]+)", condition)
                if match:
                    field, threshold = match.groups()
                    actual = output.get(field)
                    return float(actual) > float(threshold)
            
            # Pattern: "[PASS]" in output.response
            if 'in output.' in condition:
                match = re.match(r"'([^']+)'\s+in\s+output\.(\w+)", condition)
                if match:
                    needle, field = match.groups()
                    haystack = output.get(field, '')
                    return needle in haystack
            
            self.logger.warning(f"Unsupported branch condition: {condition}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error evaluating condition '{condition}': {e}")
            return False
