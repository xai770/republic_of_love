#!/usr/bin/env python3
"""
Configuration Module
===================

Configuration settings and templates for the LLM optimization framework.
Provides centralized configuration management and customization options.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class TestType(Enum):
    """Supported test types for LLM evaluation"""
    CONCISE_EXTRACTION = "concise_extraction"
    REQUIREMENTS_FOCUS = "requirements_focus"
    STRUCTURED_ANALYSIS = "structured_analysis"
    SKILLS_CATEGORIZATION = "skills_categorization"
    GENERAL_RESPONSE = "general_response"


@dataclass
class QualityThresholds:
    """Quality assessment thresholds"""
    excellent: float = 0.9
    good: float = 0.7
    fair: float = 0.5
    poor: float = 0.3


@dataclass
class CategoryWeights:
    """Weights for different metric categories"""
    quality: float = 0.4
    performance: float = 0.25
    consistency: float = 0.2
    efficiency: float = 0.1
    reliability: float = 0.05


@dataclass
class SimilarityWeights:
    """Weights for baseline similarity calculation"""
    length: float = 0.2
    structure: float = 0.3
    content: float = 0.3
    format: float = 0.2


@dataclass
class TestConfiguration:
    """Configuration for a specific test type"""
    test_id: str
    display_name: str
    description: str
    expected_elements: List[str] = field(default_factory=list)
    key_terms: List[str] = field(default_factory=list)
    length_range: tuple = (200, 800)
    required_sections: List[str] = field(default_factory=list)
    similarity_weights: Optional[SimilarityWeights] = None


@dataclass
class OptimizationConfig:
    """Main configuration for LLM optimization framework"""
    project_name: str = "LLM Optimization"
    baseline_model: Optional[str] = None
    
    # Thresholds
    quality_thresholds: QualityThresholds = field(default_factory=QualityThresholds)
    
    # Weights
    category_weights: CategoryWeights = field(default_factory=CategoryWeights)
    similarity_weights: SimilarityWeights = field(default_factory=SimilarityWeights)
    
    # Test configurations
    test_configs: Dict[str, TestConfiguration] = field(default_factory=dict)
    
    # Output settings
    output_directory: str = "reports"
    generate_json: bool = True
    generate_markdown: bool = True
    include_baseline_comparison: bool = True
    
    # Processing settings
    confidence_threshold: float = 0.6
    max_models_in_report: int = 20
    enable_detailed_logging: bool = False


class ConfigurationManager:
    """Manage framework configuration and provide defaults"""
    
    def __init__(self):
        self.default_config = self._create_default_config()
    
    def get_default_config(self) -> OptimizationConfig:
        """Get default configuration"""
        config: OptimizationConfig = self.default_config
        return config
    
    def create_custom_config(self, **overrides) -> OptimizationConfig:
        """Create custom configuration with overrides"""
        config: OptimizationConfig = self.default_config
        
        # Apply overrides
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config
    
    def _create_default_config(self) -> OptimizationConfig:
        """Create default configuration with predefined test types"""
        config = OptimizationConfig()
        
        # Add default test configurations
        config.test_configs = {
            TestType.CONCISE_EXTRACTION.value: TestConfiguration(
                test_id=TestType.CONCISE_EXTRACTION.value,
                display_name="Concise Extraction",
                description="Extract key information concisely",
                expected_elements=["tasks", "profile", "bullet_points"],
                key_terms=["audit", "security", "management", "experience", "skills"],
                length_range=(200, 600),
                required_sections=["your tasks", "your profile"],
                similarity_weights=SimilarityWeights(structure=0.4, content=0.3, format=0.2, length=0.1)
            ),
            
            TestType.REQUIREMENTS_FOCUS.value: TestConfiguration(
                test_id=TestType.REQUIREMENTS_FOCUS.value,
                display_name="Requirements Focus",
                description="Focus on specific job requirements",
                expected_elements=["requirements", "skills", "qualifications"],
                key_terms=["requirement", "skill", "experience", "degree", "education", "certification"],
                length_range=(300, 800),
                required_sections=["requirements", "qualifications"]
            ),
            
            TestType.STRUCTURED_ANALYSIS.value: TestConfiguration(
                test_id=TestType.STRUCTURED_ANALYSIS.value,
                display_name="Structured Analysis",
                description="Provide structured requirement analysis",
                expected_elements=["technical_section", "business_section", "priority_markers"],
                key_terms=["technical", "business", "critical", "important", "requirement"],
                length_range=(400, 1200),
                required_sections=["=== TECHNICAL REQUIREMENTS ===", "=== BUSINESS REQUIREMENTS ==="],
                similarity_weights=SimilarityWeights(format=0.4, structure=0.3, content=0.2, length=0.1)
            ),
            
            TestType.SKILLS_CATEGORIZATION.value: TestConfiguration(
                test_id=TestType.SKILLS_CATEGORIZATION.value,
                display_name="Skills Categorization",
                description="Categorize skills and requirements",
                expected_elements=["soft_skills", "experience", "education"],
                key_terms=["communication", "leadership", "teamwork", "experience", "education"],
                length_range=(300, 900),
                required_sections=["=== SOFT SKILLS ===", "=== EXPERIENCE REQUIRED ===", "=== EDUCATION REQUIRED ==="],
                similarity_weights=SimilarityWeights(format=0.4, structure=0.3, content=0.2, length=0.1)
            ),
            
            TestType.GENERAL_RESPONSE.value: TestConfiguration(
                test_id=TestType.GENERAL_RESPONSE.value,
                display_name="General Response",
                description="General purpose response evaluation",
                expected_elements=["content", "structure"],
                key_terms=["job", "skill", "requirement", "experience"],
                length_range=(200, 800),
                required_sections=[]
            )
        }
        
        return config
    
    def get_test_config(self, test_id: str, config: OptimizationConfig) -> TestConfiguration:
        """Get configuration for a specific test type"""
        return config.test_configs.get(test_id, config.test_configs[TestType.GENERAL_RESPONSE.value])
    
    def validate_config(self, config: OptimizationConfig) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Validate weights sum to 1.0
        total_weight = (config.category_weights.quality + 
                       config.category_weights.performance + 
                       config.category_weights.consistency + 
                       config.category_weights.efficiency + 
                       config.category_weights.reliability)
        
        if abs(total_weight - 1.0) > 0.01:
            issues.append(f"Category weights sum to {total_weight:.3f}, should be 1.0")
        
        # Validate similarity weights
        sim_total = (config.similarity_weights.length + 
                    config.similarity_weights.structure + 
                    config.similarity_weights.content + 
                    config.similarity_weights.format)
        
        if abs(sim_total - 1.0) > 0.01:
            issues.append(f"Similarity weights sum to {sim_total:.3f}, should be 1.0")
        
        # Validate thresholds are in order
        thresholds = [
            config.quality_thresholds.excellent,
            config.quality_thresholds.good,
            config.quality_thresholds.fair,
            config.quality_thresholds.poor
        ]
        
        if thresholds != sorted(thresholds, reverse=True):
            issues.append("Quality thresholds should be in descending order")
        
        # Validate test configurations
        for test_id, test_config in config.test_configs.items():
            if test_config.length_range[0] >= test_config.length_range[1]:
                issues.append(f"Invalid length range for {test_id}")
        
        return issues


# Predefined configurations for common use cases
class PresetConfigs:
    """Predefined configuration presets for common scenarios"""
    
    @staticmethod
    def quality_focused() -> OptimizationConfig:
        """Configuration focused on quality metrics"""
        config = ConfigurationManager().get_default_config()
        config.category_weights = CategoryWeights(
            quality=0.6,
            performance=0.2,
            consistency=0.15,
            efficiency=0.04,
            reliability=0.01
        )
        return config
    
    @staticmethod
    def performance_focused() -> OptimizationConfig:
        """Configuration focused on performance metrics"""
        config = ConfigurationManager().get_default_config()
        config.category_weights = CategoryWeights(
            quality=0.3,
            performance=0.4,
            consistency=0.2,
            efficiency=0.08,
            reliability=0.02
        )
        return config
    
    @staticmethod
    def consistency_focused() -> OptimizationConfig:
        """Configuration focused on consistency metrics"""
        config = ConfigurationManager().get_default_config()
        config.category_weights = CategoryWeights(
            quality=0.25,
            performance=0.25,
            consistency=0.4,
            efficiency=0.05,
            reliability=0.05
        )
        return config
    
    @staticmethod
    def production_ready() -> OptimizationConfig:
        """Configuration for production readiness assessment"""
        config = ConfigurationManager().get_default_config()
        config.category_weights = CategoryWeights(
            quality=0.3,
            performance=0.25,
            consistency=0.25,
            efficiency=0.1,
            reliability=0.1
        )
        config.quality_thresholds = QualityThresholds(
            excellent=0.95,
            good=0.85,
            fair=0.7,
            poor=0.5
        )
        return config
    
    @staticmethod
    def baseline_comparison() -> OptimizationConfig:
        """Configuration optimized for baseline comparisons"""
        config = ConfigurationManager().get_default_config()
        config.include_baseline_comparison = True
        config.similarity_weights = SimilarityWeights(
            length=0.15,
            structure=0.35,
            content=0.35,
            format=0.15
        )
        return config


# Template configurations for specific industries or use cases
class TemplateConfigs:
    """Template configurations for specific domains"""
    
    @staticmethod
    def job_matching_specialist() -> OptimizationConfig:
        """Configuration for job matching specialist evaluation"""
        config = ConfigurationManager().get_default_config()
        config.project_name = "Job Matching Specialist Optimization"
        
        # Add specialized test types
        config.test_configs[TestType.CONCISE_EXTRACTION.value].key_terms.extend([
            "coordination", "validation", "compliance", "regulatory"
        ])
        
        return config
    
    @staticmethod
    def content_extraction() -> OptimizationConfig:
        """Configuration for content extraction tasks"""
        config = ConfigurationManager().get_default_config()
        config.project_name = "Content Extraction Optimization"
        
        # Focus on structure and format for extraction tasks
        config.similarity_weights = SimilarityWeights(
            length=0.1,
            structure=0.4,
            content=0.3,
            format=0.2
        )
        
        return config
    
    @staticmethod
    def general_purpose() -> OptimizationConfig:
        """Configuration for general purpose LLM evaluation"""
        config = ConfigurationManager().get_default_config()
        config.project_name = "General Purpose LLM Optimization"
        
        # Balanced weights for general use
        config.category_weights = CategoryWeights(
            quality=0.35,
            performance=0.25,
            consistency=0.2,
            efficiency=0.12,
            reliability=0.08
        )
        
        return config


def load_config_from_dict(config_dict: Dict[str, Any]) -> OptimizationConfig:
    """Load configuration from dictionary"""
    config = OptimizationConfig()
    
    # Update basic fields
    for key, value in config_dict.items():
        if hasattr(config, key) and not key.startswith('_'):
            setattr(config, key, value)
    
    return config


def save_config_to_dict(config: OptimizationConfig) -> Dict[str, Any]:
    """Save configuration to dictionary"""
    return {
        'project_name': config.project_name,
        'baseline_model': config.baseline_model,
        'output_directory': config.output_directory,
        'generate_json': config.generate_json,
        'generate_markdown': config.generate_markdown,
        'include_baseline_comparison': config.include_baseline_comparison,
        'confidence_threshold': config.confidence_threshold,
        'max_models_in_report': config.max_models_in_report,
        'enable_detailed_logging': config.enable_detailed_logging
    }


# Export main configuration classes and functions
__all__ = [
    'OptimizationConfig',
    'TestConfiguration', 
    'ConfigurationManager',
    'PresetConfigs',
    'TemplateConfigs',
    'QualityThresholds',
    'CategoryWeights',
    'SimilarityWeights',
    'TestType',
    'load_config_from_dict',
    'save_config_to_dict'
]
