#!/usr/bin/env python3
"""
Location validation module for the requirements extraction system.

This module provides enhanced location validation with comprehensive German
patterns and variants, addressing the hallucination issues identified in
the daily reports.

Author: Investigation Team
Date: 2025-07-08
Version: 2.0
"""

import re
from typing import Dict, Any, Tuple


class EnhancedLocationValidator:
    """Enhanced location validator with comprehensive German patterns."""
    
    def __init__(self):
        # Comprehensive German location patterns
        self.german_cities = {
            'Frankfurt': ['Frankfurt', 'Frankfurt am Main', 'Frankfurt/Main', 'FFM'],
            'München': ['München', 'Munich', 'Muenchen'],
            'Berlin': ['Berlin'],
            'Hamburg': ['Hamburg'],
            'Köln': ['Köln', 'Cologne'],
            'Stuttgart': ['Stuttgart'],
            'Düsseldorf': ['Düsseldorf', 'Duesseldorf'],
            'Hannover': ['Hannover', 'Hanover'],
            'Dortmund': ['Dortmund'],
            'Essen': ['Essen'],
            'Leipzig': ['Leipzig'],
            'Bremen': ['Bremen'],
            'Dresden': ['Dresden'],
            'Nürnberg': ['Nürnberg', 'Nuremberg'],
            'Duisburg': ['Duisburg'],
            'Bochum': ['Bochum'],
            'Wuppertal': ['Wuppertal'],
            'Bonn': ['Bonn'],
            'Bielefeld': ['Bielefeld'],
            'Mannheim': ['Mannheim'],
            'Karlsruhe': ['Karlsruhe'],
            'Augsburg': ['Augsburg'],
            'Wiesbaden': ['Wiesbaden'],
            'Mönchengladbach': ['Mönchengladbach', 'Moenchengladbach'],
            'Gelsenkirchen': ['Gelsenkirchen'],
            'Braunschweig': ['Braunschweig', 'Brunswick'],
            'Chemnitz': ['Chemnitz'],
            'Kiel': ['Kiel'],
            'Aachen': ['Aachen'],
            'Halle': ['Halle'],
            'Magdeburg': ['Magdeburg'],
            'Freiburg': ['Freiburg'],
            'Krefeld': ['Krefeld'],
            'Lübeck': ['Lübeck', 'Luebeck'],
            'Oberhausen': ['Oberhausen'],
            'Erfurt': ['Erfurt'],
            'Mainz': ['Mainz'],
            'Rostock': ['Rostock'],
            'Kassel': ['Kassel'],
            'Hagen': ['Hagen'],
            'Potsdam': ['Potsdam'],
            'Saarbrücken': ['Saarbrücken', 'Saarbruecken'],
            'Hamm': ['Hamm'],
            'Mülheim': ['Mülheim', 'Muelheim'],
            'Ludwigshafen': ['Ludwigshafen'],
            'Leverkusen': ['Leverkusen'],
            'Oldenburg': ['Oldenburg'],
            'Solingen': ['Solingen'],
            'Osnabrück': ['Osnabrück', 'Osnabrueck'],
            'Heidelberg': ['Heidelberg'],
            'Darmstadt': ['Darmstadt'],
            'Paderborn': ['Paderborn'],
            'Regensburg': ['Regensburg'],
            'Würzburg': ['Würzburg', 'Wuerzburg'],
            'Ingolstadt': ['Ingolstadt'],
            'Heilbronn': ['Heilbronn'],
            'Ulm': ['Ulm'],
            'Göttingen': ['Göttingen', 'Goettingen'],
            'Wolfsburg': ['Wolfsburg'],
            'Recklinghausen': ['Recklinghausen'],
            'Pforzheim': ['Pforzheim'],
            'Offenbach': ['Offenbach'],
            'Bremerhaven': ['Bremerhaven'],
            'Remscheid': ['Remscheid'],
            'Fürth': ['Fürth', 'Fuerth'],
            'Reutlingen': ['Reutlingen'],
            'Moers': ['Moers'],
            'Koblenz': ['Koblenz'],
            'Bergisch Gladbach': ['Bergisch Gladbach'],
            'Erlangen': ['Erlangen'],
            'Siegen': ['Siegen'],
            'Trier': ['Trier'],
            'Jena': ['Jena'],
            'Hildesheim': ['Hildesheim'],
            'Cottbus': ['Cottbus'],
            'Salzgitter': ['Salzgitter'],
        }
        
        self.german_states = {
            'Hessen': ['Hessen', 'Hesse'],
            'Bayern': ['Bayern', 'Bavaria', 'Bavarian'],
            'Baden-Württemberg': ['Baden-Württemberg', 'Baden-Wuerttemberg', 'BW'],
            'Nordrhein-Westfalen': ['Nordrhein-Westfalen', 'NRW', 'North Rhine-Westphalia'],
            'Niedersachsen': ['Niedersachsen', 'Lower Saxony'],
            'Berlin': ['Berlin'],
            'Hamburg': ['Hamburg'],
            'Bremen': ['Bremen'],
            'Schleswig-Holstein': ['Schleswig-Holstein'],
            'Brandenburg': ['Brandenburg'],
            'Mecklenburg-Vorpommern': ['Mecklenburg-Vorpommern', 'Mecklenburg-Western Pomerania'],
            'Sachsen': ['Sachsen', 'Saxony'],
            'Sachsen-Anhalt': ['Sachsen-Anhalt', 'Saxony-Anhalt'],
            'Thüringen': ['Thüringen', 'Thuringia'],
            'Rheinland-Pfalz': ['Rheinland-Pfalz', 'Rhineland-Palatinate'],
            'Saarland': ['Saarland'],
        }
        
        self.country_variants = {
            'Deutschland': ['Deutschland', 'Germany', 'DE', 'German', 'deutsche'],
        }
    
    def validate_location(self, metadata_location: Dict[str, Any], job_text: str) -> Tuple[bool, float, str]:
        """
        Enhanced location validation with German variants.
        
        Args:
            metadata_location: Location metadata from job posting
            job_text: Full job description text
            
        Returns:
            - is_valid: bool indicating if location was found
            - confidence: float confidence score
            - details: string with validation details
        """
        city = metadata_location.get('city', '')
        state = metadata_location.get('state', '')
        country = metadata_location.get('country', '')
        
        validation_results = []
        
        # Check city with variants
        if city:
            city_variants = self.german_cities.get(city, [city])
            city_found = any(self._search_location_in_text(variant, job_text) for variant in city_variants)
            validation_results.append(('city', city, city_found))
        
        # Check state with variants
        if state:
            state_variants = self.german_states.get(state, [state])
            state_found = any(self._search_location_in_text(variant, job_text) for variant in state_variants)
            validation_results.append(('state', state, state_found))
        
        # Check country with variants
        if country:
            country_variants = self.country_variants.get(country, [country])
            country_found = any(self._search_location_in_text(variant, job_text) for variant in country_variants)
            validation_results.append(('country', country, country_found))
        
        # Calculate overall validation
        found_count = sum(1 for _, _, found in validation_results if found)
        total_count = len(validation_results)
        
        if total_count == 0:
            return False, 0.0, "No location information to validate"
        
        confidence = found_count / total_count
        
        # More lenient validation: if city is found, that's often sufficient for German jobs
        if city and validation_results[0][2]:  # City found
            confidence = max(confidence, 0.8)  # Boost confidence if city found
        
        is_valid = confidence >= 0.6  # Lower threshold for German locations
        
        details = f"Found {found_count}/{total_count} location components: " + \
                 ", ".join([f"{comp}:{loc}:{found}" for comp, loc, found in validation_results])
        
        return is_valid, confidence, details
    
    def _search_location_in_text(self, location: str, text: str) -> bool:
        """Search for location in text using regex with word boundaries."""
        # Create case-insensitive pattern with word boundaries
        pattern = r'\b' + re.escape(location) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))
