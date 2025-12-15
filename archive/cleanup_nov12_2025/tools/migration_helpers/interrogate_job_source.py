#!/usr/bin/env python3
"""
Job Source Interrogator
========================

Analyzes a job board to understand its structure, capabilities, and quirks.
Run this BEFORE building import scripts to save hours of debugging.

Usage:
    python3 tools/interrogate_job_source.py --source deutsche_bank
    python3 tools/interrogate_job_source.py --source deutsche_bank --deep

Author: Arden & xai
Date: 2025-11-07
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
import argparse
from collections import Counter
from bs4 import BeautifulSoup


class JobSourceInterrogator:
    """Interrogates a job board API to understand its structure"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.findings = []
        
    def add_finding(self, category: str, message: str, severity: str = "INFO"):
        """Record a finding"""
        self.findings.append({
            'category': category,
            'message': message,
            'severity': severity
        })
        
        # Print immediately for live feedback
        icon = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "SUCCESS": "✅"}
        print(f"{icon.get(severity, 'ℹ️')} [{category}] {message}")
    
    def report(self):
        """Generate final report"""
        print("\n" + "="*70)
        print("📊 INTERROGATION REPORT")
        print("="*70)
        
        by_category = {}
        for finding in self.findings:
            cat = finding['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(finding)
        
        for category, findings in by_category.items():
            print(f"\n{category}:")
            for f in findings:
                print(f"  • {f['message']}")


class DeutscheBankInterrogator(JobSourceInterrogator):
    """Specialized interrogator for Deutsche Bank career site"""
    
    API_URL = "https://api-deutschebank.beesite.de/search/"
    
    def __init__(self):
        super().__init__("Deutsche Bank")
        
    def test_api_limits(self):
        """Test how many jobs we can fetch in one request"""
        self.add_finding("API Limits", "Testing maximum fetch size...", "INFO")
        
        for count in [10, 100, 500, 1000, 2000, 5000]:
            payload = {
                "LanguageCode": "en",
                "SearchParameters": {
                    "FirstItem": 1,
                    "CountItem": count,
                    "MatchedObjectDescriptor": ["PositionID"]
                },
                "SearchCriteria": []
            }
            
            url = f"{self.API_URL}?data={json.dumps(payload)}"
            
            try:
                response = requests.get(url, timeout=30)
                data = response.json()
                
                total = data.get("SearchResult", {}).get("SearchResultCount", 0)
                returned = len(data.get("SearchResult", {}).get("SearchResultItems", []))
                
                if returned == count or returned == total:
                    self.add_finding(
                        "API Limits",
                        f"CountItem={count} → returned {returned} jobs (total available: {total})",
                        "SUCCESS"
                    )
                    
                    if returned < total:
                        self.add_finding(
                            "API Limits",
                            f"⚠️  API limit reached! {returned} returned but {total} available",
                            "WARNING"
                        )
                    
                    return total, returned
                    
            except Exception as e:
                self.add_finding("API Limits", f"CountItem={count} failed: {e}", "ERROR")
                break
        
        return None, None
    
    def analyze_geographic_distribution(self):
        """Check which countries have jobs"""
        self.add_finding("Geography", "Analyzing job distribution by country...", "INFO")
        
        payload = {
            "LanguageCode": "en",
            "SearchParameters": {
                "FirstItem": 1,
                "CountItem": 2000,
                "MatchedObjectDescriptor": ["PositionID", "PositionLocation"]
            },
            "SearchCriteria": []
        }
        
        url = f"{self.API_URL}?data={json.dumps(payload)}"
        
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            
            jobs = data.get("SearchResult", {}).get("SearchResultItems", [])
            
            countries = Counter()
            cities = Counter()
            
            for job in jobs:
                desc = job.get("MatchedObjectDescriptor", {})
                locations = desc.get("PositionLocation", [])
                
                if locations and isinstance(locations, list) and locations:
                    loc = locations[0] if isinstance(locations[0], dict) else {}
                    country = loc.get("CountryName", "Unknown")
                    city = loc.get("CityName", "Unknown")
                    
                    countries[country] += 1
                    if city:
                        cities[f"{city}, {country}"] += 1
            
            self.add_finding(
                "Geography",
                f"Found jobs in {len(countries)} countries, {len(cities)} cities",
                "SUCCESS"
            )
            
            # Top 10 countries
            self.add_finding("Geography", "\nTop 10 countries:", "INFO")
            for country, count in countries.most_common(10):
                self.add_finding("Geography", f"  • {country}: {count} jobs", "INFO")
            
            # Top 10 cities
            self.add_finding("Geography", "\nTop 10 cities:", "INFO")
            for city, count in cities.most_common(10):
                self.add_finding("Geography", f"  • {city}: {count} jobs", "INFO")
            
            return countries, cities
            
        except Exception as e:
            self.add_finding("Geography", f"Failed to analyze: {e}", "ERROR")
            return None, None
    
    def analyze_data_structure(self):
        """Understand what fields are available"""
        self.add_finding("Data Structure", "Analyzing available fields...", "INFO")
        
        payload = {
            "LanguageCode": "en",
            "SearchParameters": {
                "FirstItem": 1,
                "CountItem": 5,
                "MatchedObjectDescriptor": ["ID", "PositionTitle", "PositionURI", "PositionLocation", 
                                           "ApplyURI", "CareerLevel", "OrganizationName", "PublicationStartDate"]
            },
            "SearchCriteria": []
        }
        
        url = f"{self.API_URL}?data={json.dumps(payload)}"
        
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            
            jobs = data.get("SearchResult", {}).get("SearchResultItems", [])
            
            if jobs:
                sample_job = jobs[0]
                desc = sample_job.get("MatchedObjectDescriptor", {})
                
                self.add_finding("Data Structure", "\nSample job structure:", "INFO")
                self.add_finding("Data Structure", json.dumps(desc, indent=2)[:500], "INFO")
                
                # Check field presence across all 5 jobs
                field_presence = Counter()
                for job in jobs:
                    desc = job.get("MatchedObjectDescriptor", {})
                    for key in desc.keys():
                        field_presence[key] += 1
                
                self.add_finding("Data Structure", f"\nField presence (out of {len(jobs)} jobs):", "INFO")
                for field, count in field_presence.most_common():
                    pct = (count/len(jobs))*100
                    self.add_finding("Data Structure", f"  • {field}: {count}/{len(jobs)} ({pct:.0f}%)", "INFO")
            
        except Exception as e:
            self.add_finding("Data Structure", f"Failed: {e}", "ERROR")
    
    def test_description_sources(self):
        """Test where job descriptions come from"""
        self.add_finding("Descriptions", "Testing description sources...", "INFO")
        
        # Get one job with ApplyURI
        payload = {
            "LanguageCode": "en",
            "SearchParameters": {
                "FirstItem": 1,
                "CountItem": 1,
                "MatchedObjectDescriptor": ["PositionID", "PositionTitle", "ApplyURI"]
            },
            "SearchCriteria": []
        }
        
        url = f"{self.API_URL}?data={json.dumps(payload)}"
        
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            
            jobs = data.get("SearchResult", {}).get("SearchResultItems", [])
            
            if jobs:
                desc = jobs[0].get("MatchedObjectDescriptor", {})
                job_id = desc.get("PositionID")
                title = desc.get("PositionTitle")
                apply_uris = desc.get("ApplyURI", [])
                
                if apply_uris:
                    apply_url = apply_uris[0]
                    job_url = apply_url.replace('/apply', '') if apply_url.endswith('/apply') else apply_url
                    
                    self.add_finding("Descriptions", f"\nTesting job: {title} (ID: {job_id})", "INFO")
                    self.add_finding("Descriptions", f"ApplyURI: {apply_url}", "INFO")
                    self.add_finding("Descriptions", f"Job URL: {job_url}", "INFO")
                    
                    # Test job page
                    self.add_finding("Descriptions", "\n🔍 Fetching job page...", "INFO")
                    job_response = requests.get(job_url, timeout=15)
                    
                    if job_response.status_code == 200:
                        soup = BeautifulSoup(job_response.text, 'html.parser')
                        
                        # Check for description
                        meta_og = soup.find('meta', attrs={'property': 'og:description'})
                        meta_desc = soup.find('meta', attrs={'name': 'description'})
                        
                        if meta_og:
                            desc_text = meta_og.get('content', '')
                            self.add_finding(
                                "Descriptions",
                                f"✅ Found og:description ({len(desc_text)} chars)",
                                "SUCCESS"
                            )
                            self.add_finding("Descriptions", f"Preview: {desc_text[:200]}...", "INFO")
                        elif meta_desc:
                            desc_text = meta_desc.get('content', '')
                            self.add_finding(
                                "Descriptions",
                                f"✅ Found description meta ({len(desc_text)} chars)",
                                "SUCCESS"
                            )
                        else:
                            self.add_finding("Descriptions", "❌ No description meta tags found", "WARNING")
                    else:
                        self.add_finding(
                            "Descriptions",
                            f"❌ Job page returned {job_response.status_code}",
                            "ERROR"
                        )
        
        except Exception as e:
            self.add_finding("Descriptions", f"Failed: {e}", "ERROR")
    
    def check_url_patterns(self):
        """Identify different URL patterns used"""
        self.add_finding("URL Patterns", "Checking URL patterns...", "INFO")
        
        payload = {
            "LanguageCode": "en",
            "SearchParameters": {
                "FirstItem": 1,
                "CountItem": 50,
                "MatchedObjectDescriptor": ["PositionID", "ApplyURI"]
            },
            "SearchCriteria": []
        }
        
        url = f"{self.API_URL}?data={json.dumps(payload)}"
        
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            
            jobs = data.get("SearchResult", {}).get("SearchResultItems", [])
            
            url_patterns = Counter()
            
            for job in jobs:
                desc = job.get("MatchedObjectDescriptor", {})
                apply_uris = desc.get("ApplyURI", [])
                
                if apply_uris:
                    apply_url = apply_uris[0]
                    
                    # Extract domain pattern
                    if "workday" in apply_url.lower():
                        url_patterns["Workday"] += 1
                    elif "db-finanzberatung" in apply_url.lower():
                        url_patterns["DB Finanzberatung"] += 1
                    else:
                        url_patterns["Other"] += 1
            
            self.add_finding("URL Patterns", f"\nURL patterns found:", "INFO")
            for pattern, count in url_patterns.most_common():
                pct = (count/len(jobs))*100
                self.add_finding("URL Patterns", f"  • {pattern}: {count}/{len(jobs)} ({pct:.0f}%)", "INFO")
        
        except Exception as e:
            self.add_finding("URL Patterns", f"Failed: {e}", "ERROR")
    
    def run_full_interrogation(self):
        """Run all interrogation tests"""
        print("\n" + "="*70)
        print("🔍 DEUTSCHE BANK JOB BOARD INTERROGATION")
        print("="*70)
        print()
        
        # Test 1: API Limits
        print("\n1️⃣ Testing API Limits...")
        total, returned = self.test_api_limits()
        
        # Test 2: Geography
        print("\n2️⃣ Analyzing Geographic Distribution...")
        countries, cities = self.analyze_geographic_distribution()
        
        # Test 3: Data Structure
        print("\n3️⃣ Analyzing Data Structure...")
        self.analyze_data_structure()
        
        # Test 4: URL Patterns
        print("\n4️⃣ Checking URL Patterns...")
        self.check_url_patterns()
        
        # Test 5: Descriptions
        print("\n5️⃣ Testing Description Sources...")
        self.test_description_sources()
        
        # Final Report
        self.report()
        
        # Action Items
        print("\n" + "="*70)
        print("📋 RECOMMENDED ACTIONS")
        print("="*70)
        
        if total and returned:
            if returned < total:
                print(f"⚠️  API can return max {returned} jobs but {total} exist")
                print(f"   → Need to implement pagination or multiple requests")
            else:
                print(f"✅ Can fetch all {total} jobs in single request")
        
        print(f"\n💡 Next steps:")
        print(f"   1. Update import script with CountItem={returned if returned else 2000}")
        print(f"   2. Remove country filter to get all jobs")
        print(f"   3. Test on 10 jobs first")
        print(f"   4. Run full import")
        print(f"   5. Fetch descriptions for all jobs")


def main():
    parser = argparse.ArgumentParser(description='Interrogate job board APIs')
    parser.add_argument('--source', choices=['deutsche_bank'], default='deutsche_bank',
                       help='Which job source to interrogate')
    parser.add_argument('--deep', action='store_true',
                       help='Run deep analysis (slower, more detailed)')
    
    args = parser.parse_args()
    
    if args.source == 'deutsche_bank':
        interrogator = DeutscheBankInterrogator()
        interrogator.run_full_interrogation()
    
    print("\n✨ Interrogation complete!")


if __name__ == '__main__':
    main()
