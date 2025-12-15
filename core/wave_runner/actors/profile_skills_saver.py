#!/usr/bin/env python3
"""
Profile Skills Saver
Saves extracted skills from candidate profiles to profile_skills table.
Parallel to posting_skills_saver.py but for profiles.

Created: 2025-12-04
"""

import sys
import json
sys.path.insert(0, '/home/xai/Documents/ty_wave')

from core.wave_runner.script_actor_template import ScriptActorBase


class ProfileSkillsSaver(ScriptActorBase):
    """Save extracted skills to profile_skills table"""
    
    def _extract_skills_from_response(self, response):
        """Extract skills array from LLM response text."""
        import re
        
        # Strip markdown code fences if present
        if response.startswith('```json'):
            response = response[7:]
        if response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()
        
        # Try direct JSON parse
        try:
            parsed = json.loads(response)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON array in response
        match = re.search(r'\[[\s\S]*?\]', response)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        
        return []
    
    def process(self):
        """
        Save extracted skills to profile_skills table.
        
        Expected input:
        {
            "profile_id": 1,
            "workflow_run_id": 99,
            "interaction_id": 888,
            "skills": [...]  # Optional: pass skills directly
        }
        
        Skills format (from LLM extraction):
        [
            {"skill": "Python", "proficiency": "expert", "years_experience": 5, "context": "Used in 3 positions"},
            ...
        ]
        
        Returns:
        {
            "status": "success",
            "skills_saved": 15,
            "skills_matched": 10,
            "skills_unmatched": 5,
            "profile_id": 1
        }
        """
        profile_id = self.input_data.get('profile_id')
        workflow_run_id = self.input_data.get('workflow_run_id')
        skills_input = self.input_data.get('skills')
        
        # Try to get profile_id from workflow_run metadata if not in direct input
        if not profile_id and workflow_run_id:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT metadata->>'profile_id' as profile_id 
                FROM workflow_runs 
                WHERE workflow_run_id = %s
            """, (workflow_run_id,))
            row = cursor.fetchone()
            if row and row['profile_id']:
                profile_id = int(row['profile_id'])
            cursor.close()
        
        # Still no profile_id? Try the parent interaction chain
        if not profile_id:
            parent_input = self.query_previous_interaction(canonical_name='w1122_profile_summary')
            if parent_input:
                profile_id = parent_input.get('profile_id')
        
        if not profile_id:
            return {
                "status": "error",
                "error": "Missing profile_id"
            }
        
        # Get skills from input or query previous interaction
        skills_data = []
        
        if skills_input:
            # Skills passed directly
            if isinstance(skills_input, str):
                try:
                    skills_data = json.loads(skills_input)
                except json.JSONDecodeError:
                    skills_data = [s.strip() for s in skills_input.split(',') if s.strip()]
            else:
                skills_data = skills_input
        else:
            # Query from previous interaction (skill extraction step)
            # Use canonical_name to find the profile skill extraction conversation
            skills_output = self.query_previous_interaction(canonical_name='w1122_skill_extraction')
            if skills_output and 'response' in skills_output:
                response = skills_output['response']
                # Strip markdown code fences if present
                if response.startswith('```json'):
                    response = response[7:]
                if response.startswith('```'):
                    response = response[3:]
                if response.endswith('```'):
                    response = response[:-3]
                response = response.strip()
                
                try:
                    parsed = json.loads(response)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        skills_data = parsed
                except json.JSONDecodeError:
                    pass
            
            # Try WF1125 synthesizer
            if not skills_data:
                synth_output = self.query_previous_interaction(canonical_name='wf1125_synthesizer')
                if synth_output and 'response' in synth_output:
                    skills_data = self._extract_skills_from_response(synth_output['response'])
            
            # Try WF1125 direct expert outputs if synthesizer didn't work
            if not skills_data:
                all_skills = []
                for canonical in ['wf1125_tech_extract', 'wf1125_tech_review', 
                                 'wf1125_domain_expert', 'wf1125_leadership',
                                 'wf1125_creative', 'wf1125_business']:
                    expert_output = self.query_previous_interaction(canonical_name=canonical)
                    if expert_output and 'response' in expert_output:
                        expert_skills = self._extract_skills_from_response(expert_output['response'])
                        all_skills.extend(expert_skills)
                if all_skills:
                    skills_data = all_skills
            
            # Fallback: try conversation IDs that might have skill extraction
            if not skills_data:
                for conv_id in [9205, 9214, 3350, 3351, 9121]:  # 9214 is WF1125 synthesizer
                    skills_output = self.query_previous_interaction(conversation_id=conv_id)
                    if skills_output and 'response' in skills_output:
                        try:
                            parsed = json.loads(skills_output['response'])
                            if isinstance(parsed, list) and len(parsed) > 0:
                                skills_data = parsed
                                break
                        except json.JSONDecodeError:
                            continue
        
        if not skills_data:
            return {
                "status": "error",
                "error": "No skills found in input or previous interactions"
            }
        
        cursor = self.db_conn.cursor()
        skills_saved = 0
        skills_matched = 0
        skills_unmatched = 0
        skill_details = []
        
        try:
            for skill_item in skills_data:
                # Handle both dict and string formats
                if isinstance(skill_item, dict):
                    skill_name = skill_item.get('skill', skill_item.get('name', ''))
                    proficiency = skill_item.get('proficiency')
                    years_experience = skill_item.get('years_experience', skill_item.get('years'))
                    context = skill_item.get('context', skill_item.get('evidence_text', ''))
                else:
                    skill_name = str(skill_item).strip()
                    proficiency = None
                    years_experience = None
                    context = None
                
                if not skill_name:
                    continue
                
                # Validate proficiency level
                valid_proficiencies = ['expert', 'advanced', 'intermediate', 'beginner']
                if proficiency and proficiency.lower() not in valid_proficiencies:
                    proficiency = None
                elif proficiency:
                    proficiency = proficiency.lower()
                
                # Look up entity_id from entities (via canonical_name or alias)
                cursor.execute("""
                    SELECT e.entity_id FROM entities e
                    WHERE e.entity_type = 'skill' 
                      AND e.status = 'active'
                      AND (
                          LOWER(e.canonical_name) = LOWER(%s)
                          OR EXISTS (
                              SELECT 1 FROM entity_aliases ea 
                              WHERE ea.entity_id = e.entity_id 
                                AND LOWER(ea.alias) = LOWER(%s)
                          )
                          OR EXISTS (
                              SELECT 1 FROM entity_names en
                              WHERE en.entity_id = e.entity_id
                                AND LOWER(en.display_name) = LOWER(%s)
                          )
                      )
                    LIMIT 1
                """, (skill_name, skill_name, skill_name))
                
                result = cursor.fetchone()
                entity_id = None
                
                if result:
                    entity_id = result[0] if isinstance(result, tuple) else result['entity_id']
                    skills_matched += 1
                else:
                    skills_unmatched += 1
                    # Queue unmatched skill for Entity Registry review (WF3005)
                    # This is critical: experts extract freely, registry grows to capture!
                    try:
                        cursor.execute("""
                            INSERT INTO entities_pending (
                                entity_type,
                                raw_value,
                                source_context,
                                status
                            ) VALUES ('skill', %s, %s::jsonb, 'pending')
                            ON CONFLICT (entity_type, raw_value) DO NOTHING
                        """, (
                            skill_name,
                            json.dumps({
                                "source": "profile_skills",
                                "profile_id": profile_id,
                                "workflow_run_id": workflow_run_id
                            })
                        ))
                    except Exception as e:
                        # Don't fail on pending insert - log and continue
                        pass
                    
                    skill_details.append({
                        "skill": skill_name,
                        "status": "unmatched_queued",
                        "proficiency": proficiency
                    })
                    continue
                
                # Insert into profile_skills
                cursor.execute("""
                    INSERT INTO profile_skills (
                        profile_id,
                        entity_id,
                        proficiency_level,
                        years_experience,
                        evidence_text,
                        extracted_by,
                        recipe_run_id,
                        created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (profile_id, entity_id) 
                    WHERE entity_id IS NOT NULL
                    DO UPDATE SET
                        proficiency_level = COALESCE(EXCLUDED.proficiency_level, profile_skills.proficiency_level),
                        years_experience = COALESCE(EXCLUDED.years_experience, profile_skills.years_experience),
                        evidence_text = COALESCE(EXCLUDED.evidence_text, profile_skills.evidence_text)
                """, (
                    profile_id,
                    entity_id,
                    proficiency,
                    years_experience,
                    context,
                    f'workflow_{workflow_run_id}' if workflow_run_id else 'direct',
                    workflow_run_id
                ))
                
                skills_saved += 1
                skill_details.append({
                    "skill": skill_name,
                    "entity_id": entity_id,
                    "status": "saved",
                    "proficiency": proficiency,
                    "years": years_experience
                })
            
            # Update profile extraction status
            cursor.execute("""
                UPDATE profiles 
                SET skills_extraction_status = 'success',
                    updated_at = NOW()
                WHERE profile_id = %s
            """, (profile_id,))
            
            self.db_conn.commit()
            
            return {
                "status": "success",
                "profile_id": profile_id,
                "skills_saved": skills_saved,
                "skills_matched": skills_matched,
                "skills_unmatched": skills_unmatched,
                "skill_details": skill_details[:10]  # First 10 for preview
            }
            
        except Exception as e:
            self.db_conn.rollback()
            import traceback
            return {
                "status": "error",
                "error": str(e) if str(e) else repr(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }


if __name__ == '__main__':
    actor = ProfileSkillsSaver()
    actor.run()
