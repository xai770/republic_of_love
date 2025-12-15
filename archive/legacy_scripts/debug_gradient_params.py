#!/usr/bin/env python3
"""Debug the gradient parameter generation"""

import sys
sys.path.append('/home/xai/Documents/ty_learn/scripts')

from gradient_parameter_generator import GradientParameterGenerator

def debug_mr_params():
    generator = GradientParameterGenerator()
    params = generator.generate_mr_literal_recall_gradient(max_level=3)
    
    print("Generated MR params:")
    
    test_words = []
    for p in params:
        print(f"Level {p['difficulty_level']}: '{p['test_word']}'")
        test_words.append(p['test_word'])
    
    # Check for duplicates
    duplicates = []
    seen = set()
    for word in test_words:
        if word in seen:
            duplicates.append(word)
        seen.add(word)
    
    print(f"\nTotal params: {len(params)}")
    print(f"Unique test_words: {len(seen)}")
    print(f"Duplicates: {duplicates}")

if __name__ == "__main__":
    debug_mr_params()