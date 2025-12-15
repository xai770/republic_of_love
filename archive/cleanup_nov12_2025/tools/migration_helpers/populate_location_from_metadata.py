#!/usr/bin/env python3
"""
Populate location_city and location_country from source_metadata->>'OrganizationName'
For Deutsche Bank jobs that have OrganizationName but missing structured location fields.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.database import get_connection

# City → Country mapping (based on Deutsche Bank's global presence)
CITY_TO_COUNTRY = {
    # India (top location)
    'Pune': 'India',
    'Bangalore': 'India',
    'Mumbai': 'India',
    'Jaipur': 'India',
    'Chennai': 'India',
    'New Delhi': 'India',
    'Ahmedabad': 'India',
    'Gurgaon': 'India',
    'Kolkata': 'India',
    'Vellore': 'India',
    'Moradabad': 'India',
    'Gandhinagar': 'India',
    
    # Romania
    'Bucharest': 'Romania',
    
    # USA
    'New York': 'United States',
    'Cary': 'United States',
    'Jacksonville': 'United States',
    'San Francisco': 'United States',
    'Santa Ana': 'United States',
    'Los Angeles': 'United States',
    'Arlington': 'United States',
    'Miami': 'United States',
    'Chicago': 'United States',
    
    # UK
    'London': 'United Kingdom',
    'Birmingham': 'United Kingdom',
    
    # Philippines
    'Manila': 'Philippines',
    'Taguig': 'Philippines',
    
    # Singapore
    'Singapore': 'Singapore',
    
    # Luxembourg
    'Luxembourg': 'Luxembourg',
    
    # Japan
    'Tokyo': 'Japan',
    
    # Hong Kong
    'Hong Kong': 'Hong Kong',
    
    # Italy
    'Milano': 'Italy',
    'Brescia': 'Italy',
    'Modena': 'Italy',
    'Genova': 'Italy',
    'Pesaro': 'Italy',
    'Bologna': 'Italy',
    'Bulgarograsso': 'Italy',
    'Bellano': 'Italy',
    'Padova': 'Italy',
    'Caserta': 'Italy',
    'Olginate': 'Italy',
    'Imperia': 'Italy',
    'Asti': 'Italy',
    'Savona': 'Italy',
    'Trento': 'Italy',
    'Roma': 'Italy',
    'Cagliari': 'Italy',
    'Lecco': 'Italy',
    'Parma': 'Italy',
    'Bari': 'Italy',
    'Desenzano del Garda': 'Italy',
    
    # Spain
    'Madrid': 'Spain',
    'Barcelona': 'Spain',
    'El Prat de Llobregat': 'Spain',
    'Marbella': 'Spain',
    'Valladolid': 'Spain',
    'Alicante': 'Spain',
    'Murcia': 'Spain',
    'Pamplona': 'Spain',
    'Ibiza': 'Spain',
    'Malaga': 'Spain',
    'Valencia': 'Spain',
    
    # Australia
    'Sydney': 'Australia',
    
    # Brazil
    'Sao Paulo': 'Brazil',
    
    # Malaysia
    'Kuala Lumpur': 'Malaysia',
    
    # Switzerland
    'Zürich': 'Switzerland',
    'Geneva': 'Switzerland',
    
    # Netherlands
    'Amsterdam': 'Netherlands',
    
    # Belgium
    'Brussels': 'Belgium',
    'Liege': 'Belgium',
    'Sint-Niklaas': 'Belgium',
    'Kraainem': 'Belgium',
    'Hasselt': 'Belgium',
    'Sint-Pieters-Woluwe': 'Belgium',
    'Brasschaat': 'Belgium',
    
    # France
    'Paris': 'France',
    
    # Poland
    'Warszawa': 'Poland',
    
    # China
    'Tianjin': 'China',
    'Shanghai': 'China',
    'Beijing': 'China',
    
    # Taiwan
    'Taipei': 'Taiwan',
    
    # South Korea
    'Seoul': 'South Korea',
    
    # Germany
    'Frankfurt': 'Germany',
    'Berlin': 'Germany',
    'Dresden': 'Germany',
    'Hamburg': 'Germany',
    'Bonn': 'Germany',
    'Langenhagen': 'Germany',
    
    # Indonesia
    'Jakarta': 'Indonesia',
    
    # Saudi Arabia
    'Riyadh': 'Saudi Arabia',
    
    # Ukraine
    'Kiev': 'Ukraine',
    
    # Ireland
    'Dublin': 'Ireland',
    
    # Mexico
    'Mexico City': 'Mexico',
    
    # Thailand
    'Bangkok': 'Thailand',
    
    # Turkey
    'Istanbul': 'Turkey',
    
    # UAE
    'Dubai': 'United Arab Emirates',
    'Abu Dhabi': 'United Arab Emirates',
    
    # Hungary
    'Budapest': 'Hungary',
    
    # Portugal
    'Lisbon': 'Portugal',
    
    # Sweden
    'Stockholm': 'Sweden',
    
    # Pakistan
    'Karachi': 'Pakistan',
    
    # Vietnam
    'Ho Chi Minh': 'Vietnam',
    
    # Argentina
    'Argentina, Buenos Aires, Offsite': 'Argentina',
    
    # Special cases
    'Home': None,  # Remote work
}


def populate_locations(dry_run=True):
    """
    Populate location_city and location_country from source_metadata->>'OrganizationName'
    
    Args:
        dry_run: If True, only show what would be updated without making changes
    """
    conn = get_connection()
    cur = conn.cursor()
    
    print("\n" + "="*80)
    print("🌍 LOCATION POPULATION FROM source_metadata")
    print("="*80 + "\n")
    
    # Get jobs that need location parsing
    cur.execute("""
        SELECT 
            posting_id,
            job_title,
            source_metadata->>'OrganizationName'
        FROM postings
        WHERE source_id = 1
          AND location_city IS NULL
          AND source_metadata->>'OrganizationName' IS NOT NULL
        ORDER BY posting_id
    """)
    
    jobs_to_update = cur.fetchall()
    total_jobs = len(jobs_to_update)
    
    print(f"📊 Found {total_jobs} jobs with OrganizationName but missing location_city\n")
    
    if total_jobs == 0:
        print("✅ All jobs already have location data!")
        cur.close()
        conn.close()
        return
    
    # Statistics
    mapped_count = 0
    unmapped_count = 0
    unmapped_cities = set()
    updates_by_country = {}
    
    updates = []
    
    for row in jobs_to_update:
        posting_id = row['posting_id']
        job_title = row['job_title']
        city_name = row['?column?']  # Unaliased column from JSONB extraction
        
        if city_name in CITY_TO_COUNTRY:
            country = CITY_TO_COUNTRY[city_name]
            if country:  # Skip "Home" (remote)
                updates.append((city_name, country, posting_id))
                mapped_count += 1
                updates_by_country[country] = updates_by_country.get(country, 0) + 1
            else:
                unmapped_count += 1
                unmapped_cities.add(city_name)
        else:
            unmapped_count += 1
            unmapped_cities.add(city_name)
    
    # Display statistics
    print(f"✅ Mapped: {mapped_count}/{total_jobs} jobs ({100.0*mapped_count/total_jobs:.1f}%)")
    print(f"⚠️  Unmapped: {unmapped_count}/{total_jobs} jobs ({100.0*unmapped_count/total_jobs:.1f}%)")
    
    if unmapped_cities:
        print(f"\n⚠️  Unmapped cities ({len(unmapped_cities)}):")
        for city in sorted(unmapped_cities):
            print(f"   - {city}")
    
    print(f"\n📊 Updates by country:")
    for country, count in sorted(updates_by_country.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {country}: {count} jobs")
    
    if dry_run:
        print("\n🔍 DRY RUN - No changes made to database")
        print("   Run with --execute to apply updates")
    else:
        print(f"\n🚀 Executing {len(updates)} updates...")
        
        for i, (city, country, posting_id) in enumerate(updates, 1):
            cur.execute("""
                UPDATE postings
                SET location_city = %s,
                    location_country = %s
                WHERE posting_id = %s
            """, (city, country, posting_id))
            
            if i % 100 == 0:
                print(f"   ✅ Updated {i}/{len(updates)} jobs...")
        
        conn.commit()
        print(f"\n✅ Successfully updated {len(updates)} jobs!")
        
        # Verify
        cur.execute("""
            SELECT COUNT(*) as total
            FROM postings 
            WHERE source_id = 1 AND location_city IS NOT NULL
        """)
        result = cur.fetchone()
        total_with_location = result['total']
        print(f"📊 Total jobs with location: {total_with_location}/1801 ({100.0*total_with_location/1801:.1f}%)")
    
    cur.close()
    conn.close()
    
    print("\n" + "="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Populate location fields from source_metadata')
    parser.add_argument('--execute', action='store_true', 
                       help='Execute updates (default is dry-run)')
    
    args = parser.parse_args()
    
    populate_locations(dry_run=not args.execute)
