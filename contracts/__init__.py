"""
Workflow Data Contracts
======================

Type-safe data contracts for Turing workflows using Python dataclasses.
Auto-syncs to workflow_variables table for registry + validation.

Usage:
    from contracts.workflow_data import register_workflow_contract
    
    @register_workflow_contract(workflow_id=1121, workflow_name="Job Skills Extraction")
    class JobSkillsExtractionContract:
        @dataclass
        class Input:
            posting_id: int
        
        @dataclass
        class Output:
            skills: List[Dict[str, Any]]
            posting_id: int

Philosophy:
- Single source of truth: Code generates DB + docs
- Type safety: IDE autocomplete, mypy validation
- Self-documenting: Types + docstrings = complete spec
- Incremental: Add contracts as needed, not all at once

Author: Arden & xai
Date: 2025-11-06
"""

from dataclasses import dataclass, fields
from typing import List, Dict, Any, Optional, get_type_hints, get_origin, get_args
import json
from datetime import datetime

# Global registry of contracts (populated by decorator)
_WORKFLOW_CONTRACTS: Dict[int, 'WorkflowContract'] = {}


def register_workflow_contract(workflow_id: int, workflow_name: str):
    """
    Decorator to register a workflow contract.
    
    Example:
        @register_workflow_contract(workflow_id=1121, workflow_name="Job Skills Extraction")
        class JobSkillsExtractionContract:
            @dataclass
            class Input:
                posting_id: int
            
            @dataclass
            class Output:
                skills: List[Dict[str, Any]]
                posting_id: int
    """
    def decorator(contract_class):
        contract = WorkflowContract(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            contract_class=contract_class
        )
        _WORKFLOW_CONTRACTS[workflow_id] = contract
        return contract_class
    
    return decorator


