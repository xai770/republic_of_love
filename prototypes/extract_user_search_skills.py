#!/usr/bin/env python3
"""
Extract User Search Skills
==========================

Purpose: Extract skill aliases from user's profile for job search query generation.
Migration Target: Workflow 3006, Conversation 1
Author: Arden
Date: 2025-11-16

Usage:
    python3 prototypes/extract_user_search_skills.py --user-id 1
    python3 prototypes/extract_user_search_skills.py --user-id 1 --format json
    python3 prototypes/extract_user_search_skills.py --user-id 1 --limit 10
"""

import sys
import os
import argparse
import json
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_connection, return_connection
from psycopg2.extras import RealDictCursor


class UserSkillExtractor:
    """Extract skills from user profile for search query generation"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.conn = None
        self.cursor = None
    
    def __enter__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            return_connection(self.conn)
    
    def get_user_info(self) -> Optional[Dict]:
        """Get basic user information"""
        self.cursor.execute("""
            SELECT user_id, email, full_name
            FROM users
            WHERE user_id = %s
        """, (self.user_id,))
        
        return self.cursor.fetchone()
    
    def get_skills(self, limit: Optional[int] = None) -> List[str]:
        """
        Extract skill aliases for user from profile_skills table.
        
        Returns list of skill names (aliases) suitable for search queries.
        """
        query = """
            SELECT DISTINCT sa.skill_name
            FROM skill_aliases sa
            INNER JOIN profile_skills ps ON sa.skill_id = ps.skill_id
            INNER JOIN profiles p ON ps.profile_id = p.profile_id
            WHERE p.user_id = %s
            ORDER BY sa.skill_name
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        self.cursor.execute(query, (self.user_id,))
        
        results = self.cursor.fetchall()
        return [row['skill_name'] for row in results]
    
    def get_skills_with_proficiency(self) -> List[Dict]:
        """
        Get skills with proficiency levels for more sophisticated analysis.
        
        Returns list of dicts with skill_name and proficiency_level.
        """
        self.cursor.execute("""
            SELECT 
                sa.skill_name,
                ps.proficiency_level,
                ps.years_experience
            FROM skill_aliases sa
            INNER JOIN profile_skills ps ON sa.skill_id = ps.skill_id
            INNER JOIN profiles p ON ps.profile_id = p.profile_id
            WHERE p.user_id = %s
            ORDER BY 
                ps.proficiency_level DESC,
                ps.years_experience DESC NULLS LAST,
                sa.skill_name
        """, (self.user_id,))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_top_skills(self, count: int = 10) -> List[str]:
        """
        Get top N skills by proficiency and experience.
        
        Useful for generating focused search queries.
        """
        self.cursor.execute("""
            SELECT sa.skill_name
            FROM skill_aliases sa
            INNER JOIN profile_skills ps ON sa.skill_id = ps.skill_id
            INNER JOIN profiles p ON ps.profile_id = p.profile_id
            WHERE p.user_id = %s
            ORDER BY 
                ps.proficiency_level DESC,
                ps.years_experience DESC NULLS LAST,
                sa.skill_name
            LIMIT %s
        """, (self.user_id, count))
        
        results = self.cursor.fetchall()
        return [row['skill_name'] for row in results]
    
    def get_skill_categories(self) -> Dict[str, List[str]]:
        """
        Group skills by category (if taxonomy table exists).
        
        Returns dict: {category_name: [skill1, skill2, ...]}
        """
        # Check if skill categories exist in your schema
        # This is a placeholder - adjust based on your actual schema
        self.cursor.execute("""
            SELECT 
                COALESCE(st.category_name, 'Uncategorized') as category,
                sa.skill_name
            FROM skill_aliases sa
            INNER JOIN profile_skills ps ON sa.skill_id = ps.skill_id
            INNER JOIN profiles p ON ps.profile_id = p.profile_id
            LEFT JOIN skills_taxonomy st ON sa.skill_id = st.skill_id
            WHERE p.user_id = %s
            ORDER BY category, sa.skill_name
        """, (self.user_id,))
        
        results = self.cursor.fetchall()
        
        categories = {}
        for row in results:
            category = row['category']
            skill = row['skill_name']
            
            if category not in categories:
                categories[category] = []
            
            categories[category].append(skill)
        
        return categories
    
    def format_for_search_query(self, skills: List[str], max_skills: int = 5) -> str:
        """
        Format skills as comma-separated string for search query.
        
        Example: "Python, PostgreSQL, Django, AI, Machine Learning"
        """
        return ", ".join(skills[:max_skills])


def main():
    parser = argparse.ArgumentParser(
        description='Extract user skills for job search query generation'
    )
    parser.add_argument(
        '--user-id',
        type=int,
        required=True,
        help='User ID to extract skills for'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of skills returned (default: all)'
    )
    parser.add_argument(
        '--top',
        type=int,
        default=None,
        help='Get top N skills by proficiency (overrides --limit)'
    )
    parser.add_argument(
        '--format',
        choices=['list', 'json', 'search', 'detailed'],
        default='list',
        help='Output format: list (default), json, search (comma-separated), detailed (with proficiency)'
    )
    parser.add_argument(
        '--categories',
        action='store_true',
        help='Group skills by category'
    )
    
    args = parser.parse_args()
    
    # Extract skills
    with UserSkillExtractor(args.user_id) as extractor:
        # Get user info
        user = extractor.get_user_info()
        
        if not user:
            print(f"Error: User {args.user_id} not found", file=sys.stderr)
            sys.exit(1)
        
        print(f"User: {user['full_name']} ({user['email']})")
        print(f"User ID: {user['user_id']}")
        print("=" * 80)
        print()
        
        # Get skills based on arguments
        if args.categories:
            categories = extractor.get_skill_categories()
            
            if args.format == 'json':
                print(json.dumps(categories, indent=2))
            else:
                for category, skills in categories.items():
                    print(f"{category}:")
                    for skill in skills:
                        print(f"  - {skill}")
                    print()
        
        elif args.format == 'detailed':
            skills_detailed = extractor.get_skills_with_proficiency()
            
            print(f"Total Skills: {len(skills_detailed)}")
            print()
            
            for skill in skills_detailed:
                proficiency = skill['proficiency_level'] or 'N/A'
                years = skill['years_experience'] or 'N/A'
                print(f"  {skill['skill_name']:<40} Proficiency: {proficiency:<15} Years: {years}")
        
        else:
            # Get skills
            if args.top:
                skills = extractor.get_top_skills(args.top)
                print(f"Top {args.top} Skills (by proficiency):")
            else:
                skills = extractor.get_skills(args.limit)
                skill_count = args.limit if args.limit else len(skills)
                print(f"All Skills ({len(skills)} total):")
            
            print()
            
            # Format output
            if args.format == 'json':
                print(json.dumps(skills, indent=2))
            
            elif args.format == 'search':
                search_string = extractor.format_for_search_query(skills, max_skills=10)
                print(search_string)
            
            else:  # list format
                for i, skill in enumerate(skills, 1):
                    print(f"{i:3}. {skill}")
                
                print()
                print("=" * 80)
                print(f"Total: {len(skills)} skills")
                
                # Show search query preview
                if len(skills) > 0:
                    print()
                    print("Search Query Preview (top 5):")
                    print(f'  "{extractor.format_for_search_query(skills, max_skills=5)}"')


if __name__ == '__main__':
    main()
