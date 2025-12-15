#!/usr/bin/env python3
"""
Export Skill Hierarchy to OWL Format for Protégé
================================================

Exports skill_aliases and skill_hierarchy tables to OWL 2.0 format
that can be opened and visualized in Protégé.

Created: 2025-10-29
Author: Arden
"""

import psycopg2
from datetime import datetime
from html import escape

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'database': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

def sanitize_class_name(skill_name):
    """Convert skill name to valid OWL class name"""
    sanitized = skill_name.replace(' ', '_').replace('-', '_').replace('/', '_')
    sanitized = ''.join(c for c in sanitized if c.isalnum() or c == '_')
    return sanitized

def fetch_all_skills(conn):
    """Fetch all skills from skill_aliases"""
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            skill,
            skill_alias,
            display_name,
            language,
            confidence,
            created_by,
            notes
        FROM skill_aliases
        ORDER BY skill
    """)
    
    columns = [desc[0] for desc in cur.description]
    skills = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    
    return skills

def fetch_hierarchy(conn):
    """Fetch all hierarchical relationships"""
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            skill,
            parent_skill,
            strength,
            created_by,
            notes
        FROM skill_hierarchy
        ORDER BY parent_skill, skill
    """)
    
    columns = [desc[0] for desc in cur.description]
    relationships = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    
    return relationships

def generate_owl_xml(skills, relationships):
    """Generate OWL/XML content as string"""
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    base_uri = "http://skillbridge.base-yoga.com/ontology"
    
    xml = []
    
    # XML and RDF header
    xml.append('<?xml version="1.0" encoding="UTF-8"?>')
    xml.append('<rdf:RDF')
    xml.append('    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"')
    xml.append('    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"')
    xml.append('    xmlns:owl="http://www.w3.org/2002/07/owl#"')
    xml.append('    xmlns:xsd="http://www.w3.org/2001/XMLSchema#"')
    xml.append(f'    xmlns:skills="{base_uri}#"')
    xml.append(f'    xml:base="{base_uri}">')
    xml.append('')
    
    # Ontology declaration
    xml.append(f'  <owl:Ontology rdf:about="{base_uri}">')
    xml.append(f'    <owl:versionInfo>{timestamp}</owl:versionInfo>')
    xml.append('    <rdfs:comment>SkillBridge Skill Taxonomy from base_yoga database</rdfs:comment>')
    xml.append('  </owl:Ontology>')
    xml.append('')
    
    # Annotation properties
    xml.append('  <!-- Custom Annotation Properties -->')
    xml.append('')
    
    xml.append('  <owl:AnnotationProperty rdf:about="#confidence">')
    xml.append('    <rdfs:label>confidence</rdfs:label>')
    xml.append('  </owl:AnnotationProperty>')
    xml.append('')
    
    xml.append('  <owl:AnnotationProperty rdf:about="#language">')
    xml.append('    <rdfs:label>language</rdfs:label>')
    xml.append('  </owl:AnnotationProperty>')
    xml.append('')
    
    xml.append('  <owl:AnnotationProperty rdf:about="#hierarchyStrength">')
    xml.append('    <rdfs:label>hierarchy strength</rdfs:label>')
    xml.append('  </owl:AnnotationProperty>')
    xml.append('')
    
    xml.append('  <owl:AnnotationProperty rdf:about="#createdBy">')
    xml.append('    <rdfs:label>created by</rdfs:label>')
    xml.append('  </owl:AnnotationProperty>')
    xml.append('')
    
    xml.append('  <owl:AnnotationProperty rdf:about="#skillAlias">')
    xml.append('    <rdfs:label>skill alias</rdfs:label>')
    xml.append('  </owl:AnnotationProperty>')
    xml.append('')
    
    # Build hierarchy map for efficient lookup
    hierarchy_map = {}
    for rel in relationships:
        child = rel['skill']
        if child not in hierarchy_map:
            hierarchy_map[child] = []
        hierarchy_map[child].append(rel)
    
    # Skill classes
    xml.append('  <!-- Skill Classes -->')
    xml.append('')
    
    for skill_data in skills:
        skill_name = skill_data['skill']
        class_name = sanitize_class_name(skill_name)
        
        xml.append(f'  <owl:Class rdf:about="#{class_name}">')
        
        # Display name as label
        if skill_data.get('display_name'):
            display_name = escape(str(skill_data['display_name']))
            xml.append(f'    <rdfs:label>{display_name}</rdfs:label>')
        
        # Original skill alias
        if skill_data.get('skill_alias'):
            skill_alias = escape(str(skill_data['skill_alias']))
            xml.append(f'    <skills:skillAlias>{skill_alias}</skills:skillAlias>')
        
        # Language
        if skill_data.get('language'):
            xml.append(f'    <skills:language>{skill_data["language"]}</skills:language>')
        
        # Confidence
        if skill_data.get('confidence'):
            xml.append(f'    <skills:confidence>{skill_data["confidence"]}</skills:confidence>')
        
        # Created by
        if skill_data.get('created_by'):
            created_by = escape(str(skill_data['created_by']))
            xml.append(f'    <skills:createdBy>{created_by}</skills:createdBy>')
        
        # Notes as comment
        if skill_data.get('notes'):
            notes = escape(str(skill_data['notes']))
            xml.append(f'    <rdfs:comment>{notes}</rdfs:comment>')
        
        # Parent relationships (SubClassOf)
        if skill_name in hierarchy_map:
            for rel in hierarchy_map[skill_name]:
                parent_class = sanitize_class_name(rel['parent_skill'])
                strength = rel.get('strength', 1.0)
                xml.append(f'    <rdfs:subClassOf rdf:resource="#{parent_class}"/>')
                # Note: OWL doesn't have a standard way to annotate axioms simply,
                # so strength information is somewhat lost in this simple format
        
        xml.append('  </owl:Class>')
        xml.append('')
    
    # Close RDF
    xml.append('</rdf:RDF>')
    
    return '\n'.join(xml)

