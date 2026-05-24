# init_db.py - Database initialization script
import os
import sys

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, create_default_data

with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("Database tables created successfully!")

    print("Creating default data (users, announcements)...")
    create_default_data()
    print("Default data created successfully!")

    print("\n" + "="*50)
    print("Database initialization complete!")
    print("="*50)
    print("\nDefault login credentials:")
    print("  Admin:  admin@documanage.com / admin123")
    print("  User:   user@documanage.com / user123")
    print("")
    print("\nRun the app with: python app.py")
    print("="*50)