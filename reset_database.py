#!/usr/bin/env python3
"""
Database Reset Script for Surplus-to-Sustain
This script safely deletes and recreates the database
"""

import os
import sys

def reset_database():
    print("\n" + "="*60)
    print(" DATABASE RESET SCRIPT")
    print("="*60)
    
    # Check if database exists
    if os.path.exists('database.db'):
        print("\n⚠️  Found existing database.db")
        response = input("Delete and recreate? (yes/no): ").lower()
        
        if response != 'yes':
            print("❌ Cancelled. Database not modified.")
            return
        
        try:
            os.remove('database.db')
            print("✓ Old database deleted")
        except Exception as e:
            print(f"❌ Error deleting database: {e}")
            return
    else:
        print("\n📝 No existing database found. Creating new one...")
    
    # Create new database
    try:
        print("\n🔨 Creating new database...")
        from app import init_db
        init_db()
        print("✓ Database created successfully!")
        
        # Verify tables
        import sqlite3
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        
        print(f"\n✓ Created {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        print("\n" + "="*60)
        print(" DATABASE READY!")
        print("="*60)
        print("\nYou can now run: python app.py")
        print("Or visit: http://localhost:8000\n")
        
    except Exception as e:
        print(f"\n❌ Error creating database: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure app.py is in the current directory")
        print("2. Make sure all dependencies are installed")
        print("3. Try running: pip install -r requirements-minimal.txt")

if __name__ == "__main__":
    reset_database()