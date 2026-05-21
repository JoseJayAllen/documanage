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

    print("Creating default data...")
    create_default_data()
    print("Default data created successfully!")

    print("\nDatabase initialization complete!")
    print("\nDefault login credentials:")
    print("Admin: admin@documanage.com / admin123")
    print("Editor: editor@documanage.com / editor123")
    print("Viewer: viewer@documanage.com / viewer123")