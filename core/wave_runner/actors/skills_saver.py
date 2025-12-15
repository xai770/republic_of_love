#!/usr/bin/env python3
"""
Skills Saver
Saves extracted skills to profile_skills table.
Queries previous interaction for skill extraction output.
"""

import sys
sys.path.insert(0, '/home/xai/Documents/ty_wave')

from core.wave_runner.script_actor_template import ScriptActorBase


class SkillsSaver(ScriptActorBase):
    """Save extracted skills to profile_skills table"""
    
    def process(self):
        """
        Query skill extraction output and save to profile_skills.
        
        Expected input:
        {
            "posting_id": 12345,
            "workflow_run_id": 99,
            "interaction_id": 888
        }
        
        Returns:
        {
            "status": "success",
            "skills_saved": 15,
            "posting_id": 12345
        }
        """
        posting_id = self.input_data.get('posting_id')
        workflow_run_id = self.input_data.get('workflow_run_id')
        interaction_id = self.input_data.get('interaction_id')
        
        if not posting_id or not workflow_run_id:
            return {
                "status": "error",
                "error": "Missing posting_id or workflow_run_id"
            }
        
        # Query previous interaction output (taxonomy_skill_extraction - conversation_id 12)
        skills_output = self.query_previous_interaction(conversation_id=12)
        
        if not skills_output:
            return {
                "status": "error",
                "error": "No skills from extraction step"
            }
        
        # Extract skills from AI output
        # Expected: {"response": "Python, JavaScript, SQL, ...", "skills": ["Python", "JavaScript"]}
        skills_list = skills_output.get('skills', [])
        
        if not skills_list and 'response' in skills_output:
            # Parse from response text
            response = skills_output['response']
            # Simple parsing - split by comma
            skills_list = [s.strip() for s in response.split(',') if s.strip()]
        
        if not skills_list:
            return {
                "status": "error",
                "error": "No skills found in extraction output"
            }
        
        cursor = self.db_conn.cursor()
        skills_saved = 0
        
        try:
            for skill_name in skills_list:
                # Insert or update skill
                cursor.execute("""
                    INSERT INTO profile_skills (
                        posting_id,
                        skill_name,
                        created_by_interaction_id,
                        created_at
                    ) VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (posting_id, skill_name) DO NOTHING
                """, (posting_id, skill_name, interaction_id))
                
                if cursor.rowcount > 0:
                    skills_saved += 1
            
            self.db_conn.commit()
            
            return {
                "status": "success",
                "skills_saved": skills_saved,
                "posting_id": posting_id
            }
            
        except Exception as e:
            self.db_conn.rollback()
            return {
                "status": "error",
                "error": str(e)
            }


if __name__ == '__main__':
    actor = SkillsSaver()
    actor.run()
