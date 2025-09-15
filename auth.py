import streamlit as st
import hashlib
from datetime import datetime
from typing import Dict, Optional, List
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class UserManager:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.initialize_admin_user()
    
    def initialize_admin_user(self):
        """Initialize admin user if it doesn't exist"""
        try:
            # Check if admin user exists
            result = self.supabase.table("users").select("username").eq("username", "Admin").execute()
            
            if not result.data:
                # Create admin user
                admin_password_hash = self._hash_password("Epic@dash25")
                
                self.supabase.table("users").insert({
                    "username": "Admin",
                    "email": "prathmeshgumal@gmail.com",
                    "password_hash": admin_password_hash,
                    "role": "admin",
                    "created_by": "system",
                    "is_active": True
                }).execute()
        except Exception as e:
            st.error(f"Error initializing admin user: {e}")
    
    def _get_supabase_client(self):
        """Get Supabase client from session state"""
        return st.session_state.get('supabase_client')
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return self._hash_password(password) == password_hash
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user data if valid"""
        try:
            result = self.supabase.table("users").select("*").eq("username", username).eq("is_active", True).execute()
            
            if result.data:
                user = result.data[0]
                if self.verify_password(password, user["password_hash"]):
                    return user
            return None
        except Exception as e:
            st.error(f"Authentication error: {e}")
            return None
    
    def create_user(self, username: str, email: str, password: str, created_by: str) -> bool:
        """Create a new user account"""
        try:
            if not username or not email or not password:
                return False  # Invalid input
            
            # Check if username already exists
            username_check = self.supabase.table("users").select("username").eq("username", username).execute()
            if username_check.data:
                return False  # Username already exists
            
            # Check if email already exists
            email_check = self.supabase.table("users").select("email").eq("email", email).execute()
            if email_check.data:
                return False  # Email already exists
            
            # Create new user
            self.supabase.table("users").insert({
                "username": username,
                "email": email,
                "password_hash": self._hash_password(password),
                "role": "user",
                "created_by": created_by,
                "is_active": True
            }).execute()
            return True
        except Exception as e:
            st.error(f"Error creating user: {e}")
            return False
    
    def get_all_users(self) -> List[Dict]:
        """Get all users (admin only)"""
        try:
            result = self.supabase.table("users").select("*").eq("is_active", True).execute()
            return result.data
        except Exception as e:
            st.error(f"Error fetching users: {e}")
            return []
    
    def delete_user(self, username: str) -> bool:
        """Delete a user account (admin only)"""
        try:
            # Check if user exists and is not admin
            result = self.supabase.table("users").select("role").eq("username", username).execute()
            
            if result.data and result.data[0]["role"] != "admin":
                # Soft delete by setting is_active to False
                self.supabase.table("users").update({"is_active": False}).eq("username", username).execute()
                return True
            return False
        except Exception as e:
            st.error(f"Error deleting user: {e}")
            return False

def init_session_state(supabase_client: Client):
    """Initialize session state for authentication"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "user_manager" not in st.session_state:
        st.session_state.user_manager = UserManager(supabase_client)

def login_form():
    """Display login form"""
    st.markdown("## 🔐 Login to Dashboard")
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit_button = st.form_submit_button("Login", use_container_width=True)
        
        if submit_button:
            if username and password:
                user_manager = st.session_state.user_manager
                user = user_manager.authenticate_user(username, password)
                
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user = user
                    st.success(f"Welcome back, {user['username']}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password. Please try again.")
            else:
                st.error("Please enter both username and password.")

def admin_user_management():
    """Display user management interface for admin"""
    st.markdown("## 👥 User Management")
    
    user_manager = st.session_state.user_manager
    
    # Create new user form
    with st.expander("➕ Create New User Account", expanded=True):
        with st.form("create_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Username", placeholder="Enter username")
                new_email = st.text_input("Email", placeholder="Enter email address")
            
            with col2:
                new_password = st.text_input("Password", type="password", placeholder="Enter password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm password")
            
            create_button = st.form_submit_button("Create User", use_container_width=True)
            
            if create_button:
                if not all([new_username, new_email, new_password, confirm_password]):
                    st.error("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    success = user_manager.create_user(
                        new_username, 
                        new_email, 
                        new_password, 
                        st.session_state.user["username"]
                    )
                    
                    if success:
                        st.success(f"User '{new_username}' created successfully!")
                        st.rerun()
                    else:
                        st.error("Username or email already exists. Please choose different credentials.")
    
    # Display existing users
    st.markdown("### 📋 Existing Users")
    users = user_manager.get_all_users()
    
    if users:
        # Create a DataFrame for better display
        import pandas as pd
        
        users_data = []
        for user in users:
            users_data.append({
                "Username": user["username"],
                "Email": user["email"],
                "Role": user["role"].title(),
                "Created At": user["created_at"][:10],  # Show only date
                "Created By": user["created_by"]
            })
        
        df_users = pd.DataFrame(users_data)
        
        # Add delete buttons for each user (except admin)
        for idx, user in enumerate(users):
            if user["role"] != "admin":
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{user['username']}** ({user['email']}) - {user['role'].title()}")
                with col2:
                    if st.button("Delete", key=f"delete_{user['username']}", type="secondary"):
                        if user_manager.delete_user(user['username']):
                            st.success(f"User '{user['username']}' deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to delete user.")
                with col3:
                    st.write("")  # Empty column for spacing
    else:
        st.info("No users found.")

def logout():
    """Logout user"""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.success("Logged out successfully!")
    st.rerun()

def require_auth():
    """Decorator to require authentication for dashboard access"""
    if not st.session_state.authenticated:
        st.error("Please log in to access the dashboard.")
        login_form()
        return False
    return True

def require_admin():
    """Check if current user is admin"""
    if not st.session_state.authenticated:
        return False
    return st.session_state.user["role"] == "admin"

def show_sidebar_navigation():
    """Display sidebar navigation with user info and controls"""
    if st.session_state.authenticated:
        user = st.session_state.user
        
        with st.sidebar:
            # Add some custom CSS for better styling
            st.markdown("""
            <style>
            /* Style for buttons */
            .sidebar .stButton > button {
                width: 100%;
                margin-bottom: 0.5rem;
            }
            /* Fixed logout button at bottom */
            .logout-fixed {
                position: fixed;
                bottom: 20px;
                left: 20px;
                width: calc(25% - 40px);
                z-index: 999;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Dashboard button
            dashboard_active = not ("show_user_management" in st.session_state and st.session_state.show_user_management)
            if st.button("📊 Dashboard", use_container_width=True, type="primary" if dashboard_active else "secondary"):
                if "show_user_management" in st.session_state:
                    st.session_state.show_user_management = False
                st.rerun()
            
            # Manage Users button (admin only)
            if require_admin():
                users_active = "show_user_management" in st.session_state and st.session_state.show_user_management
                if st.button("👥 Manage Users", use_container_width=True, type="primary" if users_active else "secondary"):
                    st.session_state.show_user_management = True
                    st.rerun()
            
            # Logout button fixed at bottom
            st.markdown('<div class="logout-fixed">', unsafe_allow_html=True)
            if st.button("🚪 Logout", use_container_width=True, type="secondary"):
                logout()
            st.markdown('</div>', unsafe_allow_html=True)
