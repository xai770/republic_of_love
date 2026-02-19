#!/usr/bin/env python3
"""
Posting Skills Saver
Saves extracted skills from job postings to posting_skills table AND postings.skill_keywords.
Queries previous interaction for skill extraction output.

Updated: 2025-11-30 - Now handles rich JSON format with importance, weight, proficiency, etc.
Updated: 2025-12-08 - Uses shared SkillResolver for entity lookup + pending queue
"""

import sys
import json
sys.path.insert(0, '/home/xai/Documents/ty_learn')

from core.wave_runner.script_actor_template import ScriptActorBase
from core.wave_runner.actors.entity_skill_resolver import SkillResolver


class PostingSkillsSaver(ScriptActorBase):
    """Save extracted skills to posting_skills table and postings.skill_keywords"""
    
    def process(self):
        """
        Query skill extraction output and save to posting_skills + postings.
        
        Expected input:
        {
            "posting_id": 12345,
            "workflow_run_id": 99,
            "interaction_id": 888
        }
        
        New rich format from conversation 9121:
        [
            {"skill": "Python", "importance": "essential", "weight": 95, "proficiency": "expert", "years_required": 5, "reasoning": "Core requirement"},
            ...
        ]
        
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
        
        # Query previous interaction output - now conversation 9121 (Hybrid Job Skills Extraction)
        skills_output = self.query_previous_interaction(conversation_id=9121)
        
        if not skills_output:
            # Fallback to old conversation 3350 for backwards compatibility
            skills_output = self.query_previous_interaction(conversation_id=3350)
        
        if not skills_output:
            return {
                "status": "error",
                "error": "No skills from extraction step"
            }
        
        # Extract skills from AI output
        skills_data = []  # List of skill dicts (rich format) or strings (legacy)
        
        if 'response' in skills_output:
            response = skills_output['response']
            try:
                parsed = json.loads(response)
                if isinstance(parsed, list):
                    skills_data = parsed
            except json.JSONDecodeError:
                # Fallback: parse as comma-separated strings
                skills_data = [s.strip() for s in response.split(',') if s.strip()]
        
        if not skills_data:
            return {
                "status": "error",
                "error": f"No skills found in extraction output. Got: {skills_output}"
            }
        
        cursor = self.db_conn.cursor()
        skills_saved = 0
        skill_ids = []
        skill_keywords_rich = []  # Rich format with all metadata
        
        # Use shared resolver for entity lookup + pending queue
        resolver = SkillResolver(self.db_conn)
        source_context = {"posting_id": posting_id, "workflow_run_id": workflow_run_id}
        
        try:
            for skill_item in skills_data:
                # Handle both rich format (dict) and legacy format (string)
                if isinstance(skill_item, dict):
                    skill_name = skill_item.get('skill', '')
                    importance = skill_item.get('importance')
                    weight = skill_item.get('weight')
                    proficiency = skill_item.get('proficiency')
                    years_required = skill_item.get('years_required')
                    reasoning = skill_item.get('reasoning')
                else:
                    # Legacy: just a string
                    skill_name = str(skill_item)
                    importance = None
                    weight = None
                    proficiency = None
                    years_required = None
                    reasoning = None
                
                if not skill_name:
                    continue
                
                # Build rich skill entry for skill_keywords JSONB
                skill_entry = {"name": skill_name}
                if importance:
                    skill_entry["importance"] = importance
                if weight is not None:
                    skill_entry["weight"] = weight
                if proficiency:
                    skill_entry["proficiency"] = proficiency
                if years_required is not None:
                    skill_entry["years_required"] = years_required
                if reasoning:
                    skill_entry["reasoning"] = reasoning
                skill_keywords_rich.append(skill_entry)
                
                # Use shared resolver - returns entity_id or None (and queues to entities_pending)
                entity_id = resolver.resolve(skill_name, source_context)
                
                if entity_id:
                    skill_ids.append(entity_id)
                
                # ALWAYS save the skill - even if not in taxonomy
                # Use raw_skill_name to preserve the extracted skill name
                if entity_id:
                    # Taxonomy skill - use conflict on (posting_id, entity_id)
                    cursor.execute("""
                        INSERT INTO posting_skills (
                            posting_id,
                            entity_id,
                            raw_skill_name,
                            importance,
                            weight,
                            proficiency,
                            years_required,
                            reasoning,
                            extracted_by,
                            recipe_run_id,
                            created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (posting_id, entity_id) 
                        WHERE entity_id IS NOT NULL
                        DO UPDATE SET
                            raw_skill_name = EXCLUDED.raw_skill_name,
                            importance = EXCLUDED.importance,
                            weight = EXCLUDED.weight,
                            proficiency = EXCLUDED.proficiency,
                            years_required = EXCLUDED.years_required,
                            reasoning = EXCLUDED.reasoning,
                            updated_at = NOW()
                    """, (
                        posting_id, 
                        entity_id,
                        skill_name,
                        importance,
                        weight,
                        proficiency,
                        years_required,
                        reasoning,
                        f'workflow_{workflow_run_id}',
                        workflow_run_id
                    ))
                else:
                    # Non-taxonomy skill - resolver already queued to entities_pending
                    # Check for existing then insert/update in posting_skills
                    cursor.execute("""
                        SELECT posting_skill_id FROM posting_skills
                        WHERE posting_id = %s AND entity_id IS NULL AND LOWER(raw_skill_name) = LOWER(%s)
                    """, (posting_id, skill_name))
                    
                    existing = cursor.fetchone()
                    if existing:
                        # Update existing
                        cursor.execute("""
                            UPDATE posting_skills SET
                                importance = %s,
                                weight = %s,
                                proficiency = %s,
                                years_required = %s,
                                reasoning = %s,
                                updated_at = NOW()
                            WHERE posting_skill_id = %s
                        """, (importance, weight, proficiency, years_required, reasoning, 
                              existing[0] if isinstance(existing, tuple) else existing['posting_skill_id']))
                    else:
                        # Insert new
                        cursor.execute("""
                            INSERT INTO posting_skills (
                                posting_id,
                                entity_id,
                                raw_skill_name,
                                importance,
                                weight,
                                proficiency,
                                years_required,
                                reasoning,
                                extracted_by,
                                recipe_run_id,
                                created_at
                            ) VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            posting_id, 
                            skill_name,
                            importance,
                            weight,
                            proficiency,
                            years_required,
                            reasoning,
                            f'workflow_{workflow_run_id}',
                            workflow_run_id
                        ))
                    
                    print(f"INFO: Skill '{skill_name}' queued to entities_pending (posting {posting_id})", file=sys.stderr)
                
                skills_saved += 1
            
            # Update postings.skill_keywords with rich skill data (name + metadata)
            cursor.execute("""
                UPDATE postings
                SET skill_keywords = %s::jsonb,
                    updated_at = NOW()
                WHERE posting_id = %s
            """, (json.dumps(skill_keywords_rich), posting_id))
            
            self.db_conn.commit()
            
            return {
                "status": "success",
                "skills_saved": skills_saved,
                "total_skills": len(skill_keywords_rich),
                "skill_ids": skill_ids,
                "posting_id": posting_id,
                "message": f"Saved {skills_saved}/{len(skill_keywords_rich)} skills to posting_skills, updated postings.skill_keywords with rich data"
            }
            
        except Exception as e:
            self.db_conn.rollback()
            return {
                "status": "error",
                "error": str(e),
                "posting_id": posting_id
            }


if __name__ == '__main__':
    actor = PostingSkillsSaver()
    actor.run()
