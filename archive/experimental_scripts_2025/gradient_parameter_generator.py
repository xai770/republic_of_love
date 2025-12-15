#!/usr/bin/env python3
"""
GRADIENT PARAMETER GENERATOR 🌈
===============================
Generate progressive difficulty test parameters for canonical gradients
Because we REALLY NEED systematic capability mapping! 💕
"""

import sqlite3
import json
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

class GradientParameterGenerator:
    """Generate gradient test parameters for canonical capability testing"""
    
    def __init__(self, db_path: str = 'data/llmcore.db'):
        self.db_path = db_path
        
    def generate_mr_literal_recall_gradient(self, max_level: int = 10) -> List[Dict]:
        """Generate memory recall tests with increasing interference"""
        
        target_words = [
            "orchid", "sapphire", "velvet", "cascade", "whisper",
            "crimson", "azure", "melody", "phoenix", "glacier"
        ]
        
        interference_texts = [
            "The quick brown fox jumps over the lazy dog.",
            "In a distant galaxy, stars twinkle like diamonds scattered across black velvet.",
            "Ancient libraries hold secrets whispered through generations of scholars and dreamers.",
            "Mathematics reveals patterns hidden in nature's most beautiful creations and phenomena.",
            "Technology bridges minds across vast distances, creating connections previously impossible to imagine."
        ]
        
        gradient_params = []
        
        for level in range(1, max_level + 1):
            for target_word in target_words:
                # Calculate interference length based on level
                interference_length = level * 50  # 50 chars per level
                
                # Build interference text
                interference = ""
                while len(interference) < interference_length:
                    text_piece = random.choice(interference_texts)
                    interference += text_piece + " "
                
                interference = interference[:interference_length].strip()
                
                # Create the test prompt following canonical format
                test_prompt = f"Remember this word: {target_word}. {interference} Now respond with exactly that word."
                
                gradient_params.append({
                    'canonical_code': 'mr_literal_recall',
                    'difficulty_level': level,
                    'test_word': f"{target_word}_L{level}",  # Make test_word unique per level
                    'interference_length': len(interference),
                    'expected_response': target_word,
                    'prompt_template': test_prompt,
                    'response_format': 'exact_word',
                    'complexity_score': level * 1.2,  # Memory complexity increases super-linearly
                    'gradient_type': 'interference_length',
                    'target_word': target_word  # Keep original for reference
                })
        
        return gradient_params
    
    def generate_kv_calendar_facts_gradient(self, max_level: int = 8) -> List[Dict]:
        """Generate calendar reasoning tests with increasing temporal complexity"""
        
        gradient_params = []
        
        # Level 1: Basic day succession
        level_1_questions = [
            ("What day comes after Monday?", "Tuesday"),
            ("What day comes before Friday?", "Thursday"),
            ("What day comes after Sunday?", "Monday"),
        ]
        
        for idx, (question, answer) in enumerate(level_1_questions):
            gradient_params.append({
                'canonical_code': 'kv_calendar_facts',
                'difficulty_level': 1,
                'test_word': f"L1_Q{idx+1}",  # Unique identifier
                'expected_response': answer,
                'prompt_template': question,
                'response_format': 'day_name',
                'complexity_score': 1.0,
                'gradient_type': 'temporal_reasoning_depth',
                'question': question  # Keep original for reference
            })
        
        # Level 2: Relative day calculation
        level_2_questions = [
            ("If today is Wednesday, what was yesterday?", "Tuesday"),
            ("If today is Friday, what is tomorrow?", "Saturday"),
            ("If today is Sunday, what was the day before yesterday?", "Friday"),
        ]
        
        for idx, (question, answer) in enumerate(level_2_questions):
            gradient_params.append({
                'canonical_code': 'kv_calendar_facts',
                'difficulty_level': 2,
                'test_word': f"L2_Q{idx+1}",  # Unique identifier
                'expected_response': answer,
                'prompt_template': question,
                'response_format': 'day_name',
                'complexity_score': 2.0,
                'gradient_type': 'temporal_reasoning_depth',
                'question': question  # Keep original for reference
            })
        
        # Level 3: Workday logic
        level_3_questions = [
            ("If today is Friday, what's the next workday?", "Monday"),
            ("If today is Sunday, what's the next workday?", "Monday"),
            ("If today is Wednesday, what's the previous workday?", "Tuesday"),
        ]
        
        for idx, (question, answer) in enumerate(level_3_questions):
            gradient_params.append({
                'canonical_code': 'kv_calendar_facts',
                'difficulty_level': 3,
                'test_word': f"L3_Q{idx+1}",  # Unique identifier
                'expected_response': answer,
                'prompt_template': question,
                'response_format': 'day_name',
                'complexity_score': 3.2,
                'gradient_type': 'temporal_reasoning_depth',
                'question': question  # Keep original for reference
            })
        
        # Level 4: Date arithmetic
        level_4_questions = [
            ("If today is January 15th, 2024 (Monday), what day of the week is January 22nd?", "Monday"),
            ("If December 25th is a Monday, what day is January 1st?", "Monday"),
            ("If February 14th is a Wednesday, what day is February 21st?", "Wednesday"),
        ]
        
        for idx, (question, answer) in enumerate(level_4_questions):
            gradient_params.append({
                'canonical_code': 'kv_calendar_facts',
                'difficulty_level': 4,
                'test_word': f"L4_Q{idx+1}",  # Unique identifier
                'expected_response': answer,
                'prompt_template': question,
                'response_format': 'day_name',
                'complexity_score': 4.5,
                'gradient_type': 'temporal_reasoning_depth',
                'question': question  # Keep original for reference
            })
        
        return gradient_params
    
    def generate_rd_youngest_chain_gradient(self, max_level: int = 10) -> List[Dict]:
        """Generate deduction chain tests with increasing chain length"""
        
        gradient_params = []
        
        # Generate alphabet chains of increasing length
        alphabet = string.ascii_uppercase
        
        for level in range(2, max_level + 1):
            # Create multiple chain variations at each level
            for variation in range(3):  # 3 variations per level
                
                # Select random letters for the chain
                chain_letters = random.sample(alphabet, level)
                chain_letters.sort()  # Alphabetical order for consistency
                
                # Create the comparison chain (A > B > C means A is older than B, etc.)
                chain_description = " > ".join(chain_letters)
                
                # The youngest is always the last in the chain
                youngest = chain_letters[-1]
                
                # Create question
                question = f"Given that {chain_description}, who is the youngest?"
                
                gradient_params.append({
                    'canonical_code': 'rd_youngest_chain',
                    'difficulty_level': level,
                    'test_word': f"L{level}_V{variation+1}",  # Unique identifier
                    'expected_response': youngest,
                    'prompt_template': question,
                    'response_format': 'single_letter',
                    'complexity_score': level * 1.1,  # Linear complexity increase
                    'gradient_type': 'chain_length',
                    'chain_length': level,
                    'chain_elements': chain_letters,
                    'chain_description': chain_description  # Keep original for reference
                })
        
        return gradient_params
    
    def generate_of_translate_fr_basic_gradient(self, max_level: int = 6) -> List[Dict]:
        """Generate French translation tests with increasing linguistic complexity"""
        
        gradient_params = []
        
        # Level 1: Simple vocabulary
        level_1_phrases = [
            ("Je suis heureux", "I am happy"),
            ("Il fait beau", "It is beautiful weather"),
            ("J'aime les fleurs", "I love flowers"),
            ("Elle est gentille", "She is kind"),
        ]
        
        for french, english in level_1_phrases:
            gradient_params.append({
                'canonical_code': 'of_translate_fr_basic',
                'difficulty_level': 1,
                'test_word': french,
                'expected_response': english,
                'prompt_template': f'Translate this French phrase to English: "{french}"',
                'response_format': 'english_translation',
                'complexity_score': 1.0,
                'gradient_type': 'linguistic_complexity'
            })
        
        # Level 2: Present tense with articles
        level_2_phrases = [
            ("Nous allons au marché", "We go to the market"),
            ("Les enfants jouent dans le jardin", "The children play in the garden"),
            ("Mon chat dort sur le canapé", "My cat sleeps on the sofa"),
            ("La voiture rouge est rapide", "The red car is fast"),
        ]
        
        for french, english in level_2_phrases:
            gradient_params.append({
                'canonical_code': 'of_translate_fr_basic',
                'difficulty_level': 2,
                'test_word': french,
                'expected_response': english,
                'prompt_template': f'Translate this French phrase to English: "{french}"',
                'response_format': 'english_translation',
                'complexity_score': 2.2,
                'gradient_type': 'linguistic_complexity'
            })
        
        # Level 3: Past and future tenses
        level_3_phrases = [
            ("Hier, j'ai mangé une pomme", "Yesterday, I ate an apple"),
            ("Demain, nous irons au cinéma", "Tomorrow, we will go to the cinema"),
            ("Elle a fini ses devoirs", "She finished her homework"),
            ("Ils partiront en vacances", "They will leave for vacation"),
        ]
        
        for french, english in level_3_phrases:
            gradient_params.append({
                'canonical_code': 'of_translate_fr_basic',
                'difficulty_level': 3,
                'test_word': french,
                'expected_response': english,
                'prompt_template': f'Translate this French phrase to English: "{french}"',
                'response_format': 'english_translation',
                'complexity_score': 3.5,
                'gradient_type': 'linguistic_complexity'
            })
        
        # Level 4: Conditional and subjunctive moods
        level_4_phrases = [
            ("Si j'avais de l'argent, j'achèterais une maison", "If I had money, I would buy a house"),
            ("Il faut que tu viennes demain", "You must come tomorrow"),
            ("Je voudrais que vous compreniez", "I would like you to understand"),
        ]
        
        for french, english in level_4_phrases:
            gradient_params.append({
                'canonical_code': 'of_translate_fr_basic',
                'difficulty_level': 4,
                'test_word': french,
                'expected_response': english,
                'prompt_template': f'Translate this French phrase to English: "{french}"',
                'response_format': 'english_translation',
                'complexity_score': 4.8,
                'gradient_type': 'linguistic_complexity'
            })
        
        return gradient_params
    
    def store_gradient_parameters(self, canonical_code: str, parameters: List[Dict]):
        """Store generated gradient parameters in the database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # First, check if canonical exists and is enabled
        cursor.execute("""
            SELECT canonical_code, enabled FROM canonicals 
            WHERE canonical_code = ?
        """, (canonical_code,))
        
        canonical_info = cursor.fetchone()
        
        if not canonical_info:
            print(f"⚠️  Canonical {canonical_code} not found in database")
            conn.close()
            return 0
        
        if canonical_info[1] == 0:
            print(f"📋 Enabling canonical {canonical_code}...")
            cursor.execute("""
                UPDATE canonicals SET enabled = 1 
                WHERE canonical_code = ?
            """, (canonical_code,))
        
        # Clear existing gradient tests for this canonical
        print(f"🧹 Clearing existing gradient tests for {canonical_code}...")
        cursor.execute("""
            DELETE FROM test_parameters 
            WHERE test_id IN (
                SELECT test_id FROM tests 
                WHERE canonical_code = ?
            )
        """, (canonical_code,))
        
        cursor.execute("""
            DELETE FROM tests 
            WHERE canonical_code = ?
        """, (canonical_code,))
        
        # Get available models (use same as existing tests)
        cursor.execute("""
            SELECT DISTINCT processing_model_name 
            FROM tests 
            WHERE canonical_code IN ('ce_char_extract', 'ff_reverse_gradient')
            ORDER BY processing_model_name
            LIMIT 10
        """)
        
        models = [row[0] for row in cursor.fetchall()]
        
        if not models:
            models = ['llama3.2:latest', 'phi3:latest', 'gemma3:4b']  # Fallback models
        
        created_count = 0
        
        # Create fresh tests for each model
        model_tests = {}
        for model in models:
            cursor.execute("""
                INSERT INTO tests (
                    canonical_code, processing_model_name,
                    created_at, status
                ) VALUES (?, ?, CURRENT_TIMESTAMP, 'ready')
            """, (canonical_code, model))
            
            model_tests[model] = cursor.lastrowid
        
        # Add parameters to all model tests
        for param in parameters:
            for model in models:
                test_id = model_tests[model]
                
                # Create test parameter entry
                cursor.execute("""
                    INSERT INTO test_parameters (
                        test_id, test_word, difficulty_level, expected_response,
                        prompt_template, response_format, word_length, 
                        complexity_score, enabled
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    test_id,
                    param['test_word'],
                    param['difficulty_level'],
                    param['expected_response'],
                    param['prompt_template'],
                    param['response_format'],
                    len(param['test_word']),
                    param['complexity_score']
                ))
                
                created_count += 1
        
        conn.commit()
        conn.close()
        
        return created_count
    
    def generate_all_gradients(self):
        """Generate and store all gradient parameters"""
        
        print("🌈" + "="*60 + "🌈")
        print("   GRADIENT PARAMETER GENERATION")
        print("🌈" + "="*60 + "🌈")
        print("Creating systematic capability gradients! 💕")
        print()
        
        total_created = 0
        
        # Generate mr_literal_recall gradients
        print("🧠 Generating mr_literal_recall gradient parameters...")
        mr_params = self.generate_mr_literal_recall_gradient(max_level=8)
        mr_count = self.store_gradient_parameters('mr_literal_recall', mr_params)
        print(f"   ✅ Created {mr_count} memory recall tests")
        total_created += mr_count
        
        # Generate kv_calendar_facts gradients  
        print("\n📅 Generating kv_calendar_facts gradient parameters...")
        kv_params = self.generate_kv_calendar_facts_gradient(max_level=4)
        kv_count = self.store_gradient_parameters('kv_calendar_facts', kv_params)
        print(f"   ✅ Created {kv_count} calendar reasoning tests")
        total_created += kv_count
        
        # Generate rd_youngest_chain gradients
        print("\n⛓️  Generating rd_youngest_chain gradient parameters...")
        rd_params = self.generate_rd_youngest_chain_gradient(max_level=8)
        rd_count = self.store_gradient_parameters('rd_youngest_chain', rd_params)
        print(f"   ✅ Created {rd_count} deduction chain tests")
        total_created += rd_count
        
        # Generate of_translate_fr_basic gradients
        print("\n🇫🇷 Generating of_translate_fr_basic gradient parameters...")
        fr_params = self.generate_of_translate_fr_basic_gradient(max_level=4)
        fr_count = self.store_gradient_parameters('of_translate_fr_basic', fr_params)
        print(f"   ✅ Created {fr_count} French translation tests")
        total_created += fr_count
        
        print(f"\n🚀 TOTAL GRADIENT PARAMETERS CREATED: {total_created}")
        print("💕 Ready for systematic capability mapping!")
        
        return {
            'memory_recall': mr_count,
            'calendar_facts': kv_count, 
            'deduction_chains': rd_count,
            'french_translation': fr_count,
            'total': total_created
        }

def main():
    """Generate gradient parameters for all target canonicals"""
    
    generator = GradientParameterGenerator()
    results = generator.generate_all_gradients()
    
    print(f"\n💎 Gradient generation complete!")
    print(f"   🧠 Memory tests: {results['memory_recall']}")
    print(f"   📅 Calendar tests: {results['calendar_facts']}")  
    print(f"   ⛓️  Chain tests: {results['deduction_chains']}")
    print(f"   🇫🇷 French tests: {results['french_translation']}")
    print(f"   🌈 Total: {results['total']} systematic capability tests!")
    
    print(f"\n💕 This is us building something beautiful together!")

if __name__ == "__main__":
    main()