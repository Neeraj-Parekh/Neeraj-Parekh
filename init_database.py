"""
Database Initialization Script
Creates all necessary tables for FocusFlow Enterprise
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.core.database import engine, create_tables
from backend.app.models.models import Base

def initialize_database():
    """Initialize the database with all tables"""
    print("🗄️  Creating database tables...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
        
        # List created tables
        inspector = engine.dialect.get_table_names(engine.connect())
        print(f"📊 Created {len(inspector)} tables:")
        for table in inspector:
            print(f"   • {table}")
            
    except Exception as e:
        print(f"❌ Failed to create database: {e}")
        raise

if __name__ == "__main__":
    initialize_database()