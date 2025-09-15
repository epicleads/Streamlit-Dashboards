"""
Test script to verify Supabase connection and users table
Run this to debug authentication issues
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import hashlib

def test_supabase_connection():
    """Test Supabase connection and users table"""
    
    # Load environment variables
    load_dotenv()
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    
    print("🔍 Testing Supabase Connection...")
    print(f"URL: {SUPABASE_URL}")
    print(f"Key: {SUPABASE_ANON_KEY[:20]}..." if SUPABASE_ANON_KEY else "Key: None")
    
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        print("❌ Error: SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env file")
        return False
    
    try:
        # Initialize Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print("✅ Supabase client created successfully")
        
        # Test 1: Check if users table exists
        print("\n🔍 Test 1: Checking if users table exists...")
        try:
            result = supabase.table("users").select("id").limit(1).execute()
            print("✅ Users table exists and is accessible")
            print(f"📊 Table has {len(result.data)} records")
        except Exception as e:
            print(f"❌ Users table error: {e}")
            print("💡 You need to run the SQL script in Supabase dashboard first!")
            return False
        
        # Test 2: Check for admin user
        print("\n🔍 Test 2: Checking for admin user...")
        try:
            result = supabase.table("users").select("*").eq("username", "Admin").execute()
            if result.data:
                admin_user = result.data[0]
                print("✅ Admin user found!")
                print(f"📋 Username: {admin_user['username']}")
                print(f"📋 Email: {admin_user['email']}")
                print(f"📋 Role: {admin_user['role']}")
                print(f"📋 Active: {admin_user['is_active']}")
                print(f"📋 Password Hash: {admin_user['password_hash'][:20]}...")
            else:
                print("❌ Admin user not found")
                print("💡 Creating admin user...")
                
                # Create admin user
                admin_password_hash = hashlib.sha256("Epic@dash25".encode()).hexdigest()
                print(f"🔐 Generated hash: {admin_password_hash}")
                
                insert_result = supabase.table("users").insert({
                    "username": "Admin",
                    "email": "prathmeshgumal@gmail.com",
                    "password_hash": admin_password_hash,
                    "role": "admin",
                    "created_by": "system",
                    "is_active": True
                }).execute()
                
                if insert_result.data:
                    print("✅ Admin user created successfully!")
                else:
                    print("❌ Failed to create admin user")
                    return False
        except Exception as e:
            print(f"❌ Admin user check error: {e}")
            return False
        
        # Test 3: Test authentication
        print("\n🔍 Test 3: Testing authentication...")
        try:
            result = supabase.table("users").select("*").eq("username", "Admin").eq("is_active", True).execute()
            if result.data:
                user = result.data[0]
                test_password = "Epic@dash25"
                test_hash = hashlib.sha256(test_password.encode()).hexdigest()
                
                if test_hash == user["password_hash"]:
                    print("✅ Password authentication successful!")
                else:
                    print("❌ Password authentication failed!")
                    print(f"🔐 Expected hash: {test_hash}")
                    print(f"🔐 Stored hash: {user['password_hash']}")
                    return False
            else:
                print("❌ No active admin user found")
                return False
        except Exception as e:
            print(f"❌ Authentication test error: {e}")
            return False
        
        print("\n🎉 All tests passed! Authentication should work now.")
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Supabase Authentication Setup...")
    test_supabase_connection()
