"""
Setup script to create the users table in Supabase for authentication
Run this script once to set up the authentication system
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def setup_supabase_auth():
    """Set up the users table in Supabase"""
    
    # Initialize Supabase client
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        print("❌ Error: SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env file")
        return False
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        
        # Read the SQL file
        with open('create_users_table.sql', 'r') as f:
            sql_script = f.read()
        
        print("📝 Creating users table in Supabase...")
        
        # Execute the SQL script
        # Note: You'll need to run this SQL in your Supabase dashboard SQL editor
        # as the Python client doesn't support DDL operations directly
        
        print("✅ SQL script loaded successfully!")
        print("\n📋 Please follow these steps to complete the setup:")
        print("1. Go to your Supabase dashboard")
        print("2. Navigate to the SQL Editor")
        print("3. Copy and paste the contents of 'create_users_table.sql'")
        print("4. Execute the SQL script")
        print("5. The users table and admin user will be created automatically")
        
        print(f"\n📄 SQL Script Location: {os.path.abspath('create_users_table.sql')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up Supabase authentication: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Setting up Supabase Authentication...")
    setup_supabase_auth()
