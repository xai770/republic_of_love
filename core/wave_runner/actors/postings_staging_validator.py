#!/usr/bin/env python3
"""
Postings Staging Validator
Validates and promotes staging records to production postings table.
Centralized validation prevents script actors from corrupting production.
"""

import sys
sys.path.insert(0, '/home/xai/Documents/ty_learn')

from core.wave_runner.script_actor_template import ScriptActorBase


class PostingsStagingValidator(ScriptActorBase):
    """Validate and promote postings from staging to production"""
    
    def process(self):
        """
        Validate staging records and promote to production.
        
        Expected input:
        {
            "staging_ids": [101, 102, 103],  # From db_job_fetcher output
            "workflow_run_id": 99,
            "interaction_id": 888
        }
        
        Returns:
        {
            "validated": 3,
            "promoted": 2,
            "rejected": 1,
            "posting_ids": [4720, 4721]
        }
        """
        staging_ids = self.input_data.get('staging_ids', [])
        interaction_id = self.input_data.get('interaction_id')
        
        if not staging_ids:
            # Query staging records from previous interaction (db_job_fetcher)
            fetcher_output = self.query_previous_interaction(conversation_id=1)
            if fetcher_output:
                staging_ids = fetcher_output.get('staging_ids', [])
        
        if not staging_ids:
            return {
                "validated": 0,
                "promoted": 0,
                "rejected": 0,
                "error": "No staging records to validate"
            }
        
        cursor = self.db_conn.cursor()
        validated = 0
        promoted = 0
        rejected = 0
        posting_ids = []
        
        for staging_id in staging_ids:
            # Get staging record
            cursor.execute("""
                SELECT * FROM postings_staging
                WHERE staging_id = %s
            """, (staging_id,))
            
            staging = cursor.fetchone()
            if not staging:
                continue
            
            # Validate
            validation_errors = self._validate_staging(staging)
            
            if validation_errors:
                # Mark as failed
                cursor.execute("""
                    UPDATE postings_staging
                    SET validation_status = 'failed',
                        validation_errors = %s::jsonb,
                        validated_at = NOW(),
                        validated_by_actor_id = 1
                    WHERE staging_id = %s
                """, ('{"errors": ' + str(validation_errors) + '}', staging_id))
                rejected += 1
            else:
                # Mark as passed
                cursor.execute("""
                    UPDATE postings_staging
                    SET validation_status = 'passed',
                        validated_at = NOW(),
                        validated_by_actor_id = 1
                    WHERE staging_id = %s
                """, (staging_id,))
                validated += 1
                
                # Promote to production
                posting_id = self._promote_to_production(staging, interaction_id, cursor)
                if posting_id:
                    promoted += 1
                    posting_ids.append(posting_id)
        
        self.db_conn.commit()
        
        return {
            "validated": validated,
            "promoted": promoted,
            "rejected": rejected,
            "posting_ids": posting_ids
        }
    
    def _validate_staging(self, staging):
        """Validate staging record - returns list of errors or empty list"""
        errors = []
        
        # Required fields
        if not staging.get('job_title'):
            errors.append("job_title is required")
        
        # Optional: Check URL uniqueness
        if staging.get('posting_url'):
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM postings
                WHERE external_url = %s
            """, (staging['posting_url'],))
            
            if cursor.fetchone()['count'] > 0:
                errors.append("posting_url already exists in production")
        
        return errors
    
    def _promote_to_production(self, staging, interaction_id, cursor):
        """Promote staging record to production postings table"""
        try:
            import json
            
            # Convert raw_data to JSON string if it's a dict
            raw_data = staging.get('raw_data', {})
            if isinstance(raw_data, str):
                raw_data = json.loads(raw_data)
            
            # Extract external_id from raw_data (DB job ID like "R0412770")
            external_job_id = raw_data.get('external_id')
            if not external_job_id:
                # Fallback: extract from external_path if available
                external_path = raw_data.get('external_path', '')
                if external_path and '_R' in external_path:
                    # Extract job ID from path like "/job/.../Job-Title_R0412770"
                    external_job_id = external_path.split('_R')[-1] if '_R' in external_path else None
                    if external_job_id:
                        external_job_id = 'R' + external_job_id
            
            # Build posting_position_uri (unique identifier for the posting)
            posting_position_uri = external_job_id  # Use DB job ID as position URI
            
            raw_data_json = json.dumps(raw_data) if raw_data else '{}'
            
            # Get the staging_id for lineage
            staging_id = staging.get('staging_id') or staging['staging_id']
            # Get the interaction_id that created this staging record (from staging table)
            source_interaction_id = staging.get('interaction_id') or interaction_id
            
            cursor.execute("""
                INSERT INTO postings (
                    posting_name,
                    job_title,
                    job_description,
                    location_city,
                    external_url,
                    external_job_id,
                    posting_position_uri,
                    source_metadata,
                    fetched_at,
                    posting_status,
                    source,
                    created_by_interaction_id,
                    created_by_staging_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s::jsonb, NOW(), 'active', 'db',
                    %s, %s
                ) RETURNING posting_id
            """, (
                staging.get('job_title', 'Unknown'),
                staging.get('job_title'),
                staging.get('job_description'),
                staging.get('location'),
                staging.get('posting_url'),
                external_job_id,  # Use extracted DB job ID
                posting_position_uri,  # Same as external_job_id for DB jobs
                raw_data_json,
                source_interaction_id,  # ✅ Link to source interaction
                staging_id              # ✅ Link to staging record
            ))
            
            posting_id = cursor.fetchone()['posting_id']
            
            # Update staging record
            cursor.execute("""
                UPDATE postings_staging
                SET promoted_to_posting_id = %s,
                    promoted_at = NOW(),
                    validation_status = 'promoted'
                WHERE staging_id = %s
            """, (posting_id, staging['staging_id']))
            
            return posting_id
            
        except Exception as e:
            # Promotion failed - mark as failed
            cursor.execute("""
                UPDATE postings_staging
                SET validation_status = 'failed',
                    validation_errors = %s::jsonb
                WHERE staging_id = %s
            """, ('{"error": "' + str(e) + '"}', staging['staging_id']))
            return None


if __name__ == '__main__':
    actor = PostingsStagingValidator()
    actor.run()
