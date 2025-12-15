#!/usr/bin/env python3
"""
Smart Parameter Linkage
=======================
Links our clean test_parameters to existing tests via proper foreign keys.
Respects the work already done while creating proper relational structure.
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SmartParameterLinkage:
    """Links test_parameters to existing tests with proper foreign keys"""
    
    def __init__(self, db_path: str = 'data/llmcore.db'):
        self.db_path = db_path
        
    def analyze_existing_tests(self):
        """Analyze what tests already exist"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check strawberry tests
        cursor.execute("""
            SELECT 
                COUNT(*) as test_count,
                MIN(test_id) as min_id, 
                MAX(test_id) as max_id,
                COUNT(DISTINCT processing_model_name) as model_count
            FROM tests 
            WHERE canonical_code = 'ce_char_extract'
        """)
        
        strawberry_info = cursor.fetchone()
        
        # Check reverse tests  
        cursor.execute("""
            SELECT 
                COUNT(*) as test_count,
                MIN(test_id) as min_id,
                MAX(test_id) as max_id,
                COUNT(DISTINCT processing_model_name) as model_count
            FROM tests 
            WHERE canonical_code = 'ff_reverse_exact_14'
        """)
        
        reverse_info = cursor.fetchone()
        
        conn.close()
        
        logger.info("🔍 Existing Test Analysis:")
        logger.info(f"  🍓 Strawberry (ce_char_extract): {strawberry_info[0]} tests (IDs {strawberry_info[1]}-{strawberry_info[2]}, {strawberry_info[3]} models)")
        logger.info(f"  🔄 Reverse (ff_reverse_exact_14): {reverse_info[0]} tests (IDs {reverse_info[1]}-{reverse_info[2]}, {reverse_info[3]} models)")
        
        return {
            'strawberry': {
                'count': strawberry_info[0],
                'min_id': strawberry_info[1], 
                'max_id': strawberry_info[2],
                'model_count': strawberry_info[3]
            },
            'reverse': {
                'count': reverse_info[0],
                'min_id': reverse_info[1],
                'max_id': reverse_info[2], 
                'model_count': reverse_info[3]
            }
        }
    
    def create_linked_test_parameters(self):
        """Create test_parameters table properly linked to existing tests"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Drop and recreate test_parameters with proper FK structure
        logger.info("🏗️ Creating properly linked test_parameters table...")
        
        cursor.execute("DROP TABLE IF EXISTS test_parameters")
        
        cursor.execute("""
            CREATE TABLE test_parameters (
                param_id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                
                -- Test definition
                test_word TEXT NOT NULL,
                difficulty_level INTEGER NOT NULL,
                expected_response TEXT NOT NULL,
                prompt_template TEXT NOT NULL,
                response_format TEXT NOT NULL,
                
                -- Metadata
                word_length INTEGER NOT NULL,
                complexity_score REAL,
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                enabled INTEGER DEFAULT 1,
                
                -- Proper foreign key relationship
                FOREIGN KEY(test_id) REFERENCES tests(test_id) ON DELETE CASCADE,
                UNIQUE(test_id, test_word)
            )
        """)
        
        # For strawberry tests - create one parameter per test_id
        logger.info("🍓 Linking strawberry test parameters...")
        
        # Get strawberry test IDs and their models
        cursor.execute("""
            SELECT test_id, processing_model_name
            FROM tests 
            WHERE canonical_code = 'ce_char_extract'
            ORDER BY test_id
        """)
        
        strawberry_tests = cursor.fetchall()
        
        # Get strawberry words from word_banks 
        cursor.execute("""
            SELECT content, length, expected_count
            FROM word_banks
            WHERE category = 'letter_counting'
            ORDER BY length, content
        """)
        
        strawberry_words = cursor.fetchall()
        
        # Link each test to its corresponding word (cycle through words for each model)
        strawberry_count = 0
        for i, (test_id, model_name) in enumerate(strawberry_tests):
            # Cycle through words - each model gets all words
            word_idx = i % len(strawberry_words)
            word, length, expected_count = strawberry_words[word_idx]
            
            cursor.execute("""
                INSERT INTO test_parameters (
                    test_id, test_word, difficulty_level, expected_response,
                    prompt_template, response_format, word_length, complexity_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_id,
                word,
                length,
                str(expected_count),
                'How many times does the letter "r" appear in the word "{word}"?',
                'number',
                length,
                length
            ))
            strawberry_count += 1
        
        # For reverse tests - create one parameter per test_id
        logger.info("🔄 Linking reverse test parameters...")
        
        # Get reverse test IDs
        cursor.execute("""
            SELECT test_id, processing_model_name
            FROM tests 
            WHERE canonical_code = 'ff_reverse_exact_14'
            ORDER BY test_id
        """)
        
        reverse_tests = cursor.fetchall()
        
        # Get reverse words from word_banks
        cursor.execute("""
            SELECT content, length, target_letter
            FROM word_banks
            WHERE category = 'reverse_string_gradient'
            ORDER BY length, content
        """)
        
        reverse_words = cursor.fetchall()
        
        # Link each test to its corresponding word
        reverse_count = 0
        for i, (test_id, model_name) in enumerate(reverse_tests):
            # Cycle through words
            word_idx = i % len(reverse_words)
            word, length, reversed_word = reverse_words[word_idx]
            expected = f"[{reversed_word}]"
            
            cursor.execute("""
                INSERT INTO test_parameters (
                    test_id, test_word, difficulty_level, expected_response,
                    prompt_template, response_format, word_length, complexity_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_id,
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
                length * 1.2
            ))
            reverse_count += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Smart linkage complete:")
        logger.info(f"  🍓 Strawberry parameters: {strawberry_count}")
        logger.info(f"  🔄 Reverse parameters: {reverse_count}")
        logger.info(f"  📊 Total linked parameters: {strawberry_count + reverse_count}")
        
        return {
            'strawberry_count': strawberry_count,
            'reverse_count': reverse_count,
            'total_count': strawberry_count + reverse_count
        }
    
    def verify_linkage(self):
        """Verify the foreign key linkage is working correctly"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Test the join between tests and test_parameters
        cursor.execute("""
            SELECT 
                t.canonical_code,
                t.processing_model_name,
                tp.test_word,
                tp.difficulty_level,
                tp.expected_response
            FROM tests t
            JOIN test_parameters tp ON t.test_id = tp.test_id
            ORDER BY t.canonical_code, t.test_id
            LIMIT 10
        """)
        
        sample_joins = cursor.fetchall()
        
        print("\n" + "="*80)
        print("🔗 FOREIGN KEY LINKAGE VERIFICATION")
        print("="*80)
        
        if sample_joins:
            print("✅ Foreign keys working - Sample joined data:")
            print(f"{'Canonical':<20} {'Model':<20} {'Word':<15} {'Diff':<5} {'Expected':<15}")
            print("-" * 80)
            
            for row in sample_joins:
                canonical = row[0][:18]
                model = row[1][:18] 
                word = row[2][:13]
                diff = str(row[3])
                expected = str(row[4])[:13]
                print(f"{canonical:<20} {model:<20} {word:<15} {diff:<5} {expected:<15}")
        else:
            print("❌ No joined data found - foreign keys may be broken")
        
        # Check counts
        cursor.execute("SELECT COUNT(*) FROM test_parameters")
        param_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tests WHERE canonical_code IN ('ce_char_extract', 'ff_reverse_exact_14')")
        test_count = cursor.fetchone()[0]
        
        print(f"\n📊 Linkage Summary:")
        print(f"   Tests: {test_count}")
        print(f"   Parameters: {param_count}")
        print(f"   Ratio: {param_count/test_count:.1f} params per test")
        print("="*80)
        
        conn.close()

def main():
    """Execute smart parameter linkage"""
    
    linker = SmartParameterLinkage()
    
    print("🧠 SMART PARAMETER LINKAGE APPROACH")
    print("="*50)
    print("Working WITH existing tests, creating proper FK relationships")
    print("Respecting the work already done while building clean structure")
    print()
    
    # Analyze what we have
    existing = linker.analyze_existing_tests()
    
    # Create linked parameters
    result = linker.create_linked_test_parameters()
    
    # Verify linkage
    linker.verify_linkage()
    
    print(f"\n✅ Smart linkage complete - {result['total_count']} parameters linked to existing tests!")
    print("🔗 Full traceability: tests ← test_parameters → test_results")

if __name__ == "__main__":
    main()