class WorkflowContract:
    """
    Represents the complete input/output contract for a workflow.
    Auto-generates JSON Schema and database registry entries.
    """
    
    def __init__(self, workflow_id: int, workflow_name: str, contract_class):
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.contract_class = contract_class
        self.input_class = getattr(contract_class, 'Input', None)
        self.output_class = getattr(contract_class, 'Output', None)
        
    def get_input_schema(self) -> Dict[str, Any]:
        """Generate JSON Schema for input variables"""
        if not self.input_class:
            return {}
        return self._dataclass_to_schema(self.input_class)
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Generate JSON Schema for output variables"""
        if not self.output_class:
            return {}
        return self._dataclass_to_schema(self.output_class)
    
    def validate_input(self, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate input data against contract.
        Returns: (is_valid, error_messages)
        """
        if not self.input_class:
            return True, []
        
        errors = []
        type_hints = get_type_hints(self.input_class)
        
        for field_name, field_type in type_hints.items():
            if field_name not in data:
                errors.append(f"Missing required field: {field_name}")
                continue
            
            # Basic type checking
            value = data[field_name]
            if not self._check_type(value, field_type):
                errors.append(f"Field {field_name}: expected {field_type}, got {type(value)}")
        
        return len(errors) == 0, errors
    
    def validate_output(self, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate output data against contract.
        Returns: (is_valid, error_messages)
        """
        if not self.output_class:
            return True, []
        
        errors = []
        type_hints = get_type_hints(self.output_class)
        
        for field_name, field_type in type_hints.items():
            if field_name not in data:
                errors.append(f"Missing required output field: {field_name}")
                continue
            
            value = data[field_name]
            if not self._check_type(value, field_type):
                errors.append(f"Output field {field_name}: expected {field_type}, got {type(value)}")
        
        return len(errors) == 0, errors
    
    def to_registry_rows(self) -> List[Dict[str, Any]]:
        """
        Generate database rows for workflow_variables table.
        Returns list of dicts ready for insertion.
        """
        rows = []
        
        # Input variables
        if self.input_class:
            type_hints = get_type_hints(self.input_class)
            for field_name, field_type in type_hints.items():
                rows.append(self._field_to_registry_row(field_name, field_type, 'input'))
        
        # Output variables
        if self.output_class:
            type_hints = get_type_hints(self.output_class)
            for field_name, field_type in type_hints.items():
                rows.append(self._field_to_registry_row(field_name, field_type, 'output'))
        
        return rows
    
    def _field_to_registry_row(self, field_name: str, field_type: type, scope: str) -> Dict[str, Any]:
        """Convert a field to a workflow_variables row"""
        data_type, json_schema = self._python_type_to_json_schema(field_type)
        
        return {
            'variable_name': field_name,
            'workflow_id': self.workflow_id,
            'scope': scope,
            'data_type': data_type,
            'json_schema': json.dumps(json_schema),
            'is_required': True,  # All dataclass fields are required by default
            'python_type': str(field_type).replace('typing.', ''),
            'description': f'{scope.capitalize()} variable for {self.workflow_name}',
        }
    
    def _dataclass_to_schema(self, dataclass_type) -> Dict[str, Any]:
        """Convert dataclass to JSON Schema"""
        type_hints = get_type_hints(dataclass_type)
        properties = {}
        required = []
        
        for field_name, field_type in type_hints.items():
            data_type, schema = self._python_type_to_json_schema(field_type)
            properties[field_name] = schema
            required.append(field_name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def _python_type_to_json_schema(self, python_type) -> tuple[str, Dict[str, Any]]:
        """
        Convert Python type annotation to (data_type, JSON Schema).
        
        Examples:
            int -> ('integer', {'type': 'integer'})
            str -> ('string', {'type': 'string'})
            List[str] -> ('array', {'type': 'array', 'items': {'type': 'string'}})
        """
        # Handle Optional types
        origin = get_origin(python_type)
        args = get_args(python_type)
        
        if origin is Optional:
            python_type = args[0]
            origin = get_origin(python_type)
            args = get_args(python_type)
        
        # Basic types
        if python_type == int:
            return 'integer', {'type': 'integer'}
        elif python_type == str:
            return 'string', {'type': 'string'}
        elif python_type == bool:
            return 'boolean', {'type': 'boolean'}
        elif python_type == float:
            return 'number', {'type': 'number'}
        
        # List types
        elif origin is list or origin is List:
            if args:
                item_type, item_schema = self._python_type_to_json_schema(args[0])
                return 'array', {'type': 'array', 'items': item_schema}
            return 'array', {'type': 'array'}
        
        # Dict types
        elif origin is dict or origin is Dict:
            return 'object', {'type': 'object'}
        
        # Fallback
        else:
            return 'json', {'type': 'object'}
    
    def _check_type(self, value: Any, expected_type: type) -> bool:
        """Simple runtime type checking"""
        origin = get_origin(expected_type)
        
        if origin is list or origin is List:
            return isinstance(value, list)
        elif origin is dict or origin is Dict:
            return isinstance(value, dict)
        elif expected_type == int:
            return isinstance(value, int)
        elif expected_type == str:
            return isinstance(value, str)
        elif expected_type == bool:
            return isinstance(value, bool)
        elif expected_type == float:
            return isinstance(value, (int, float))
        else:
            return True  # Skip complex type checking


def get_contract(workflow_id: int) -> Optional[WorkflowContract]:
    """Get registered contract for a workflow"""
    return _WORKFLOW_CONTRACTS.get(workflow_id)


def list_all_contracts() -> Dict[int, WorkflowContract]:
    """Get all registered contracts"""
    return _WORKFLOW_CONTRACTS.copy()


# ============================================================================
# Concrete Workflow Contracts
# ============================================================================

@register_workflow_contract(workflow_id=1121, workflow_name="Job Skills Extraction")
class JobSkillsExtractionContract:
    """
    Contract for Workflow 1121: Extract skills from job descriptions.
    
    Input: posting_id (job to analyze)
    Output: skills array + posting_id for reference
    """
    
    @dataclass
    class Input:
        posting_id: int
    
    @dataclass
    class Output:
        skills: List[Dict[str, Any]]  # Array of skill objects
        posting_id: int


@register_workflow_contract(workflow_id=2002, workflow_name="Profile Skills Extraction")
class ProfileSkillsExtractionContract:
    """
    Contract for Workflow 2002: Extract skills from candidate profiles.
    
    Input: profile_id (candidate to analyze)
    Output: skills array + profile_id for reference
    """
    
    @dataclass
    class Input:
        profile_id: int
    
    @dataclass
    class Output:
        skills: List[Dict[str, Any]]
        profile_id: int


@register_workflow_contract(workflow_id=1122, workflow_name="Profile Skill Extraction")
class ProfileSkillExtractionLegacyContract:
    """
    Contract for Workflow 1122: Legacy profile skills extraction.
    Similar to 2002 but older implementation.
    
    Input: profile_id (candidate to analyze)
    Output: skills array + profile_id for reference
    """
    
    @dataclass
    class Input:
        profile_id: int
    
    @dataclass
    class Output:
        skills: List[Dict[str, Any]]
        profile_id: int


@register_workflow_contract(workflow_id=1126, workflow_name="Profile Document Import")
class ProfileDocumentImportContract:
    """
    Contract for Workflow 1126: Import profile document into database.
    
    4-conversation workflow:
    1. Extract: Parse document → structured JSON
    2. Validate: Check data quality
    3. Import: Generate SQL and insert
    4. Error: Handle failures
    
    Input: document_text (raw profile document)
    Output: profile_id (newly created profile)
    """
    
    @dataclass
    class Input:
        document_text: str
    
    @dataclass
    class Output:
        profile_id: int


# ============================================================================
# Data Contracts for Deutsche Bank Job Fetcher
# ============================================================================

@dataclass
class DeutscheBankJobFlattened:
    """
    Deutsche Bank API response AFTER flattening in _fetch_from_api().
    
    Key insight: MatchedObjectDescriptor is merged to top level!
    This means ApplyURI, PositionTitle, etc. are directly accessible.
    
    Usage:
        jobs: List[DeutscheBankJobFlattened] = fetcher._fetch_from_api()
        for job in jobs:
            apply_uri = job.ApplyURI  # Type-safe access!
    """
    MatchedObjectId: str
    PositionTitle: str
    ApplyURI: List[str]  # At TOP level after flattening!
    PositionLocation: List[Dict[str, Any]]
    CareerLevel: List[Dict[str, Any]]
    PositionSchedule: List[Dict[str, Any]]
    PositionOfferingType: List[Dict[str, Any]]
    PublicationStartDate: str
    PositionURI: Optional[str] = None
    PositionHiringYear: Optional[str] = None
    OrganizationName: Optional[str] = None


@dataclass
class JobFetcherInput:
    """Input for job fetcher"""
    user_id: int
    max_jobs: int = 50


@dataclass
class JobFetcherOutput:
    """Output statistics from job fetcher"""
    fetched: int
    new: int
    duplicate: int
    error: int


@register_workflow_contract(workflow_id=1124, workflow_name="Fake Job Detector")
class FakeJobDetectorContract:
    """
    Contract for Workflow 1124: Detect pre-wired/fake job postings.
    
    Uses IHL Score (Intrinsic Hiring Logic) to identify compliance theater:
    - 1-3: Genuine opening (apply!)
    - 4-7: Compliance theater (suspicious)
    - 8-10: Pre-wired for specific candidate (skip)
    
    Input: posting_id (workflow fetches job_description from database)
    Output: IHL analysis with score, verdict, red flags
    """
    
    @dataclass
    class Input:
        posting_id: int
    
    @dataclass
    class Output:
        ihl_score: int
        verdict: str  # GENUINE | COMPLIANCE_THEATER | PRE_WIRED
        confidence: str  # LOW | MEDIUM | HIGH
        red_flags: List[Dict[str, str]]
        candidate_pool_estimate: str
        recommendation: str  # APPLY | CAUTION | SKIP
        reasoning: str


@register_workflow_contract(workflow_id=3001, workflow_name="Complete Job Processing Pipeline")
class CompleteJobProcessingPipelineContract:
    """
    Contract for Workflow 3001: Full end-to-end job processing.
    
    15-conversation pipeline that:
    1. Fetches jobs from Deutsche Bank API
    2. Extracts & validates job summary (multi-model consensus)
    3. Extracts skills & maps to taxonomy
    4. Performs IHL scoring (3-actor debate)
    
    Input: API fetch parameters (user_id, max_jobs, source_id)
    Output: Complete processing results with summary, skills, IHL score
    
    Note: This is the FULL pipeline. For just summary extraction,
    use workflow 3002 (when created).
    """
    
    @dataclass
    class Input:
        variations_param_1: str  # Job description text
        posting_id: int          # Posting ID to update
        user_id: int = 1         # User requesting the work
        max_jobs: int = 1        # Number of jobs to process
        source_id: int = 1       # Job source ID
    
    @dataclass
    class Output:
        extracted_summary: str   # Formatted job summary
        skills: List[Dict[str, Any]]  # Extracted skills
        ihl_score: int          # Fake job score (1-10)
        ihl_verdict: str        # GENUINE | COMPLIANCE_THEATER | PRE_WIRED
        posting_id: int         # Reference to processed posting
