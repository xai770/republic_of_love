#!/usr/bin/env python3
"""
Reverse String Gradient Test Setup
==================================
Creates a comprehensive gradient testing framework for string reversal capabilities
using words of graduated complexity from 2 to 45 letters.
"""

import sqlite3
import logging
import json
from datetime import datetime
from typing import List, Dict, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Word bank organized by length with exact letter counts
REVERSE_WORD_BANK = {
    2: ["on", "no", "in", "up"],
    3: ["cat", "dog", "sky"],
    4: ["milk", "love", "fire"],
    5: ["apple", "world", "sound"],
    6: ["length", "people", "stream"],
    7: ["complex", "plastic", "journal"],
    8: ["computer", "mountain", "lottery"],
    9: ["strengths", "chocolate", "boundary"],
    10: ["submarine", "important", "fantastic"],
    11: ["application"],
    12: ["consideration"],
    13: ["relationship"],
    14: ["communication"],
    15: ["incomprehensible"],
    16: ["congratulatorily"],
    17: ["environmentalist"],
    18: ["disenfranchisement"],
    19: ["unconstitutionality"],
    20: ["counterrevolutionaries", "incomprehensibilities"],
    27: ["honorificabilitudinitatibus"],
    30: ["pseudopseudohypoparathyroidism"],
    34: ["supercalifragilisticexpialidocious"],
    36: ["hippopotomonstrosesquippedaliophobia"],
    45: ["pneumonoultramicroscopicsilicovolcanoconiosis"]
}

def setup_reverse_gradient_canonical():
    """Create or update the reverse string gradient canonical test"""
    
    conn = sqlite3.connect('data/llmcore.db')
    cursor = conn.cursor()
    
    # Create the canonical entry
    canonical_code = 'ff_reverse_gradient'
    
    processing_instructions = """## Processing Instructions
Format your response as [string]. Make sure to include the brackets in the output.

## Processing Payload
Write "{word}" backwards.

## QA Check
Submit ONLY the required response. Do not add spaces. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets."""

    # Insert/update canonical
    cursor.execute("""
        INSERT OR REPLACE INTO canonicals (
            canonical_code,
            facet_id, 
            capability_description,
            processing_instructions,
            processing_payload,
            processing_expected_response,
            qa_instructions,
            qa_scoring,
            enabled,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        canonical_code,
        'ff_reverse_gradient',
        'Follow rules: reverse string exactly - gradient difficulty',
        processing_instructions,
        'Write "{word}" backwards.',
        '[{reversed_word}]',
        'Check if response exactly matches expected format with correct reversed string',
        'EXACT_MATCH',
        1,
        datetime.now().isoformat()
    ))
    
    # Create facet if it doesn't exist
    cursor.execute("""
        INSERT OR IGNORE INTO facets (
            facet_id,
            parent_id,
            short_description,
            remarks,
            enabled,
            timestamp
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        'ff_reverse_gradient',
        'f',
        'Follow rules: reverse string - gradient difficulty',
        'Tests string reversal across graduated word lengths (2-45 letters)',
        1,
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Created canonical: {canonical_code}")

def setup_reverse_test_parameters():
    """Populate word_banks table with reverse string gradient test data"""
    
    conn = sqlite3.connect('data/llmcore.db')
    cursor = conn.cursor()
    
    # Clear existing parameters for this test type
    cursor.execute("DELETE FROM word_banks WHERE category = 'reverse_string_gradient'")
    
    parameter_id = 1
    
    for length, words in REVERSE_WORD_BANK.items():
        for word in words:
            reversed_word = word[::-1]
            
            cursor.execute("""
                INSERT INTO word_banks (
                    category,
                    length,
                    difficulty_score,
                    content,
                    target_letter,
                    expected_count,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                'reverse_string_gradient',
                length,
                length,  # Difficulty score = length
                word,
                reversed_word,  # Store reversed as target_letter field
                length,  # Expected_count = word length
                datetime.now().isoformat()
            ))
            
            logger.info(f"✅ Added parameter {parameter_id}: {word} ({length} letters) -> {reversed_word}")
            parameter_id += 1
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Added {parameter_id - 1} reverse string test parameters")

def setup_reverse_word_bank():
    """This function is now integrated into setup_reverse_test_parameters()"""
    logger.info("✅ Word bank setup integrated into test parameters")

def verify_setup():
    """Verify the gradient setup is complete and show statistics"""
    
    conn = sqlite3.connect('data/llmcore.db')
    cursor = conn.cursor()
    
    # Check canonical
    cursor.execute("SELECT COUNT(*) FROM canonicals WHERE canonical_code = 'ff_reverse_gradient'")
    canonical_count = cursor.fetchone()[0]
    
    # Check parameters (stored in word_banks)
    cursor.execute("SELECT COUNT(*) FROM word_banks WHERE category = 'reverse_string_gradient'")
    param_count = cursor.fetchone()[0]
    
    # Check word bank (same as parameters)
    word_count = param_count
    
    # Get difficulty distribution
    cursor.execute("""
        SELECT length, COUNT(*) 
        FROM word_banks 
        WHERE category = 'reverse_string_gradient' 
        GROUP BY length 
        ORDER BY length
    """)
    difficulty_dist = cursor.fetchall()
    
    conn.close()
    
    print("\n" + "="*60)
    print("🔄 REVERSE STRING GRADIENT TEST SETUP VERIFICATION")
    print("="*60)
    print(f"✅ Canonical entries: {canonical_count}")
    print(f"✅ Test parameters: {param_count}")
    print(f"✅ Word bank entries: {word_count}")
    print("\n📊 DIFFICULTY DISTRIBUTION:")
    
    total_words = 0
    for length, count in difficulty_dist:
        total_words += count
        print(f"   {length:2d} letters: {count:2d} words")
    
    print(f"\n🎯 TOTAL GRADIENT POINTS: {total_words}")
    print(f"🎯 LENGTH RANGE: 2-45 letters")
    print(f"🎯 COMPLEXITY SPAN: {max(dict(difficulty_dist).keys()) - min(dict(difficulty_dist).keys())} levels")
    print("="*60)

def main():
    """Main setup function"""
    
    print("🔄 Setting up Reverse String Gradient Test Framework...")
    
    try:
        # 1. Setup canonical
        setup_reverse_gradient_canonical()
        
        # 2. Setup test parameters
        setup_reverse_test_parameters()
        
        # 3. Setup word bank
        setup_reverse_word_bank()
        
        # 4. Verify everything
        verify_setup()
        
        print("\n✅ Reverse String Gradient Test setup complete!")
        print("   Ready for comprehensive model testing across 27 difficulty levels!")
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        raise

if __name__ == "__main__":
    main()