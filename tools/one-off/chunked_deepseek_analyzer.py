#!/usr/bin/env python3
"""
Chunked DeepSeek Career Analyzer
Splits career history into time periods and analyzes each chunk with DeepSeek-R1
"""

import subprocess
import json
import sys
from datetime import datetime

class ChunkedDeepSeekAnalyzer:
    def __init__(self, career_file_path):
        with open(career_file_path, 'r') as f:
            self.full_text = f.read()
        
        # Define career chunks by time period
        self.chunks = self._split_career_into_chunks()
        self.results = {}
    
    def _split_career_into_chunks(self):
        """Split the career history into logical time periods."""
        # Extract sections based on time markers in the document
        chunks = {
            "2020-2025_Deutsche_Bank_CTO": {
                "period": "2020 - today",
                "org": "Deutsche Bank, Chief Technology Office",
                "roles": ["Project lead Contract Compliance/Tech Lead", 
                         "Team Lead Proof of Entitlement",
                         "Financial Planning and Governance"]
            },
            "2016-2020_Self_Employed": {
                "period": "2016 - 2020",
                "org": "Self-Employed",
                "roles": ["Development of analysis framework for structured text documents"]
            },
            "2010-2016_Novartis": {
                "period": "2010 – 2016",
                "org": "Novartis, Basel (Global Sourcing)",
                "roles": ["Global Sourcing IT Change Management",
                         "Global Lead, Software License Management",
                         "Global Lead, Mobile Telecom Demand Management",
                         "Software Category Manager"]
            },
            "2005-2010_Deutsche_Bank_1": {
                "period": "2005 - 2010",
                "org": "Deutsche Bank AG, Frankfurt",
                "roles": ["Software Licenses and Services Vendor Manager",
                         "Software Category Manager",
                         "Global Software Compliance Manager"]
            },
            "2002-2005_Television": {
                "period": "2002 – 2005",
                "org": "Independent producer for public television",
                "roles": ["Video production for ZDF"]
            },
            "1996-2002_Freelance": {
                "period": "1996 - 2002",
                "org": "Freelance contractor",
                "roles": ["Deutsche Bank Vendor Manager",
                         "Commerzbank Application Architect",
                         "F. Hoffmann-La Roche Rollout Manager",
                         "Dresdner Bank Information Architect",
                         "Deutsche Bahn Helpdesk and Rollout Manager"]
            }
        }
        
        # Extract actual text for each chunk
        result = {}
        for chunk_id, metadata in chunks.items():
            # Find the section in the full text
            period_marker = metadata["period"]
            start_idx = self.full_text.find(period_marker)
            
            if start_idx != -1:
                # Find the end of this section (next period marker or end of file)
                next_periods = [p["period"] for k, p in chunks.items() if k != chunk_id]
                end_idx = len(self.full_text)
                
                for next_period in next_periods:
                    next_idx = self.full_text.find(next_period, start_idx + 1)
                    if next_idx != -1 and next_idx < end_idx:
                        end_idx = next_idx
                
                chunk_text = self.full_text[start_idx:end_idx].strip()
                result[chunk_id] = {
                    "metadata": metadata,
                    "text": chunk_text
                }
        
        return result
    
    def call_deepseek_api(self, chunk_id: str, chunk_data: dict) -> str:
        """Call DeepSeek-R1 via Ollama API instead of CLI."""
        import requests
        
        metadata = chunk_data["metadata"]
        text = chunk_data["text"]
        
        prompt = f"""You are an expert at analyzing organizational dynamics at large financial institutions.

CAREER PERIOD: {metadata['period']}
ORGANIZATION: {metadata['org']}

CAREER HISTORY EXCERPT:

{text}

Reason step-by-step and provide:

1. **STAKEHOLDER LEVELS**: What levels of stakeholders would this person interact with during this period?
   - C-level executives (CIO, CFO, CTO, etc.)
   - Directors/VPs (which functions?)
   - Managers (which departments?)
   - End users?

2. **FUNCTIONS INVOLVED**: What organizational functions would be engaged?
   - Legal? Procurement? IT? Finance? Compliance? Operations?
   - Be specific about WHY each function is involved

3. **ORGANIZATIONAL SKILLS REQUIRED**: What organizational navigation skills does this require?
   - Stakeholder management
   - Cross-functional collaboration
   - Influence without authority
   - Change management
   - Negotiation
   - Political savvy

4. **CAREER PROGRESSION INSIGHTS**: What does this period show about career development?
   - Leadership level (individual contributor, team lead, manager, director-level responsibilities?)
   - Scope of influence (team, department, division, global?)
   - Strategic vs tactical work?

Think through the organizational complexity carefully. Consider the size and nature of the organization."""

        print(f"\n🔍 Analyzing: {chunk_id}")
        print(f"   Period: {metadata['period']}")
        print(f"   Organization: {metadata['org']}")
        
        try:
            # Use Ollama API for better control
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': 'deepseek-r1:8b',
                    'prompt': prompt,
                    'stream': False
                },
                timeout=900
            )
            
            if response.status_code == 200:
                result_text = response.json().get('response', '')
                print(f"   ✅ Analysis complete ({len(result_text)} chars)")
                return result_text
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                print(f"   ❌ API Error: {error_msg}")
                return f"❌ API Error: {error_msg}"
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ Timeout after 15 minutes")
            return "⏰ Timeout after 15 minutes"
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return f"❌ Error: {str(e)}"
    
    def analyze_all_chunks(self):
        """Analyze all career chunks with DeepSeek."""
        print(f"\n📊 Starting chunked analysis of {len(self.chunks)} career periods...")
        
        for chunk_id in sorted(self.chunks.keys(), reverse=True):  # Most recent first
            chunk_data = self.chunks[chunk_id]
            response = self.call_deepseek_api(chunk_id, chunk_data)
            
            self.results[chunk_id] = {
                "metadata": chunk_data["metadata"],
                "analysis": response,
                "timestamp": datetime.now().isoformat()
            }
        
        print(f"\n✅ All chunks analyzed!")
        return self.results
    
    def save_results(self, output_file: str):
        """Save results to JSON file."""
        output = {
            "analysis_type": "chunked_deepseek_career_analysis",
            "total_chunks": len(self.results),
            "chunks": self.results,
            "generated_at": datetime.now().isoformat()
        }
        
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 chunked_deepseek_analyzer.py <career_file> <output_json>")
        sys.exit(1)
    
    career_file = sys.argv[1]
    output_file = sys.argv[2]
    
    analyzer = ChunkedDeepSeekAnalyzer(career_file)
    analyzer.analyze_all_chunks()
    analyzer.save_results(output_file)
    
    print("\n🎉 Analysis complete!")

if __name__ == "__main__":
    main()
