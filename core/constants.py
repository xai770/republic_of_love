"""
Core Constants - Single source of truth for field names and status values.

Import these instead of using string literals. Typo = import error, not silent bug.

Usage:
    from core.constants import Status, Fields, Commands
    
    if ticket['status'] == Status.COMPLETED:  # Not 'success' or 'completed'
    output[Fields.OWL_ID] = owl_id                  # Not 'owl_id' sometimes, 'competency_id' others

Author: Arden
Date: 2026-01-02
Reason: Too many bugs from inconsistent field names ('success' vs 'completed', 
        'parent_folder_id' vs 'parent_id' vs 'new_folder_parent_id')
"""


class Status:
    """Ticket and workflow status values."""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    STOPPED = 'stopped'
    INTERRUPTED = 'interrupted'


class QueueStatus:
    """Queue table status values. (Legacy - queues deprecated, keeping for reference)"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'


class Fields:
    """Standard field names for data passing between actors."""
    # OWL (ontology) identification
    OWL_ID = 'owl_id'
    COMPETENCY_NAME = 'competency_name'
    
    # Task types and logs
    TASK_TYPE_ID = 'task_type_id'
    TICKET_ID = 'ticket_id'
    
    # Folder/taxonomy
    FOLDER_ID = 'folder_id'
    FOLDER_NAME = 'folder_name'
    PARENT_FOLDER_ID = 'parent_folder_id'  # THE canonical name
    
    # Classification results
    NEW_FOLDER = 'new_folder'
    CREATE_FOLDER = 'create_folder'
    NEW_FOLDER_NAME = 'new_folder_name'
    NEW_FOLDER_PARENT_ID = 'new_folder_parent_id'  # Alias for PARENT_FOLDER_ID in apply context
    
    # Workflow state
    SUCCESS = 'success'
    ERROR = 'error'
    MATCH = 'match'
    REASON = 'reason'
    
    # Parent chain
    PARENT_OUTPUT = 'parent_output'


class Commands:
    """Classifier commands."""
    PLACE = 'PLACE'
    NEW_FOLDER = 'NEW_FOLDER'
    NAVIGATE = 'NAVIGATE'
    UP = 'UP'
    ESCALATE = 'ESCALATE'
    MAX_DEPTH = 'MAX_DEPTH'


class Relationships:
    """Entity relationship types."""
    BELONGS_TO = 'belongs_to'
    IS_A = 'is_a'
    ALIAS_OF = 'alias_of'


class OwlTypes:
    """OWL (ontology) type values.
    
    Renamed 2026-01-08 for clarity:
    - competency/competency_atomic → skill
    - competency_group → folder
    - competency_root → taxonomy_root
    """
    # Core hierarchy
    SKILL = 'skill'              # Leaf nodes - actual competencies
    FOLDER = 'folder'            # Container/category in hierarchy
    TAXONOMY_ROOT = 'taxonomy_root'  # Root of taxonomy tree
    
    # Geography
    CITY = 'city'
    STATE = 'state'
    COUNTRY = 'country'
    CONTINENT = 'continent'
    
    # Competency Proof Stack hierarchies (CPS)
    CERTIFICATE = 'certificate'       # Formal credentials (AWS, PMP, CPA, degrees)
    INDUSTRY_DOMAIN = 'industry_domain'   # fintech, healthcare, startups, etc.
    SENIORITY_CONTEXT = 'seniority_context'  # Org-specific level docs (DB VP vs Google L6)
    
    # Future types (add as needed)
    LANGUAGE = 'language'             # Spoken languages
    WORK_MODE = 'work_mode'           # remote/hybrid/onsite
    SALARY_RANGE = 'salary_range'     # Compensation expectations
    
    # Deprecated (kept for migration reference, delete after 2026-02-08)
    COMPETENCY = 'competency'
    COMPETENCY_ATOMIC = 'competency_atomic'
    COMPETENCY_GROUP = 'competency_group'
    COMPETENCY_ROOT = 'competency_root'


class RequirementStrength:
    """Posting competency requirement strength values (SECT model)."""
    REQUIRED = 'required'
    PREFERRED = 'preferred'
    NICE_TO_HAVE = 'nice_to_have'


class SECTType:
    """SECT proof stack types."""
    COMPETENCY = 'S'           # Learnable capability
    EXPERIENCE = 'E'      # Skill + Duration
    CERTIFICATION = 'C'   # Formal credential
    TRACK_RECORD = 'T'    # Demonstrated outcome


class SpecialFolders:
    """Special folder IDs and names in the OWL taxonomy."""
    COMPETENCY_ROOT_ID = 39066      # The 'competency' node - taxonomy root
    NEEDS_REVIEW_ID = 39993         # _NeedsReview escape hatch folder
    NEEDS_REVIEW_NAME = '_NeedsReview'


class TaskTypeNames:
    """Active task type names. Query task_types table for full list."""
    # Posting processing
    SUMMARY_EXTRACT = 'session_a_extract_summary'
    IHL_ANALYST = 'ihl_analyst_find_red_flags'
    LILY_CPS_EXTRACT = 'lily_cps_extract'
    
    # OWL taxonomy
    LUCY_LOOKUP = 'lucy_lookup'
