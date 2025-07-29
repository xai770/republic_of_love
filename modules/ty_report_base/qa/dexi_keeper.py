"""
Dexi Integration for ty_report_base
Phase 2b: Quality assurance keeper and validation tracking

"Begin wiring Dexi into the loop as keeper.validate(output)" - Misty
"""

import hashlib
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class ValidationRecord:
    """Record of Dexi's validation decision"""
    report_hash: str
    validation_timestamp: str
    validation_result: str  # "approved", "flagged", "rejected"
    qa_flags: List[str]
    confidence_score: float
    dexi_notes: str
    validation_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QAJournalEntry:
    """Entry in Dexi's QA journal"""
    entry_id: str
    timestamp: str
    report_hash: str
    validation_action: str
    quality_assessment: Dict[str, Any]
    recommendations: List[str]
    keeper_signature: str

class DexiKeeper:
    """Dexi - The Quality Assurance Keeper"""
    
    def __init__(self, journal_path: Optional[Path] = None):
        self.keeper_name = "Dexi"
        self.validation_history: List[ValidationRecord] = []
        self.qa_journal: List[QAJournalEntry] = []
        
        # Initialize journal storage
        self.journal_path = journal_path or Path(__file__).parent.parent / "qa" / "dexi_journal.jsonl"
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing journal if available
        self._load_existing_journal()
        
        logger.info(f"Dexi keeper initialized. Journal: {self.journal_path}")
    
    def validate_output(self, report: Dict[str, Any], input_context: Optional[Dict[str, Any]] = None) -> ValidationRecord:
        """
        Dexi's comprehensive report validation
        
        Args:
            report: Generated report to validate
            input_context: Original input data for context
            
        Returns:
            ValidationRecord with Dexi's assessment
        """
        start_time = time.time()
        
        # Generate report hash for tracking
        report_content = json.dumps(report, sort_keys=True)
        report_hash = hashlib.sha256(report_content.encode()).hexdigest()[:16]
        
        # Run Dexi's validation checks
        validation_flags = []
        confidence_score = 1.0
        
        # Structure validation
        structure_flags = self._validate_report_structure(report)
        validation_flags.extend(structure_flags)
        
        # Content quality validation
        content_flags = self._validate_content_quality(report)
        validation_flags.extend(content_flags)
        
        # Empathy validation
        empathy_flags = self._validate_empathy_presence(report)
        validation_flags.extend(empathy_flags)
        
        # Metadata validation
        metadata_flags = self._validate_metadata_integrity(report)
        validation_flags.extend(metadata_flags)
        
        # Context consistency validation
        if input_context:
            context_flags = self._validate_context_consistency(report, input_context)
            validation_flags.extend(context_flags)
        
        # Calculate overall confidence
        confidence_score = self._calculate_validation_confidence(validation_flags, report)
        
        # Determine validation result
        validation_result = self._determine_validation_result(validation_flags, confidence_score)
        
        # Generate Dexi's notes
        dexi_notes = self._generate_keeper_notes(validation_flags, confidence_score, report)
        
        # Create validation record
        validation_record = ValidationRecord(
            report_hash=report_hash,
            validation_timestamp=datetime.now().isoformat(),
            validation_result=validation_result,
            qa_flags=validation_flags,
            confidence_score=confidence_score,
            dexi_notes=dexi_notes,
            validation_metadata={
                "validation_time_ms": (time.time() - start_time) * 1000,
                "keeper_version": "v1_phase2b",
                "sections_validated": len(report.get('sections', [])),
                "input_context_available": input_context is not None
            }
        )
        
        # Store validation
        self.validation_history.append(validation_record)
        
        # Log validation decision
        logger.info(f"Dexi validation: {validation_result} (confidence: {confidence_score:.2f}, flags: {len(validation_flags)})")
        
        return validation_record
    
    def store_agreement(self, report_hash: str, flags: List[str], 
                       keeper_decision: str = "approved") -> str:
        """
        Store Dexi's agreement/disagreement with QA flags
        
        Args:
            report_hash: Hash of the report being assessed
            flags: QA flags from the system
            keeper_decision: Dexi's decision (approved/flagged/rejected)
            
        Returns:
            Agreement record ID
        """
        agreement_id = f"dexi_agreement_{int(time.time())}_{report_hash[:8]}"
        
        # Analyze flag agreement
        flag_assessment = {}
        for flag in flags:
            # Dexi's assessment of each flag
            if flag.startswith('missing_'):
                flag_assessment[flag] = "critical_concern"
            elif flag.startswith('empty_'):
                flag_assessment[flag] = "moderate_concern"
            elif flag.startswith('low_confidence'):
                flag_assessment[flag] = "noted_with_context"
            elif flag.startswith('placeholder_'):
                flag_assessment[flag] = "development_artifact"
            else:
                flag_assessment[flag] = "under_review"
        
        # Store agreement
        agreement_record = {
            "agreement_id": agreement_id,
            "report_hash": report_hash,
            "timestamp": datetime.now().isoformat(),
            "keeper_decision": keeper_decision,
            "flag_assessment": flag_assessment,
            "dexi_signature": f"validated_by_dexi_{agreement_id}"
        }
        
        # Add to validation metadata
        if self.validation_history:
            last_validation = self.validation_history[-1]
            if last_validation.report_hash == report_hash:
                last_validation.validation_metadata["agreement_record"] = agreement_id
        
        logger.debug(f"Dexi stored agreement: {agreement_id} for {report_hash}")
        return agreement_id
    
    def append_to_qa_journal(self, report_hash: str, validation_action: str,
                           quality_assessment: Dict[str, Any],
                           recommendations: Optional[List[str]] = None) -> QAJournalEntry:
        """
        Append entry to Dexi's QA journal
        
        Args:
            report_hash: Report identifier
            validation_action: Action taken (validate/flag/approve/reject)
            quality_assessment: Detailed quality analysis
            recommendations: List of recommendations
            
        Returns:
            QAJournalEntry that was added
        """
        entry_id = f"qa_journal_{int(time.time())}_{len(self.qa_journal)}"
        
        journal_entry = QAJournalEntry(
            entry_id=entry_id,
            timestamp=datetime.now().isoformat(),
            report_hash=report_hash,
            validation_action=validation_action,
            quality_assessment=quality_assessment,
            recommendations=recommendations or [],
            keeper_signature=f"dexi_qa_v1_{entry_id}"
        )
        
        # Add to journal
        self.qa_journal.append(journal_entry)
        
        # Persist to file
        self._persist_journal_entry(journal_entry)
        
        logger.info(f"Dexi QA journal entry: {entry_id} - {validation_action}")
        return journal_entry
    
    def _validate_report_structure(self, report: Dict[str, Any]) -> List[str]:
        """Validate report structure integrity"""
        flags = []
        
        # Check required top-level fields
        required_fields = ['title', 'metadata', 'sections', 'template_name']
        for field in required_fields:
            if field not in report:
                flags.append(f"missing_structure_{field}")
        
        # Check sections structure
        sections = report.get('sections', [])
        if not sections:
            flags.append("no_sections_present")
        else:
            for i, section in enumerate(sections):
                if not isinstance(section, dict):
                    flags.append(f"invalid_section_structure_{i}")
                else:
                    section_required = ['name', 'prompt', 'content']
                    for req_field in section_required:
                        if req_field not in section:
                            flags.append(f"missing_section_field_{i}_{req_field}")
        
        # Check metadata structure
        metadata = report.get('metadata', {})
        metadata_required = ['generated_by', 'timestamp', 'empathy_enabled']
        for req_field in metadata_required:
            if req_field not in metadata:
                flags.append(f"missing_metadata_{req_field}")
        
        return flags
    
    def _validate_content_quality(self, report: Dict[str, Any]) -> List[str]:
        """Validate content quality and substance"""
        flags = []
        
        sections = report.get('sections', [])
        for i, section in enumerate(sections):
            content = section.get('content', '')
            section_name = section.get('name', f'section_{i}')
            
            # Length validation
            if len(content.strip()) < 30:
                flags.append(f"insufficient_content_{section_name}")
            
            # Placeholder detection
            if '[Placeholder' in content or '[Generated' in content:
                flags.append(f"placeholder_content_{section_name}")
            
            # Repetition detection
            sentences = content.split('.')
            if len(set(sentences)) < len(sentences) * 0.8 and len(sentences) > 3:
                flags.append(f"repetitive_content_{section_name}")
            
            # Generic content detection
            generic_phrases = ['based on the data', 'analysis shows', 'in summary']
            if sum(phrase in content.lower() for phrase in generic_phrases) > 2:
                flags.append(f"generic_content_{section_name}")
        
        return flags
    
    def _validate_empathy_presence(self, report: Dict[str, Any]) -> List[str]:
        """Validate empathy presence and appropriateness"""
        flags = []
        
        empathy_enabled = report.get('metadata', {}).get('empathy_enabled', False)
        if not empathy_enabled:
            flags.append("empathy_not_enabled")
            return flags
        
        # Check for empathy indicators in content
        empathy_indicators = [
            'job seeker', 'career', 'professional', 'opportunity',
            'perspective', 'journey', 'experience', 'growth'
        ]
        
        sections = report.get('sections', [])
        empathy_found = False
        
        for section in sections:
            content = section.get('content', '').lower()
            if any(indicator in content for indicator in empathy_indicators):
                empathy_found = True
                break
        
        if not empathy_found:
            flags.append("empathy_not_present_in_content")
        
        # Check for appropriate tone
        harsh_language = ['failure', 'inadequate', 'poor', 'bad', 'wrong']
        for section in sections:
            content = section.get('content', '').lower()
            if any(harsh in content for harsh in harsh_language):
                flags.append(f"harsh_language_{section.get('name', 'unknown')}")
        
        return flags
    
    def _validate_metadata_integrity(self, report: Dict[str, Any]) -> List[str]:
        """Validate metadata completeness and accuracy"""
        flags = []
        
        metadata = report.get('metadata', {})
        
        # Check timestamp format
        timestamp = metadata.get('timestamp', '')
        if not timestamp or 'T' not in timestamp:
            flags.append("invalid_timestamp_format")
        
        # Check QA flags structure
        qa_flags = metadata.get('qa_flags', [])
        if not isinstance(qa_flags, list):
            flags.append("invalid_qa_flags_structure")
        
        # Check generated_by field
        generated_by = metadata.get('generated_by', '')
        if not generated_by or generated_by == '':
            flags.append("missing_generated_by")
        
        return flags
    
    def _validate_context_consistency(self, report: Dict[str, Any], 
                                    input_context: Dict[str, Any]) -> List[str]:
        """Validate consistency between report and input context"""
        flags: List[str] = []
        
        # Extract blocks from input context
        blocks = input_context.get('blocks', [])
        if not blocks:
            return flags
        
        first_block = blocks[0]
        report_title = report.get('title', '')
        
        # Check title consistency
        if 'title' in first_block:
            input_title = first_block['title']
            if input_title and input_title not in report_title:
                flags.append("title_mismatch_with_input")
        
        # Check if content references input data appropriately
        sections = report.get('sections', [])
        references_input = False
        
        for section in sections:
            content = section.get('content', '').lower()
            if any(word in content for word in ['extraction', 'data', 'source', 'provided']):
                references_input = True
                break
        
        if not references_input:
            flags.append("no_input_data_reference")
        
        return flags
    
    def _calculate_validation_confidence(self, flags: List[str], 
                                       report: Dict[str, Any]) -> float:
        """Calculate Dexi's confidence in the validation"""
        base_confidence = 1.0
        
        # Deduct confidence for each flag category
        flag_penalties = {
            'missing_structure_': 0.3,
            'missing_metadata_': 0.2,
            'insufficient_content_': 0.15,
            'placeholder_content_': 0.1,
            'empathy_not_': 0.2,
            'harsh_language_': 0.1,
            'repetitive_content_': 0.05
        }
        
        for flag in flags:
            for penalty_pattern, penalty in flag_penalties.items():
                if flag.startswith(penalty_pattern):
                    base_confidence -= penalty
                    break
        
        # Ensure confidence stays within bounds
        return max(0.1, min(1.0, base_confidence))
    
    def _determine_validation_result(self, flags: List[str], 
                                   confidence: float) -> str:
        """Determine Dexi's validation result"""
        
        # Critical flags that result in rejection
        critical_flags = [flag for flag in flags if any(
            critical in flag for critical in 
            ['missing_structure_', 'no_sections_present', 'empathy_not_enabled']
        )]
        
        if critical_flags:
            return "rejected"
        
        # Low confidence or multiple flags result in flagging
        if confidence < 0.7 or len(flags) > 5:
            return "flagged"
        
        # Otherwise approved
        return "approved"
    
    def _generate_keeper_notes(self, flags: List[str], confidence: float, 
                             report: Dict[str, Any]) -> str:
        """Generate Dexi's keeper notes"""
        
        notes = []
        
        # Overall assessment
        if confidence > 0.9:
            notes.append("Excellent report quality with strong empathetic content.")
        elif confidence > 0.7:
            notes.append("Good report quality with minor areas for improvement.")
        elif confidence > 0.5:
            notes.append("Acceptable quality but requires attention to flagged issues.")
        else:
            notes.append("Quality concerns identified - review and revision recommended.")
        
        # Specific flag commentary
        if any('empathy' in flag for flag in flags):
            notes.append("Empathy integration needs attention to ensure caring tone throughout.")
        
        if any('structure' in flag for flag in flags):
            notes.append("Report structure requires alignment with expected format.")
        
        if any('content' in flag for flag in flags):
            notes.append("Content quality could benefit from more specific, contextual information.")
        
        # Positive observations
        sections_count = len(report.get('sections', []))
        if sections_count >= 5:
            notes.append(f"Comprehensive coverage with {sections_count} well-structured sections.")
        
        empathy_enabled = report.get('metadata', {}).get('empathy_enabled', False)
        if empathy_enabled:
            notes.append("Empathy framework is properly enabled and configured.")
        
        return " | ".join(notes)
    
    def _load_existing_journal(self):
        """Load existing journal entries from file"""
        if self.journal_path.exists():
            try:
                with open(self.journal_path, 'r') as f:
                    for line in f:
                        if line.strip():
                            entry_data = json.loads(line)
                            # Reconstruct QAJournalEntry from stored data
                            # (Implementation would depend on exact storage format)
                            pass
                logger.info(f"Loaded existing Dexi journal from {self.journal_path}")
            except Exception as e:
                logger.warning(f"Could not load existing journal: {e}")
    
    def _persist_journal_entry(self, entry: QAJournalEntry):
        """Persist journal entry to file"""
        try:
            entry_data = {
                'entry_id': entry.entry_id,
                'timestamp': entry.timestamp,
                'report_hash': entry.report_hash,
                'validation_action': entry.validation_action,
                'quality_assessment': entry.quality_assessment,
                'recommendations': entry.recommendations,
                'keeper_signature': entry.keeper_signature
            }
            
            with open(self.journal_path, 'a') as f:
                f.write(json.dumps(entry_data) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to persist journal entry: {e}")
    
    def get_keeper_summary(self) -> Dict[str, Any]:
        """Get summary of Dexi's validation activity"""
        if not self.validation_history:
            return {"status": "no_validations_performed"}
        
        total_validations = len(self.validation_history)
        results_summary: Dict[str, int] = {}
        avg_confidence = 0.0
        total_flags = 0
        
        for validation in self.validation_history:
            result = validation.validation_result
            results_summary[result] = results_summary.get(result, 0) + 1
            avg_confidence += validation.confidence_score
            total_flags += len(validation.qa_flags)
        
        avg_confidence /= total_validations
        
        return {
            "keeper_name": self.keeper_name,
            "total_validations": total_validations,
            "validation_results": results_summary,
            "average_confidence": round(avg_confidence, 3),
            "average_flags_per_report": round(total_flags / total_validations, 2),
            "journal_entries": len(self.qa_journal),
            "keeper_version": "v1_phase2b"
        }
