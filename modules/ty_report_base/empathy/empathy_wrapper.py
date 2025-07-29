"""
Empathy Layer for ty_report_base
Implements empathetic prompt wrapping and tone adjustment

"Hello, fellow being. How are you?..."
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class EmpathyWrapper:
    """Advanced empathy injection for prompts"""
    
    def __init__(self, version: str = "v1"):
        self.version = version
        self.empathy_templates = self._load_empathy_templates()
    
    def _load_empathy_templates(self) -> Dict[str, Dict[str, str]]:
        """Load empathy templates for different contexts"""
        return {
            "v1": {
                "greeting": "Hello, fellow being. How are you?",
                "request": "We come asking for your insight with respect and care.",
                "context": "Please consider this information thoughtfully:",
                "closing": "Thank you for your thoughtful response. We appreciate your wisdom."
            },
            "caring": {
                "greeting": "Dear friend, we hope you are well today.",
                "request": "We seek your gentle guidance on this matter:",
                "context": "Here is what we're working with:",
                "closing": "With gratitude for your kindness and insight."
            },
            "professional": {
                "greeting": "Good day, colleague.",
                "request": "We request your professional assessment:",
                "context": "Please review the following information:",
                "closing": "Thank you for your expertise."
            }
        }
    
    def wrap_prompt(self, prompt: str, empathy: bool = True, 
                   tone: str = "v1", audience: str = "general",
                   context_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Wrap a prompt with empathetic framing
        
        Args:
            prompt: The core prompt to wrap
            empathy: Whether to apply empathy wrapping
            tone: Empathy tone variant (v1, caring, professional)
            audience: Target audience (general, technical, creative)
            context_data: Optional context for personalization
            
        Returns:
            Empathy-wrapped prompt
        """
        if not empathy:
            return prompt
        
        # Get template for the specified tone
        template = self.empathy_templates.get(tone, self.empathy_templates["v1"])
        
        # Build empathetic wrapper
        wrapped = []
        
        # Greeting
        wrapped.append(template["greeting"])
        wrapped.append("")  # Empty line for breathing room
        
        # Context setting
        wrapped.append(template["request"])
        wrapped.append("")
        
        if context_data:
            wrapped.append(template["context"])
            wrapped.append("")
        
        # The actual prompt
        wrapped.append(prompt)
        wrapped.append("")
        
        # Closing
        wrapped.append(template["closing"])
        
        result = "\n".join(wrapped)
        
        logger.info(f"Wrapped prompt with empathy (tone: {tone}, length: {len(result)} chars)")
        return result
    
    def adjust_tone_for_content(self, base_tone: str, content_type: str, 
                               confidence: float = 1.0) -> str:
        """
        Adjust empathy tone based on content characteristics
        
        Args:
            base_tone: Starting tone preference
            content_type: Type of content being processed
            confidence: Confidence level of the data
            
        Returns:
            Recommended tone adjustment
        """
        # Lower confidence data needs more caring approach
        if confidence < 0.5:
            return "caring"
        
        # Technical content can use professional tone
        if content_type in ["technical", "analysis", "validation"]:
            return "professional"
        
        # Narrative content benefits from caring tone
        if content_type in ["narrative", "commentary", "story"]:
            return "caring"
        
        # Default to requested tone
        return base_tone
    
    def get_empathy_metadata(self, tone: str, content_type: str) -> Dict[str, Any]:
        """Generate metadata about empathy settings used"""
        return {
            "empathy_version": self.version,
            "tone_used": tone,
            "content_type": content_type,
            "template_keys": list(self.empathy_templates.get(tone, {}).keys())
        }
