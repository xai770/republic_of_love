#!/usr/bin/env python3
"""
Clean Test Parameters Migration
==============================
Rebuild the unified test_parameters table from clean word_banks source data.
Then run fresh tests with proper parameter tracking.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CleanParameterMigration:
    """Clean rebuild of test_parameters from authoritative word_banks"""
    
    def __init__(self, db_path: str = 'data/llmcore.db'):
        self.db_path = db_path
        
    def clean_rebuild_test_parameters(self):
        """Clean rebuild of unified test_parameters table"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Drop all backup tables (clean slate)
        logger.info("🧹 Cleaning up backup tables...")
        backup_tables = [
            'test_parameters_backup_20250925_190419',
            'test_parameters_backup_20250925_190441', 
            'test_parameters_backup_20250925_190509',
            'test_parameters_fk_backup_20250925_191746'
        ]
        
        for table in backup_tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            logger.info(f"  ✅ Dropped {table}")
        
        # 2. Clear and rebuild main test_parameters table
        logger.info("🏗️ Rebuilding unified test_parameters table...")
        
        cursor.execute("DROP TABLE IF EXISTS test_parameters")
        
        cursor.execute("""
            CREATE TABLE test_parameters (
                param_id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                canonical_code TEXT NOT NULL,
                test_type TEXT NOT NULL,
                test_word TEXT NOT NULL,
                difficulty_level INTEGER NOT NULL,
                expected_response TEXT NOT NULL,
                prompt_template TEXT NOT NULL,
                response_format TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                enabled INTEGER DEFAULT 1,
                
                -- Metadata for analysis
                word_length INTEGER NOT NULL,
                complexity_score REAL,
                
                -- Proper foreign key relationship
                FOREIGN KEY(test_id) REFERENCES tests(test_id) ON DELETE CASCADE,
                UNIQUE(test_id, test_word, test_type)
            )
        """)
        
        # 3. Load strawberry parameters from word_banks
        logger.info("🍓 Loading strawberry test parameters...")
        
        cursor.execute("""
            SELECT content, length, expected_count
            FROM word_banks
            WHERE category = 'letter_counting'
            ORDER BY length, content
        """)
        
        strawberry_count = 0
        for row in cursor.fetchall():
            word = row[0]
            length = row[1]
            expected_count = row[2]
            
            cursor.execute("""
                INSERT INTO test_parameters (
                    canonical_code, test_type, test_word, difficulty_level,
                    expected_response, prompt_template, response_format,
                    word_length, complexity_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'strawberry_gradient',
                'strawberry',
                word,
                length,
                str(expected_count),
                'How many times does the letter "r" appear in the word "{word}"?',
                'number',
                length,
                length  # Simple complexity = length for now
            ))
            strawberry_count += 1
        
        # 4. Load reverse string parameters from word_banks
        logger.info("🔄 Loading reverse string test parameters...")
        
        cursor.execute("""
            SELECT content, length, target_letter
            FROM word_banks
            WHERE category = 'reverse_string_gradient'
            ORDER BY length, content
        """)
        
        reverse_count = 0
        for row in cursor.fetchall():
            word = row[0]
            length = row[1]
            reversed_word = row[2]
            expected = f"[{reversed_word}]"
            
            cursor.execute("""
                INSERT INTO test_parameters (
                    canonical_code, test_type, test_word, difficulty_level,
                    expected_response, prompt_template, response_format,
                    word_length, complexity_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'ff_reverse_gradient',
                'reverse',
                word,
                length,
                expected,
                '''## Processing Instructions
Format your response as [string]. Make sure to include the brackets in the output.

## Processing Payload
Write "{word}" backwards.

## QA Check
Submit ONLY the required response. Do not add spaces. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.''',
                'bracketed_string',
                length,
                length * 1.2  # Reverse is slightly harder than counting
            ))
            reverse_count += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Clean rebuild complete:")
        logger.info(f"  🍓 Strawberry parameters: {strawberry_count}")
        logger.info(f"  🔄 Reverse parameters: {reverse_count}")
        logger.info(f"  📊 Total parameters: {strawberry_count + reverse_count}")
        
        return {
            'strawberry_count': strawberry_count,
            'reverse_count': reverse_count,
            'total_count': strawberry_count + reverse_count
        }
    
    def verify_clean_parameters(self):
        """Verify the clean parameter rebuild"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check parameter counts by type
        cursor.execute("""
            SELECT 
                test_type,
                COUNT(*) as param_count,
                MIN(difficulty_level) as min_diff,
                MAX(difficulty_level) as max_diff,
                AVG(complexity_score) as avg_complexity
            FROM test_parameters
            GROUP BY test_type
            ORDER BY test_type
        """)
        
        print("\n" + "="*60)
        print("🧪 CLEAN TEST PARAMETERS VERIFICATION")
        print("="*60)
        
        total_params = 0
        for row in cursor.fetchall():
            test_type = row[0]
            count = row[1]
            min_diff = row[2]
            max_diff = row[3]
            avg_complexity = row[4]
            total_params += count
            
            print(f"🎯 {test_type.upper()} TEST:")
            print(f"   Parameters: {count}")
            print(f"   Difficulty: {min_diff}-{max_diff} letters")
            print(f"   Avg Complexity: {avg_complexity:.1f}")
            print()
        
        print(f"📊 TOTAL PARAMETERS: {total_params}")
        print("="*60)
        
        # Check for duplicates
        cursor.execute("""
            SELECT canonical_code, test_word, COUNT(*)
            FROM test_parameters
            GROUP BY canonical_code, test_word
            HAVING COUNT(*) > 1
        """)
        
        duplicates = cursor.fetchall()
        if duplicates:
            print("⚠️  DUPLICATES FOUND:")
            for dup in duplicates:
                print(f"   {dup[0]} - {dup[1]} appears {dup[2]} times")
        else:
            print("✅ NO DUPLICATES - Clean parameter set!")
        
        conn.close()

def main():
    """Execute clean parameter migration"""
    
    migrator = CleanParameterMigration()
    
    print("🔥 HOT TAKE: CLEAN REBUILD APPROACH")
    print("="*50)
    print("Rebuilding test_parameters from clean word_banks source data")
    print("This gives us a pristine, unified structure for production!")
    print()
    
    # Execute clean rebuild
    result = migrator.clean_rebuild_test_parameters()
    
    # Verify results
    migrator.verify_clean_parameters()
    
    print("\n✅ Ready for fresh test execution with unified parameters!")
    print("🚀 Next step: Run unified_test_runner.py for clean results")

if __name__ == "__main__":
    main()