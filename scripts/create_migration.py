#!/usr/bin/env python
"""
Script to create database migration for EventApplication model
"""
import os
import sys
import django

# Add the project directory to Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wafungi_nation.settings')
django.setup()

from django.core.management import execute_from_command_line

def create_migration():
    """Create and apply database migrations"""
    print("Creating database migrations...")
    
    try:
        # Create migrations
        execute_from_command_line(['manage.py', 'makemigrations', 'wafungi'])
        print("✓ Migrations created successfully")
        
        # Apply migrations
        execute_from_command_line(['manage.py', 'migrate'])
        print("✓ Migrations applied successfully")
        
        print("\nDatabase updated with:")
        print("- EventApplication model for musician event applications")
        print("- PaymentTransaction model for M-Pesa payment tracking")
        print("- Updated Booking model with recipient phone methods")
        
    except Exception as e:
        print(f"✗ Error creating/applying migrations: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success = create_migration()
    if success:
        print("\n🎉 Database migration completed successfully!")
        print("\nNext steps:")
        print("1. Configure M-Pesa API credentials in settings.py")
        print("2. Install required packages: pip install reportlab")
        print("3. Test the payment flow with M-Pesa sandbox")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
