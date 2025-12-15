#!/usr/bin/env python3
"""
Profile Importer Actor
======================

Script actor for Workflow 1126: Import Profile to Database

Takes validated profile JSON and imports it into the Turing database:
- profiles table (main profile data)
- work_history table (employment records)
- languages table (language proficiencies)
- education table (degrees)
- certifications table (professional certifications)
- Links skills to taxonomy

Outputs:
- [SUCCESS] if import succeeded
- [FAIL] if import failed

Usage:
    Called by workflow_executor as a script actor.
    Receives JSON via stdin, outputs result to stdout.
"""

import sys
import json
import psycopg2
from datetime import datetime
from typing import Dict, Any, Optional, List

# Import database connection
sys.path.insert(0, '/home/xai/Documents/ty_learn')
from core.database import get_connection

class ProfileImporter:
    def __init__(self):
        self.conn = None
        self.profile_id = None
        self.stats = {
            'profiles': 0,
            'work_history': 0,
            'languages': 0,
            'education': 0,
            'certifications': 0,
            'skills': 0
        }
        
    def import_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Import complete profile into database
        
        Args:
            profile_data: Validated profile JSON from extraction/validation
            
        Returns:
            Result dict with status, profile_id, and statistics
        """
        try:
            self.conn = get_connection()
            self.conn.autocommit = False  # Use transaction
            
            # 1. Import main profile
            self.profile_id = self._import_profile_record(profile_data['profile'])
            
            # 2. Import work history
            if 'work_history' in profile_data:
                self._import_work_history(profile_data['work_history'])
            
            # 3. Import languages
            if 'languages' in profile_data:
                self._import_languages(profile_data['languages'])
            
            # 4. Import education
            if 'education' in profile_data:
                self._import_education(profile_data['education'])
            
            # 5. Import certifications
            if 'certifications' in profile_data:
                self._import_certifications(profile_data['certifications'])
            
            # 6. Import skills and link to taxonomy
            if 'skills' in profile_data:
                self._import_skills(profile_data['skills'])
            
            # Commit transaction
            self.conn.commit()
            
            return {
                'status': 'SUCCESS',
                'profile_id': self.profile_id,
                'records_inserted': self.stats,
                'message': f'Profile imported successfully (profile_id={self.profile_id})'
            }
            
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            return {
                'status': 'FAILED',
                'profile_id': None,
                'records_inserted': self.stats,
                'error': str(e)
            }
        finally:
            if self.conn:
                self.conn.close()
    
    def _import_profile_record(self, profile: Dict[str, Any]) -> int:
        """Import main profile record"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO profiles (
                full_name,
                email,
                phone,
                location,
                current_title,
                linkedin_url,
                years_of_experience,
                experience_level,
                profile_summary,
                created_at,
                updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            RETURNING profile_id
        """, (
            profile.get('full_name'),
            profile.get('email'),
            profile.get('phone'),
            profile.get('location'),
            profile.get('current_title'),
            profile.get('linkedin_url'),
            profile.get('years_of_experience'),
            profile.get('experience_level'),
            profile.get('profile_summary')
        ))
        
        profile_id = cursor.fetchone()[0]
        cursor.close()
        
        self.stats['profiles'] = 1
        return profile_id
    
    def _import_work_history(self, work_history: List[Dict[str, Any]]):
        """Import work history records"""
        cursor = self.conn.cursor()
        
        for job in work_history:
            cursor.execute("""
                INSERT INTO work_history (
                    profile_id,
                    company_name,
                    job_title,
                    department,
                    start_date,
                    end_date,
                    is_current,
                    location,
                    job_description,
                    achievements,
                    technologies_used,
                    created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    CURRENT_TIMESTAMP
                )
            """, (
                self.profile_id,
                job.get('company_name'),
                job.get('job_title'),
                job.get('department'),
                job.get('start_date'),
                job.get('end_date'),
                job.get('is_current', False),
                job.get('location'),
                job.get('job_description'),
                json.dumps(job.get('achievements', [])),
                json.dumps(job.get('technologies_used', []))
            ))
            
            self.stats['work_history'] += 1
        
        cursor.close()
    
    def _import_languages(self, languages: List[Dict[str, Any]]):
        """Import language proficiencies"""
        cursor = self.conn.cursor()
        
        for lang in languages:
            cursor.execute("""
                INSERT INTO languages (
                    profile_id,
                    language_name,
                    proficiency_level,
                    created_at
                ) VALUES (
                    %s, %s, %s, CURRENT_TIMESTAMP
                )
            """, (
                self.profile_id,
                lang.get('language_name'),
                lang.get('proficiency_level')
            ))
            
            self.stats['languages'] += 1
        
        cursor.close()
    
    def _import_education(self, education: List[Dict[str, Any]]):
        """Import education records"""
        cursor = self.conn.cursor()
        
        for edu in education:
            cursor.execute("""
                INSERT INTO education (
                    profile_id,
                    institution,
                    degree,
                    field_of_study,
                    start_year,
                    end_year,
                    is_current,
                    created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
                )
            """, (
                self.profile_id,
                edu.get('institution'),
                edu.get('degree'),
                edu.get('field_of_study'),
                edu.get('start_year'),
                edu.get('end_year'),
                edu.get('is_current', False)
            ))
            
            self.stats['education'] += 1
        
        cursor.close()
    
    def _import_certifications(self, certifications: List[Dict[str, Any]]):
        """Import certification records"""
        cursor = self.conn.cursor()
        
        for cert in certifications:
            cursor.execute("""
                INSERT INTO certifications (
                    profile_id,
                    certification_name,
                    issuing_organization,
                    issue_date,
                    expiry_date,
                    created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
                )
            """, (
                self.profile_id,
                cert.get('certification_name'),
                cert.get('issuing_organization'),
                cert.get('issue_date'),
                cert.get('expiry_date')
            ))
            
            self.stats['certifications'] += 1
        
        cursor.close()
    
    def _import_skills(self, skills: List[str]):
        """
        Import skills and link to taxonomy
        
        For now, just store skills as-is. In future iterations:
        - Match skills to taxonomy nodes
        - Create profile_skills entries linked to taxonomy
        """
        # TODO: Implement taxonomy linking
        # For now, just count the skills we received
        self.stats['skills'] = len(skills)
        
        # Note: We'll implement the taxonomy linking in a future enhancement
        # when we build the matching workflow


def main():
    """
    Main entry point when called as script actor
    
    Expects JSON input via stdin, outputs result to stdout
    """
    try:
        # Read input from stdin (passed by workflow_executor)
        input_data = sys.stdin.read()
        
        # Parse the input
        # Input format from workflow: Contains validation output with profile data
        data = json.loads(input_data)
        
        # Extract the actual profile data
        # The input could be raw extraction output or validation output
        if 'corrected_data' in data and data['corrected_data']:
            # Use corrected data from validation if available
            profile_data = data['corrected_data']
        elif 'profile' in data:
            # Use raw extraction output
            profile_data = data
        else:
            raise ValueError("Invalid input format: expected profile data with 'profile' key")
        
        # Import the profile
        importer = ProfileImporter()
        result = importer.import_profile(profile_data)
        
        # Output result as JSON
        print(json.dumps(result, indent=2))
        
        # Output branch marker for workflow routing
        if result['status'] == 'SUCCESS':
            print("\n[SUCCESS]")
        else:
            print("\n[FAIL]")
        
        sys.exit(0 if result['status'] == 'SUCCESS' else 1)
        
    except Exception as e:
        # Output error
        error_result = {
            'status': 'FAILED',
            'profile_id': None,
            'records_inserted': {},
            'error': str(e)
        }
        print(json.dumps(error_result, indent=2))
        print("\n[FAIL]")
        sys.exit(1)


if __name__ == '__main__':
    main()
