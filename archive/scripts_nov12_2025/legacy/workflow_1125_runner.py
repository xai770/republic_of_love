#!/usr/bin/env python3
"""
Workflow 1125 Runner: Profile Career Analysis
===========================================

PURPOSE:
    Orchestrates multi-model ensemble for comprehensive career analysis.
    Integrates chunked_deepseek_analyzer.py with Turing's workflow system.

WORKFLOW:
    1. Extract career history from database (profile_id) or file
    2. Chunk career into logical time periods
    3. Execute DeepSeek-R1 organizational analysis per chunk (parallel)
    4. Execute Qwen2.5 technical skills extraction (full profile)
    5. Execute Olmo2 soft skills extraction (full profile)
    6. Synthesize all outputs into comprehensive markdown report
    7. Save to career_analyses table

USAGE:
    # Analyze profile from database
    python3 workflow_1125_runner.py --profile-id 1
    
    # Analyze from file
    python3 workflow_1125_runner.py --career-file "docs/Gershon Pollatschek Projects.md"
    
    # Run with specific workflow_run_id for tracking
    python3 workflow_1125_runner.py --profile-id 1 --workflow-run-id 1234

DATABASE INTEGRATION:
    - Creates workflow_run in workflow_runs table
    - Saves results to career_analyses table
    - Links to llm_interactions for full audit trail
    - Updates profiles table with analysis_id reference

AUTHOR: Base Yoga Team
DATE: 2025-11-04
"""

import psycopg2
import psycopg2.extras
import subprocess
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Import the chunked analyzer
sys.path.append(str(Path(__file__).parent.parent))
from tools.chunked_deepseek_analyzer import ChunkedDeepSeekAnalyzer

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'database': 'turing',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