def export_to_owl(output_file='skills_hierarchy.owl'):
    """Main export function"""
    
    print("=" * 70)
    print("🦉 Exporting Skill Hierarchy to OWL Format")
    print("=" * 70)
    print(f"Output file: {output_file}\n")
    
    # Connect to database
    print("📊 Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Fetch data
    print("📥 Fetching skills...")
    skills = fetch_all_skills(conn)
    print(f"   Found {len(skills)} skills")
    
    print("📥 Fetching hierarchy...")
    relationships = fetch_hierarchy(conn)
    print(f"   Found {len(relationships)} parent-child relationships\n")
    
    conn.close()
    
    # Generate OWL XML
    print("🔨 Building OWL ontology...")
    owl_content = generate_owl_xml(skills, relationships)
    
    # Write to file
    print(f"\n💾 Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(owl_content)
    
    # Statistics
    import os
    size_kb = os.path.getsize(output_file) / 1024
    
    print("\n" + "=" * 70)
    print("✅ Export Complete!")
    print("=" * 70)
    print(f"📄 File: {output_file}")
    print(f"📊 Classes: {len(skills)}")
    print(f"🔗 SubClassOf axioms: {len(relationships)}")
    print(f"🏷️  Annotation properties: 5")
    print(f"💾 File size: {size_kb:.1f} KB")
    
    print("\n📖 How to use:")
    print("   1. Install Protégé: https://protege.stanford.edu/")
    print("   2. Open Protégé")
    print(f"   3. File → Open → Select {output_file}")
    print("   4. View → Class hierarchy to see the tree")
    print("   5. Window → Tabs → OntoGraf for graph visualization")
    
    print("\n🎨 Recommended Protégé plugins:")
    print("   - OntoGraf: Interactive graph visualization")
    print("   - OWLViz: Hierarchical tree visualization (uses Graphviz)")
    
    print("\n💡 Tips for Protégé:")
    print("   - Click the 'Entities' tab to see all skills")
    print("   - Select a skill to see its parents/children")
    print("   - Use the 'DL Query' tab to query the ontology")
    print("   - Right-click skills to expand/collapse hierarchy")
    
    print("\n" + "=" * 70)
    
    return output_file

if __name__ == "__main__":
    try:
        output_file = export_to_owl('/home/xai/Documents/ty_learn/skills_hierarchy.owl')
        print(f"\n✅ Success! Open {output_file} in Protégé to explore the hierarchy.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
