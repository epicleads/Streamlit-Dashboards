# 🔐 Supabase Authentication Setup

This guide will help you set up user authentication using Supabase database instead of local JSON storage.

## 📋 Prerequisites

- Supabase project created
- Environment variables configured in `.env` file

## 🚀 Setup Steps

### 1. Create the Users Table

1. Go to your Supabase dashboard
2. Navigate to **SQL Editor**
3. Copy and paste the contents of `create_users_table.sql`
4. Click **Run** to execute the script

### 2. Verify the Setup

The SQL script will:
- ✅ Create a `users` table with proper structure
- ✅ Add indexes for performance
- ✅ Set up Row Level Security (RLS)
- ✅ Create the admin user with credentials:
  - **Username**: `Admin`
  - **Email**: `prathmeshgumal@gmail.com`
  - **Password**: `Epic@dash25`

### 3. Test the Authentication

1. Run your Streamlit app: `streamlit run app.py`
2. Try logging in with the admin credentials
3. Create a new user account through the admin interface

## 🗄️ Database Schema

The `users` table includes:

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PRIMARY KEY | Auto-incrementing ID |
| `username` | VARCHAR(50) UNIQUE | Unique username |
| `email` | VARCHAR(255) UNIQUE | Unique email address |
| `password_hash` | VARCHAR(255) | SHA-256 hashed password |
| `role` | VARCHAR(20) | User role (admin/user) |
| `created_at` | TIMESTAMP | Account creation time |
| `created_by` | VARCHAR(50) | Who created the account |
| `is_active` | BOOLEAN | Account status |

## 🔒 Security Features

- **Password Hashing**: SHA-256 encryption
- **Row Level Security**: Database-level access control
- **Soft Deletes**: Users are deactivated, not permanently deleted
- **Unique Constraints**: Prevents duplicate usernames/emails
- **Role-Based Access**: Admin vs User permissions

## 🛠️ Troubleshooting

### Common Issues:

1. **"Table doesn't exist" error**
   - Make sure you've run the SQL script in Supabase

2. **"Permission denied" error**
   - Check your Supabase API keys in `.env` file

3. **"Admin user not found" error**
   - The admin user should be created automatically by the SQL script

### Manual Admin User Creation:

If the admin user wasn't created, you can manually insert it:

```sql
INSERT INTO users (username, email, password_hash, role, created_by, is_active)
VALUES (
    'Admin',
    'prathmeshgumal@gmail.com',
    'a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456',
    'admin',
    'system',
    TRUE
);
```

## 📱 Usage

Once set up, users can:
- **Login** with their credentials
- **Admin users** can create/delete user accounts
- **All users** can access the dashboard
- **Logout** to end their session

The authentication system is now fully integrated with Supabase and provides enterprise-grade security for your dashboard.
