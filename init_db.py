import os
from app import app, db
from flask import Flask
import sys

def init_db():
    try:
        with app.app_context():
            # Create all database tables
            db.create_all()
            
            print("✅ Database tables created successfully!")
            return True
    except Exception as e:
        print(f"❌ Error creating database tables: {str(e)}", file=sys.stderr)
        return False

if __name__ == "__main__":
    # Get the environment
    env = os.getenv('FLASK_ENV', 'development')
    print(f"🚀 Initializing database in {env} environment...")
    
    success = init_db()
    sys.exit(0 if success else 1) 
