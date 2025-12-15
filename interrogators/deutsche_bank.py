#!/usr/bin/env python3
"""
Deutsche Bank Job Board Interrogator
======================================

Specialized interrogator for https://careers.db.com
Analyzes API structure, limits, and data patterns.

Usage:
    python3 interrogators/deutsche_bank.py
    python3 interrogators/deutsche_bank.py --deep
    python3 interrogators/deutsche_bank.py --export findings.json

Author: Arden & xai
Date: 2025-11-07
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
import time
import argparse
from collections import Counter
from bs4 import BeautifulSoup
from typing import Tuple, Optional

from interrogators.base import JobSourceInterrogator


class DeutscheBankInterrogator(JobSourceInterrogator):
    """Specialized interrogator for Deutsche Bank career site"""
    
    API_URL = "https://api-deutschebank.beesite.de/search/"
    
    def __init__(self):
        super().__init__("Deutsche Bank")
        self.max_count = None
        self.total_jobs = None
        
    def test_api_limits(self) -> Tuple[Optional[int], Optional[int]]:
        """Test how many jobs we can fetch in one request
        
        Returns:
            Tuple of (total_jobs, max_fetch_size)
        """
        self.add_finding("API Limits", "Testing maximum fetch size...", "INFO")
        
        # First, test WITH Germany filter (Country=46) - the main use case
        self.add_finding("API Limits", "🔍 Testing with Germany filter (Country=46)...", "INFO")
        
        payload_germany = {
            "LanguageCode": "en",
            "SearchParameters": {
                "FirstItem": 1,
                "CountItem": 10,
                "MatchedObjectDescriptor": ["PositionID"]
            },
            "SearchCriteria": [
                {"CriterionName": "PositionLocation.Country", "CriterionValue": ["46"]}
            ]
        }
        
        try:
            url = f"{self.API_URL}?data={json.dumps(payload_germany)}"
            response = requests.get(url, timeout=30)
            data = response.json()
            
            germany_total = data.get("SearchResult", {}).get("SearchResultCount", 0)
            self.add_finding(
                "API Limits",
                f"📊 German jobs (Country=46): {germany_total}",
                "SUCCESS"
            )
        except Exception as e:
            self.add_finding("API Limits", f"Failed to get Germany count: {e}", "ERROR")
            germany_total = None
        
        # Also test WITHOUT filters to see baseline
        self.add_finding("API Limits", "🔍 Testing without filters (baseline)...", "INFO")
        
        payload_no_filter = {
            "LanguageCode": "en",
            "SearchParameters": {
                "FirstItem": 1,
                "CountItem": 10,
                "MatchedObjectDescriptor": ["PositionID"]
            }
        }
        
        try:
            url = f"{self.API_URL}?data={json.dumps(payload_no_filter)}"
            response = requests.get(url, timeout=30)
            data = response.json()
            
            no_filter_total = data.get("SearchResult", {}).get("SearchResultCount", 0)
            self.add_finding(
                "API Limits",
                f"📊 Jobs without filter: {no_filter_total}",
                "INFO"
            )
        except Exception as e:
            self.add_finding("API Limits", f"Failed to get no-filter count: {e}", "ERROR")
            no_filter_total = None
        
        # Use Germany total as our primary target
        true_total = germany_total if germany_total else no_filter_total
        
        # Now test increasing sizes to find the fetch limit (using Germany filter)
        self.add_finding("API Limits", "\n🔍 Testing maximum fetch size per request (German jobs)...", "INFO")
        test_sizes = [100, 500, 1000, 2000]
        last_successful = None
        
        for count in test_sizes:
            payload = {
                "LanguageCode": "en",
                "SearchParameters": {
                    "FirstItem": 1,
                    "CountItem": count,
                    "MatchedObjectDescriptor": ["PositionID"]
                },
                "SearchCriteria": [
                    {"CriterionName": "PositionLocation.Country", "CriterionValue": ["46"]}
                ]
            }
            
            url = f"{self.API_URL}?data={json.dumps(payload)}"
            
            try:
                response = requests.get(url, timeout=30)
                data = response.json()
                
                total = data.get("SearchResult", {}).get("SearchResultCount", 0)
                returned = len(data.get("SearchResult", {}).get("SearchResultItems", []))
                
                self.add_finding(
                    "API Limits",
                    f"CountItem={count} → returned {returned} jobs (total available: {total})",
                    "SUCCESS"
                )
                
                last_successful = (total, returned)
                
                # If we got all jobs or hit the limit, we can stop
                if returned >= total:
                    self.add_finding(
                        "API Limits",
                        f"✅ Can fetch ALL {total} jobs in single request!",
                        "SUCCESS"
                    )
                    self.total_jobs = total
                    self.max_count = count
                    return total, count
                elif returned < count:
                    self.add_finding(
                        "API Limits",
                        f"⚠️  API limit: max {returned} jobs per request (but {total} total exist)",
                        "WARNING"
                    )
                    self.total_jobs = total
                    self.max_count = returned
                    return total, returned
                    
            except Exception as e:
                self.add_finding("API Limits", f"CountItem={count} failed: {e}", "ERROR")
                if last_successful:
                    return last_successful
                break
        
        return last_successful if last_successful else (None, None)
    
    def analyze_geographic_distribution(self) -> Tuple[Optional[Counter], Optional[Counter]]:
        """Analyze job distribution by country and city
        
        Returns:
            Tuple of (countries_counter, cities_counter)
        """
        self.add_finding("Geography", "Analyzing job distribution by country...", "INFO")
        
        # Use the max count we discovered, or default to 5000
        fetch_count = self.max_count if self.max_count else 5000
        
        payload = {
            "LanguageCode": "en",
            "SearchParameters": {
                "FirstItem": 1,
                "CountItem": fetch_count,
                "MatchedObjectDescriptor": ["PositionID", "PositionLocation"]
            },
            "SearchCriteria": [
                {"CriterionName": "PositionLocation.Country", "CriterionValue": ["46"]}
            ]
        }
        
        url = f"{self.API_URL}?data={json.dumps(payload)}"
        
        try:
            response = requests.get(url, timeout=60)
            data = response.json()
            
            jobs = data.get("SearchResult", {}).get("SearchResultItems", [])
            
            if not jobs:
                self.add_finding("Geography", "❌ No jobs returned", "ERROR")
                return None, None
            
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
                    if city and city != "Unknown":
                        cities[f"{city}, {country}"] += 1
            
            self.add_finding(
                "Geography",
                f"Found jobs in {len(countries)} countries, {len(cities)} cities",
                "SUCCESS"
            )
            
            # Top 10 countries
            if countries:
                self.add_finding("Geography", "\n📍 Top 10 countries:", "INFO")
                for country, count in countries.most_common(10):
                    pct = (count / len(jobs)) * 100
                    self.add_finding("Geography", f"  • {country}: {count} jobs ({pct:.1f}%)", "INFO")
            
            # Top 10 cities
            if cities:
                self.add_finding("Geography", "\n🏙️  Top 10 cities:", "INFO")
                for city, count in cities.most_common(10):
                    pct = (count / len(jobs)) * 100
                    self.add_finding("Geography", f"  • {city}: {count} jobs ({pct:.1f}%)", "INFO")
            
            return countries, cities
            
        except Exception as e:
            self.add_finding("Geography", f"Failed to analyze: {e}", "ERROR")
            return None, None
    
    def analyze_data_structure(self):
        """Understand what fields are available and their completeness"""
        self.add_finding("Data Structure", "Analyzing available fields...", "INFO")
        
        # Test with a comprehensive list of possible fields
        all_possible_fields = [
            "PositionID", "PositionTitle", "PositionURI", "PositionLocation",
            "ApplyURI", "CareerLevel", "OrganizationName", "PublicationStartDate",
            "PositionFormattedDescription", "PositionSchedule", "PositionOfferingType",
            "PositionIndustry", "JobCategory", "CompanyIndustry", 
            "PublicationEndDate", "HiringOrganization", "PositionDepartment"
        ]
        
        payload = {
            "LanguageCode": "en",
            "SearchParameters": {
                "FirstItem": 1,
                "CountItem": 50,  # Get more samples for better analysis
                "MatchedObjectDescriptor": all_possible_fields
            },
            "SearchCriteria": [
                {"CriterionName": "PositionLocation.Country", "CriterionValue": ["46"]}
            ]
        }
        
        url = f"{self.API_URL}?data={json.dumps(payload)}"
        
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            
            jobs = data.get("SearchResult", {}).get("SearchResultItems", [])
            
            if not jobs:
                self.add_finding("Data Structure", "❌ No jobs returned", "ERROR")
                return
            
            # Sample job structure
            sample_job = jobs[0]
            desc = sample_job.get("MatchedObjectDescriptor", {})
            
            self.add_finding("Data Structure", "\n📋 Sample job structure:", "INFO")
            sample_json = json.dumps(desc, indent=2, ensure_ascii=False)
            # Show first 800 chars for more context
            preview = sample_json[:800] + ("..." if len(sample_json) > 800 else "")
            self.add_finding("Data Structure", preview, "INFO")
            
            # List all available fields
            self.add_finding("Data Structure", f"\n📝 Available fields in response:", "INFO")
            available_fields = list(desc.keys())
            self.add_finding("Data Structure", f"   Found {len(available_fields)} fields: {', '.join(sorted(available_fields))}", "INFO")
            
            # Field presence analysis
            field_presence = Counter()
            for job in jobs:
                desc = job.get("MatchedObjectDescriptor", {})
                for key in desc.keys():
                    if desc[key]:  # Count non-empty values
                        field_presence[key] += 1
            
            self.add_finding("Data Structure", f"\n📊 Field completeness (out of {len(jobs)} jobs):", "INFO")
            for field, count in field_presence.most_common():
                pct = (count/len(jobs))*100
                severity = "SUCCESS" if pct >= 95 else ("WARNING" if pct >= 80 else "ERROR")
                
                # Get sample value for this field (truncated)
                sample_value = ""
                for job in jobs:
                    val = job.get("MatchedObjectDescriptor", {}).get(field)
                    if val:
                        if isinstance(val, list):
                            sample_value = f" [list with {len(val)} items]"
                        elif isinstance(val, dict):
                            sample_value = f" [dict with {len(val)} keys]"
                        elif isinstance(val, str):
                            sample_value = f' (e.g., "{val[:30]}...")'
                        else:
                            sample_value = f" (e.g., {val})"
                        break
                
                self.add_finding("Data Structure", f"  • {field}: {count}/{len(jobs)} ({pct:.0f}%){sample_value}", severity)
            
        except Exception as e:
            self.add_finding("Data Structure", f"Failed: {e}", "ERROR")
    
    def test_description_sources(self):
        """Test where job descriptions come from (API vs separate pages)"""
        self.add_finding("Descriptions", "Testing description sources...", "INFO")
        
        # Get one job with ApplyURI
        payload = {
            "LanguageCode": "en",
            "SearchParameters": {
                "FirstItem": 1,
                "CountItem": 3,  # Test multiple jobs
                "MatchedObjectDescriptor": ["PositionID", "PositionTitle", "ApplyURI", "PositionFormattedDescription"]
            },
            "SearchCriteria": [
                {"CriterionName": "PositionLocation.Country", "CriterionValue": ["46"]}
            ]
        }
        
        url = f"{self.API_URL}?data={json.dumps(payload)}"
        
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            
            jobs = data.get("SearchResult", {}).get("SearchResultItems", [])
            
            if not jobs:
                self.add_finding("Descriptions", "❌ No jobs returned for testing", "ERROR")
                return
            
            # Check if descriptions are in API response
            desc = jobs[0].get("MatchedObjectDescriptor", {})
            api_desc = desc.get("PositionFormattedDescription")
            
            if api_desc:
                self.add_finding(
                    "Descriptions",
                    f"✅ Descriptions available in API ({len(api_desc)} chars)",
                    "SUCCESS"
                )
            else:
                self.add_finding(
                    "Descriptions",
                    "ℹ️  No descriptions in API response - need to fetch from job pages",
                    "INFO"
                )
            
            # Test fetching from job page
            for i, job in enumerate(jobs[:2], 1):  # Test first 2 jobs
                desc = job.get("MatchedObjectDescriptor", {})
                job_id = desc.get("PositionID")
                title = desc.get("PositionTitle")
                apply_uris = desc.get("ApplyURI", [])
                
                if apply_uris:
                    apply_url = apply_uris[0]
                    # Remove /apply suffix if present
                    job_url = apply_url.replace('/apply', '') if apply_url.endswith('/apply') else apply_url
                    
                    self.add_finding("Descriptions", f"\n🔍 Testing job {i}: {title[:50]}...", "INFO")
                    self.add_finding("Descriptions", f"   URL: {job_url}", "INFO")
                    
                    try:
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
                                    f"   ✅ Found og:description ({len(desc_text)} chars)",
                                    "SUCCESS"
                                )
                            elif meta_desc:
                                desc_text = meta_desc.get('content', '')
                                self.add_finding(
                                    "Descriptions",
                                    f"   ✅ Found description meta ({len(desc_text)} chars)",
                                    "SUCCESS"
                                )
                            else:
                                self.add_finding(
                                    "Descriptions",
                                    "   ⚠️  No description meta tags found",
                                    "WARNING"
                                )
                        else:
                            self.add_finding(
                                "Descriptions",
                                f"   ❌ Job page returned {job_response.status_code}",
                                "ERROR"
                            )
                    except Exception as e:
                        self.add_finding("Descriptions", f"   ❌ Failed to fetch: {e}", "ERROR")
                    
                    time.sleep(0.5)  # Be polite
        
        except Exception as e:
            self.add_finding("Descriptions", f"Failed: {e}", "ERROR")
    
    def check_url_patterns(self):
        """Identify different URL patterns used"""
        self.add_finding("URL Patterns", "Analyzing URL patterns...", "INFO")
        
        # Use discovered max count
        fetch_count = min(self.max_count if self.max_count else 100, 100)
        
        payload = {
            "LanguageCode": "en",
            "SearchParameters": {
                "FirstItem": 1,
                "CountItem": fetch_count,
                "MatchedObjectDescriptor": ["PositionID", "ApplyURI"]
            },
            "SearchCriteria": [
                {"CriterionName": "PositionLocation.Country", "CriterionValue": ["46"]}
            ]
        }
        
        url = f"{self.API_URL}?data={json.dumps(payload)}"
        
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            
            jobs = data.get("SearchResult", {}).get("SearchResultItems", [])
            
            url_patterns = Counter()
            apply_suffix_count = 0
            
            for job in jobs:
                desc = job.get("MatchedObjectDescriptor", {})
                apply_uris = desc.get("ApplyURI", [])
                
                if apply_uris:
                    apply_url = apply_uris[0]
                    
                    # Check for /apply suffix
                    if apply_url.endswith('/apply'):
                        apply_suffix_count += 1
                    
                    # Categorize by domain
                    if "workday" in apply_url.lower():
                        url_patterns["Workday"] += 1
                    elif "db-finanzberatung" in apply_url.lower():
                        url_patterns["DB Finanzberatung"] += 1
                    else:
                        url_patterns["Other"] += 1
            
            total = len(jobs)
            
            self.add_finding("URL Patterns", f"\n🔗 URL patterns found:", "INFO")
            for pattern, count in url_patterns.most_common():
                pct = (count/total)*100
                self.add_finding("URL Patterns", f"  • {pattern}: {count}/{total} ({pct:.0f}%)", "INFO")
            
            # Check /apply suffix
            if apply_suffix_count > 0:
                pct = (apply_suffix_count/total)*100
                self.add_finding(
                    "URL Patterns",
                    f"\n⚠️  {apply_suffix_count}/{total} ({pct:.0f}%) URLs end with /apply",
                    "WARNING"
                )
                self.add_finding(
                    "URL Patterns",
                    "   → Import script MUST remove /apply suffix to get job page!",
                    "WARNING"
                )
        
        except Exception as e:
            self.add_finding("URL Patterns", f"Failed: {e}", "ERROR")
    
    def generate_recommendations(self) -> list:
        """Generate actionable recommendations based on findings"""
        recommendations = []
        
        if self.total_jobs and self.max_count:
            if self.max_count >= self.total_jobs:
                recommendations.append(f"✅ Use CountItem={self.max_count} to fetch all {self.total_jobs} jobs in single request")
            else:
                recommendations.append(f"⚠️  Use CountItem={self.max_count} and implement pagination for {self.total_jobs} total jobs")
        
        # Check findings for specific recommendations
        has_apply_suffix = any(
            '/apply' in f['message'] 
            for f in self.findings 
            if f['category'] == 'URL Patterns'
        )
        
        if has_apply_suffix:
            recommendations.append("🔧 Transform ApplyURI: remove /apply suffix before storing")
        
        # Check if descriptions are in API
        api_has_descriptions = any(
            'available in API' in f['message']
            for f in self.findings
            if f['category'] == 'Descriptions' and f['severity'] == 'SUCCESS'
        )
        
        if not api_has_descriptions:
            recommendations.append("📄 Descriptions NOT in API - build separate fetcher for job pages")
            recommendations.append("🕐 Rate limit description fetching to ~5 req/s")
        
        recommendations.append("🧪 Test import with 10 jobs first")
        recommendations.append("✅ Verify no duplicates in database after import")
        
        return recommendations
    
    def run_full_interrogation(self):
        """Run all interrogation tests"""
        print("\n" + "="*70)
        print("🔍 DEUTSCHE BANK JOB BOARD INTERROGATION")
        print("="*70)
        print()
        
        # Test 1: API Limits (CRITICAL - do this first!)
        print("1️⃣  Testing API Limits...")
        self.test_api_limits()
        
        # Test 2: Geography
        print("\n2️⃣  Analyzing Geographic Distribution...")
        self.analyze_geographic_distribution()
        
        # Test 3: Data Structure
        print("\n3️⃣  Analyzing Data Structure...")
        self.analyze_data_structure()
        
        # Test 4: URL Patterns
        print("\n4️⃣  Checking URL Patterns...")
        self.check_url_patterns()
        
        # Test 5: Descriptions
        print("\n5️⃣  Testing Description Sources...")
        self.test_description_sources()
        
        # Final Report
        self.report()
        
        # Recommendations
        print("\n" + "="*70)
        print("📋 RECOMMENDED ACTIONS")
        print("="*70)
        recommendations = self.generate_recommendations()
        for rec in recommendations:
            print(f"  {rec}")
        
        # Summary stats
        summary = self.generate_summary()
        print("\n" + "="*70)
        print("📊 SUMMARY")
        print("="*70)
        print(f"  Duration: {summary['duration_seconds']:.1f} seconds")
        print(f"  Findings: {summary['total_findings']} total")
        print(f"    ✅ Success: {summary['successes']}")
        print(f"    ⚠️  Warnings: {summary['warnings']}")
        print(f"    ❌ Errors: {summary['errors']}")


def main():
    parser = argparse.ArgumentParser(
        description='Interrogate Deutsche Bank job board API',
        epilog='Example: python3 interrogators/deutsche_bank.py --export findings.json'
    )
    parser.add_argument('--export', type=str, metavar='FILE',
                       help='Export findings to JSON file')
    parser.add_argument('--deep', action='store_true',
                       help='Run deep analysis (more comprehensive tests)')
    
    args = parser.parse_args()
    
    interrogator = DeutscheBankInterrogator()
    interrogator.run_full_interrogation()
    
    if args.export:
        interrogator.export_report(args.export)
        print(f"\n✅ Findings exported to {args.export}")
    
    print("\n✨ Interrogation complete!")


if __name__ == '__main__':
    main()
