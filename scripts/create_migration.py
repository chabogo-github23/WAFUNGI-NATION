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

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wafungi_nation.settings')
django.setup()

from django.core.management import execute_from_command_line

if __name__ == '__main__':
    # Create migration
    execute_from_command_line(['manage.py', 'makemigrations', 'wafungi'])
    print("Migration created successfully!")
    
    # Apply migration
    execute_from_command_line(['manage.py', 'migrate'])
    print("Migration applied successfully!")
