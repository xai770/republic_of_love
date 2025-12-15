#!/usr/bin/env python3
"""
Base Interrogator Class
========================

Abstract base class for all job source interrogators.
Provides common functionality for finding recording, reporting, and export.

Author: Arden & xai
Date: 2025-11-07
"""

import json
from datetime import datetime
from typing import List, Dict, Optional
from abc import ABC, abstractmethod


class JobSourceInterrogator(ABC):
    """Base class for interrogating job board APIs"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.findings: List[Dict] = []
        self.start_time = datetime.now()
        
    def add_finding(self, category: str, message: str, severity: str = "INFO"):
        """Record a finding with category, message, and severity
        
        Args:
            category: Finding category (e.g., "API Limits", "Geography")
            message: Human-readable finding description
            severity: One of INFO, SUCCESS, WARNING, ERROR
        """
        self.findings.append({
            'category': category,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        })
        
        # Print immediately for live feedback
        icon = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "SUCCESS": "✅"
        }
        print(f"{icon.get(severity, 'ℹ️')} [{category}] {message}")
    
    def report(self):
        """Generate and print final report"""
        print("\n" + "="*70)
        print("📊 INTERROGATION REPORT")
        print("="*70)
        
        # Group by category
        by_category = {}
        for finding in self.findings:
            cat = finding['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(finding)
        
        # Print findings by category
        for category, findings in by_category.items():
            print(f"\n{category}:")
            for f in findings:
                print(f"  • {f['message']}")
    
    def generate_summary(self) -> Dict:
        """Generate summary statistics"""
        return {
            'source': self.source_name,
            'timestamp': self.start_time.isoformat(),
            'duration_seconds': (datetime.now() - self.start_time).total_seconds(),
            'total_findings': len(self.findings),
            'errors': len([f for f in self.findings if f['severity'] == 'ERROR']),
            'warnings': len([f for f in self.findings if f['severity'] == 'WARNING']),
            'successes': len([f for f in self.findings if f['severity'] == 'SUCCESS']),
            'info': len([f for f in self.findings if f['severity'] == 'INFO'])
        }
    
    def export_report(self, output_file: str):
        """Export findings to JSON file
        
        Args:
            output_file: Path to JSON output file
        """
        report = {
            'summary': self.generate_summary(),
            'findings': self.findings,
            'recommendations': self.generate_recommendations()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.add_finding("Export", f"✅ Report saved to {output_file}", "SUCCESS")
    
    @abstractmethod
    def generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on findings
        
        Returns:
            List of recommendation strings
        """
        pass
    
    @abstractmethod
    def run_full_interrogation(self):
        """Run all interrogation tests
        
        Must be implemented by subclasses
        """
        pass
