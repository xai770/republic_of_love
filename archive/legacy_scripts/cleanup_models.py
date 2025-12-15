#!/usr/bin/env python3
"""
Clean up models table by removing models not available in Ollama
"""
import sqlite3
import subprocess
import json

def get_ollama_models():
    """Get list of available Ollama models"""
    try:
        result = subprocess.run(['ollama', 'list', '--format', 'json'], 
                              capture_output=True, text=True, check=True)
        models = json.loads(result.stdout)
        return set(model['name'] for model in models)
    except:
        # Fallback to parsing text output
        result = subprocess.run(['ollama', 'list'], 
                              capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        return set(line.split()[0] for line in lines if line.strip())

def get_db_models(db_path):
    """Get models from database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT model_name FROM models")
    db_models = set(row[0] for row in cursor.fetchall())
    conn.close()
    return db_models

def remove_unavailable_models(db_path, models_to_remove):
    """Remove models that are not available in Ollama"""
    if not models_to_remove:
        print("✅ No models to remove - database is in sync!")
        return
    
    print(f"🗄️  Removing {len(models_to_remove)} unavailable models from database...")
    
    # Try with timeout and WAL mode for better concurrency
    try:
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        
        for model in models_to_remove:
            print(f"   🗑️  Removing: {model}")
            conn.execute("DELETE FROM models WHERE model_name = ?", (model,))
        
        conn.commit()
        
        # Show remaining count
        cursor = conn.execute("SELECT COUNT(*) FROM models")
        remaining_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✅ Cleanup complete! {remaining_count} models remaining in database")
        
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print("❌ Database is locked - please close SQLite Browser and try again")
            print("💡 Or use the manual SQL commands printed below:")
            print("\n📝 Manual cleanup SQL:")
            for model in sorted(models_to_remove):
                print(f"DELETE FROM models WHERE model_name = '{model}';")
            print()
        else:
            raise

def add_missing_models(db_path, models_to_add):
    """Add models that exist in Ollama but not in database"""
    if not models_to_add:
        return
        
    print(f"➕ Adding {len(models_to_add)} missing models to database...")
    
    conn = sqlite3.connect(db_path)
    
    for model in models_to_add:
        print(f"   ➕ Adding: {model}")
        conn.execute("""
            INSERT INTO models (model_name, provider, enabled, updated_at) 
            VALUES (?, 'ollama', 1, CURRENT_TIMESTAMP)
        """, (model,))
    
    conn.commit()
    conn.close()

def main():
    db_path = "/home/xai/Documents/ty_learn/data/llmcore.db"
    
    print("🔍 Checking Ollama models vs database...")
    
    # Get current models
    ollama_models = get_ollama_models()
    db_models = get_db_models(db_path)
    
    print(f"📊 Ollama has {len(ollama_models)} models")
    print(f"🗄️  Database has {len(db_models)} models")
    
    # Find discrepancies
    models_to_remove = db_models - ollama_models  # In DB but not in Ollama
    models_to_add = ollama_models - db_models     # In Ollama but not in DB
    
    if models_to_remove:
        print(f"\n❌ Models to REMOVE (in DB but not available in Ollama):")
        for model in sorted(models_to_remove):
            print(f"   - {model}")
    
    if models_to_add:
        print(f"\n➕ Models to ADD (available in Ollama but not in DB):")
        for model in sorted(models_to_add):
            print(f"   + {model}")
    
    # Perform cleanup
    if models_to_remove or models_to_add:
        print(f"\n🛠️  Performing database sync...")
        remove_unavailable_models(db_path, models_to_remove)
        add_missing_models(db_path, models_to_add)
        
        print(f"\n✅ Database sync complete!")
    else:
        print(f"\n✅ Database is already in sync with Ollama!")

if __name__ == "__main__":
    main()