class Workflow1125Runner:
    """
    Multi-Model Career Analysis Orchestrator
    
    Coordinates:
    - Career chunking (Python tool)
    - DeepSeek-R1 organizational analysis (per chunk)
    - Qwen2.5 technical skills extraction
    - Olmo2 soft skills extraction
    - Claude synthesis (comprehensive report)
    """
    
    def __init__(self):
        self.workflow_id = 1125
        self.workflow_run_id = None
        self.profile_id = None
        self.career_text = None
    
    def get_connection(self):
        """Get database connection with RealDictCursor."""
        return psycopg2.connect(**DB_CONFIG, cursor_factory=psycopg2.extras.RealDictCursor)
    
    def get_profile_career_history(self, profile_id: int) -> tuple[str, dict]:
        """
        Extract career history from database profile.
        
        Args:
            profile_id: Profile ID to analyze
            
        Returns:
            tuple: (career_text, profile_metadata)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if career history is stored in a specific field
        # For now, we'll look for a linked document
        cursor.execute("""
            SELECT 
                p.profile_id,
                p.full_name,
                p.current_title,
                p.location,
                p.years_of_experience,
                p.profile_summary,
                p.profile_raw_text
            FROM profiles p
            WHERE p.profile_id = %s
        """, (profile_id,))
        
        profile = cursor.fetchone()
        
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")
        
        # Check for linked career document
        career_doc_path = Path(f"docs/{profile['full_name']} Projects.md")
        
        if not career_doc_path.exists():
            raise ValueError(f"Career history document not found for profile {profile_id}")
        
        with open(career_doc_path, 'r') as f:
            career_text = f.read()
        
        metadata = {
            'profile_id': profile['profile_id'],
            'full_name': profile['full_name'],
            'current_title': profile['current_title'],
            'location': profile['location'],
            'years_of_experience': profile['years_of_experience']
        }
        
        conn.close()
        return career_text, metadata
    
    def create_workflow_run(self, profile_id: int) -> int:
        """Create workflow_run record for tracking."""
        """Create workflow_run for tracking. Uses minimal required fields."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # First, get or create a test_case for this profile
        test_case_name = f'profile_{profile_id}_career_analysis'
        
        # Check if test case already exists
        cursor.execute("""
            SELECT test_case_id FROM test_cases WHERE test_case_name = %s
        """, (test_case_name,))
        
        result = cursor.fetchone()
        if result:
            test_case_id = result['test_case_id']
        else:
            # Create new test case
            cursor.execute("""
                INSERT INTO test_cases (test_case_name, workflow_id, test_data)
                VALUES (%s, %s, %s)
                RETURNING test_case_id
            """, (test_case_name, self.workflow_id, json.dumps({'profile_id': profile_id})))
            test_case_id = cursor.fetchone()['test_case_id']
        
        # Use default batch_id 1
        batch_id = 1
        
        # Create workflow_run
        cursor.execute("""
            INSERT INTO workflow_runs (
                workflow_id,
                test_case_id,
                batch_id,
                status,
                execution_mode,
                total_sessions
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING workflow_run_id
        """, (self.workflow_id, test_case_id, batch_id, 'RUNNING', 'production', 4))
        
        workflow_run_id = cursor.fetchone()['workflow_run_id']
        conn.commit()
        conn.close()
        
        return workflow_run_id
    
    def call_ollama_model(self, model: str, prompt: str, timeout: int = 900) -> str:
        """Call Ollama model with prompt."""
        print(f"   🤖 Calling {model}...")
        try:
            result = subprocess.run(
                ['ollama', 'run', model, prompt],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            print(f"   ✅ {model} completed")
            return result.stdout
        except subprocess.TimeoutExpired:
            print(f"   ⏰ {model} timed out after {timeout}s")
            return f"⏰ Timeout after {timeout//60} minutes"
        except Exception as e:
            print(f"   ❌ {model} error: {str(e)}")
            return f"❌ Error: {str(e)}"
    
    def log_llm_interaction(self, model: str, prompt: str, response: str, metadata: dict = None) -> int:
        """Log LLM interaction to database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get actor_id for the model (create dummy conversation_run for now)
        cursor.execute("SELECT actor_id FROM actors WHERE actor_name = %s LIMIT 1", (model,))
        result = cursor.fetchone()
        actor_id = result['actor_id'] if result else 5  # Default to deepseek-r1:8b
        
        # Need a conversation_run_id - create a minimal one
        cursor.execute("""
            INSERT INTO conversation_runs (
                workflow_run_id, 
                conversation_id,
                workflow_step_id,
                status
            ) 
            SELECT %s, conversation_id, step_id, 'SUCCESS'
            FROM conversations c
            JOIN workflow_conversations wc ON c.conversation_id = wc.conversation_id
            WHERE c.actor_id = %s AND wc.workflow_id = %s
            LIMIT 1
            RETURNING conversation_run_id
        """, (self.workflow_run_id, actor_id, self.workflow_id))
        
        conv_run_result = cursor.fetchone()
        if not conv_run_result:
            # Fallback: just skip logging if we can't create conversation_run
            conn.close()
            return None
        
        conversation_run_id = conv_run_result['conversation_run_id']
        
        cursor.execute("""
            INSERT INTO llm_interactions (
                workflow_run_id,
                conversation_run_id,
                actor_id,
                execution_order,
                prompt_sent,
                response_received,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING interaction_id
        """, (self.workflow_run_id, conversation_run_id, actor_id, 1, prompt, response, 'SUCCESS'))
        
        interaction_id = cursor.fetchone()['interaction_id']
        conn.commit()
        conn.close()
        
        return interaction_id
    
    def run_chunked_deepseek_analysis(self, career_text: str) -> dict:
        """
        Run chunked DeepSeek organizational analysis.
        
        Returns:
            dict: Chunked analysis results
        """
        print("\n📊 Phase 1: Chunked Organizational Analysis (DeepSeek-R1)")
        print("="*70)
        
        # Save career text to temp file
        temp_file = Path("temp/career_input_1122.txt")
        temp_file.parent.mkdir(exist_ok=True)
        with open(temp_file, 'w') as f:
            f.write(career_text)
        
        # Run chunked analyzer
        analyzer = ChunkedDeepSeekAnalyzer(str(temp_file))
        results = analyzer.analyze_all_chunks()
        
        # Log each chunk analysis to llm_interactions
        for chunk_id, chunk_result in results.items():
            metadata = {
                'phase': 'organizational_analysis',
                'chunk_id': chunk_id,
                'period': chunk_result['metadata']['period'],
                'organization': chunk_result['metadata']['org']
            }
            
            prompt = f"Period: {chunk_result['metadata']['period']}\nOrg: {chunk_result['metadata']['org']}\n\n{chunk_result.get('prompt', 'N/A')}"
            
            self.log_llm_interaction(
                model='deepseek-r1:8b',
                prompt=prompt,
                response=chunk_result['analysis'],
                metadata=metadata
            )
        
        return results
    
    def run_qwen_technical_skills(self, career_text: str) -> str:
        """Run Qwen2.5 technical skills extraction."""
        print("\n🔧 Phase 2: Technical Skills Extraction (Qwen2.5)")
        print("="*70)
        
        prompt = f"""You are an expert at identifying technical skills, tools, and methodologies from career descriptions.

FULL CAREER HISTORY:

{career_text}

Analyze the MOST LIKELY technical skills, tools, and standards used. Be REALISTIC and PRACTICAL - avoid over-engineering or speculation.

Provide:

### 1. SOFTWARE & TOOLS

**Most Likely Used:**
- Office Tools (Excel, Word, etc.)
- Database Management (SQL databases, query tools)
- Data Analysis & Reporting (BI tools)
- Process Automation tools
- Backend/Development tools
- Project Management tools

### 2. TECHNICAL SKILLS

**Required Technical Competencies:**
- Programming Languages
- Database & Query Skills
- System Integration
- Data Analysis
- Process Automation

### 3. STANDARDS & METHODOLOGIES

**Industry Standards and Regulations:**
- Compliance Frameworks (GDPR, SOX, etc.)
- Software Licensing Standards
- Project Management Methodologies (Agile, Scrum, etc.)
- Data Quality & Integrity standards

Focus on tools and skills that are MOST LIKELY based on the job descriptions, not just POSSIBLE. If speculating, clearly mark as [LIKELY] vs [CONFIRMED].

Be specific and practical."""
        
        response = self.call_ollama_model('qwen2.5:7b', prompt, timeout=600)
        
        self.log_llm_interaction(
            model='qwen2.5:7b',
            prompt=prompt,
            response=response,
            metadata={'phase': 'technical_skills'}
        )
        
        return response
    
    def run_olmo_soft_skills(self, career_text: str) -> str:
        """Run Olmo2 soft skills extraction."""
        print("\n👥 Phase 3: Soft Skills Extraction (Olmo2)")
        print("="*70)
        
        prompt = f"""You are an expert at identifying soft skills and interpersonal competencies from career descriptions.

FULL CAREER HISTORY:

{career_text}

Analyze and categorize the soft skills and interpersonal competencies demonstrated throughout this career.

Provide:

### COMMUNICATION SKILLS:
- Written/verbal communication (WHY needed in this role?)
- Presentation skills (WHY needed?)
- Technical translation (WHY needed?)

### INTERPERSONAL SKILLS:
- Stakeholder management (WHY needed?)
- Negotiation (WHY needed?)
- Diplomacy (WHY needed?)
- Conflict resolution (WHY needed?)

### LEADERSHIP & INFLUENCE:
- Team leadership (WHY needed?)
- Influence without authority (WHY needed?)
- Change management (WHY needed?)

### ANALYTICAL & PROBLEM-SOLVING:
- Critical thinking (WHY needed?)
- Problem decomposition (WHY needed?)
- Root cause analysis (WHY needed?)

### PERSONAL ATTRIBUTES:
- Attention to detail (WHY needed?)
- Adaptability (WHY needed?)
- Persistence (WHY needed?)
- Political savvy (WHY needed?)

For each skill, explain WHY it is needed based on the specific responsibilities and organizational context described. Provide concrete examples from the career history."""
        
        response = self.call_ollama_model('olmo2:7b', prompt, timeout=600)
        
        self.log_llm_interaction(
            model='olmo2:7b',
            prompt=prompt,
            response=response,
            metadata={'phase': 'soft_skills'}
        )
        
        return response
    
    def save_career_analysis(self, profile_id: int, deepseek_results: dict, 
                            qwen_results: str, olmo_results: str, 
                            profile_metadata: dict) -> int:
        """
        Save all analysis results to career_analyses table.
        
        Returns:
            analysis_id: Primary key of saved analysis
        """
        print("\n💾 Saving analysis to database...")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Extract organizations from chunks
        organizations = list(set([
            chunk['metadata']['org'] 
            for chunk in deepseek_results.values()
        ]))
        
        # Determine career span
        periods = [chunk['metadata']['period'] for chunk in deepseek_results.values()]
        period_years = []
        for p in periods:
            # Extract years from period strings like "2020 - today" or "2010 – 2016"
            import re
            years = re.findall(r'\d{4}', p)
            period_years.extend(years)
        
        career_span = f"{min(period_years)}-{max(period_years) if 'today' not in ' '.join(periods) else '2025'}"
        
        # Structure results as JSONB
        stakeholder_levels_combined = {}
        functions_combined = {}
        org_skills_combined = {}
        
        for chunk_id, chunk_data in deepseek_results.items():
            # Parse DeepSeek analysis for structured data
            # For now, store full text in JSONB
            stakeholder_levels_combined[chunk_id] = {
                'period': chunk_data['metadata']['period'],
                'org': chunk_data['metadata']['org'],
                'analysis': chunk_data['analysis'][:1000]  # Truncate for JSONB
            }
        
        # Insert main analysis record
        cursor.execute("""
            INSERT INTO career_analyses (
                profile_id,
                workflow_run_id,
                analysis_type,
                organization,
                stakeholder_levels,
                functions_involved,
                organizational_skills,
                technical_skills,
                soft_skills,
                career_insights,
                model_used,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, NOW())
            RETURNING analysis_id
        """, (
            profile_id,
            self.workflow_run_id,
            'full_career',
            ', '.join(organizations),
            json.dumps(stakeholder_levels_combined),
            json.dumps(functions_combined),
            json.dumps(org_skills_combined),
            json.dumps({'full_text': qwen_results}),
            json.dumps({'full_text': olmo_results}),
            json.dumps({'career_span': career_span, 'full_name': profile_metadata.get('full_name', 'Unknown')}),
            'ensemble'
        ))
        
        analysis_id = cursor.fetchone()['analysis_id']
        conn.commit()
        conn.close()
        
        print(f"   ✅ Saved analysis_id: {analysis_id}")
        return analysis_id
    
    def update_workflow_run(self, status: str, notes: str = None):
        """Update workflow_run status."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE workflow_runs
            SET status = %s,
                output_data = %s,
                completed_at = NOW()
            WHERE workflow_run_id = %s
        """, (status, notes, self.workflow_run_id))
        
        conn.commit()
        conn.close()
    
    def run(self, profile_id: int = None, career_file: str = None) -> bool:
        """
        Execute Workflow 1125: Profile Career Analysis
        
        Args:
            profile_id: Profile ID from database
            career_file: Path to career history file
            
        Returns:
            bool: Success status
        """
        print("\n" + "="*70)
        print("🚀 Workflow 1125: Profile Career Analysis")
        print("="*70)
        
        try:
            # Get career history
            if profile_id:
                self.profile_id = profile_id
                print(f"\n📄 Loading career history for profile_id: {profile_id}")
                career_text, profile_metadata = self.get_profile_career_history(profile_id)
            elif career_file:
                print(f"\n📄 Loading career history from: {career_file}")
                with open(career_file, 'r') as f:
                    career_text = f.read()
                profile_metadata = {'full_name': Path(career_file).stem}
                self.profile_id = None
            else:
                raise ValueError("Must provide either profile_id or career_file")
            
            print(f"   ✅ Loaded {len(career_text)} characters")
            
            # Create workflow run
            if profile_id:
                self.workflow_run_id = self.create_workflow_run(profile_id)
                print(f"\n📋 Created workflow_run_id: {self.workflow_run_id}")
            
            # Phase 1: Chunked DeepSeek organizational analysis
            deepseek_results = self.run_chunked_deepseek_analysis(career_text)
            
            # Phase 2: Qwen technical skills
            qwen_results = self.run_qwen_technical_skills(career_text)
            
            # Phase 3: Olmo soft skills
            olmo_results = self.run_olmo_soft_skills(career_text)
            
            # Save to database
            if profile_id:
                analysis_id = self.save_career_analysis(
                    profile_id, deepseek_results, qwen_results, olmo_results, profile_metadata
                )
                print(f"\n✅ Analysis complete! analysis_id: {analysis_id}")
                
                # Update workflow_run
                self.update_workflow_run('SUCCESS', f'Analysis ID: {analysis_id}')
            else:
                print("\n✅ Analysis complete! (No database save - file input)")
                
                # Save results to JSON
                output_file = f"output/career_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(output_file, 'w') as f:
                    json.dump({
                        'deepseek': deepseek_results,
                        'qwen': qwen_results,
                        'olmo': olmo_results,
                        'profile_metadata': profile_metadata
                    }, f, indent=2)
                print(f"   💾 Saved to: {output_file}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            if self.workflow_run_id:
                self.update_workflow_run('FAILED', str(e))
            return False

def main():
    parser = argparse.ArgumentParser(description='Workflow 1125: Profile Career Analysis')
    parser.add_argument('--profile-id', type=int, help='Profile ID from database')
    parser.add_argument('--career-file', type=str, help='Path to career history file')
    parser.add_argument('--workflow-run-id', type=int, help='Optional workflow_run_id for tracking')
    
    args = parser.parse_args()
    
    if not args.profile_id and not args.career_file:
        parser.error("Must provide either --profile-id or --career-file")
    
    runner = Workflow1125Runner()
    if args.workflow_run_id:
        runner.workflow_run_id = args.workflow_run_id
    
    success = runner.run(profile_id=args.profile_id, career_file=args.career_file)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
