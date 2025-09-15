-- Simple users table creation for authentication
-- Run this in your Supabase SQL Editor

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE
);

-- Insert the admin user with the correct password hash
-- Password: Epic@dash25
-- Hash: 882b93331769ed8e162cfe6751b376b552b42e74522607be050b015771138d77
INSERT INTO users (username, email, password_hash, role, created_by, is_active)
VALUES (
    'Admin',
    'prathmeshgumal@gmail.com',
    '882b93331769ed8e162cfe6751b376b552b42e74522607be050b015771138d77',
    'admin',
    'system',
    TRUE
) ON CONFLICT (username) DO NOTHING;

-- Verify the admin user was created
SELECT * FROM users WHERE username = 'Admin';
