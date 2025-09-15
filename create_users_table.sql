-- Create users table for authentication
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

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Insert the admin user
INSERT INTO users (username, email, password_hash, role, created_by, is_active)
VALUES (
    'Admin',
    'prathmeshgumal@gmail.com',
    'a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456', -- This will be the actual hash
    'admin',
    'system',
    TRUE
) ON CONFLICT (username) DO NOTHING;

-- Enable Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create policies for RLS
-- Users can only see their own data
CREATE POLICY "Users can view own data" ON users
    FOR SELECT USING (username = current_setting('app.current_user', true));

-- Only admins can insert new users
CREATE POLICY "Admins can insert users" ON users
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM users 
            WHERE username = current_setting('app.current_user', true) 
            AND role = 'admin'
        )
    );

-- Only admins can update users
CREATE POLICY "Admins can update users" ON users
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE username = current_setting('app.current_user', true) 
            AND role = 'admin'
        )
    );

-- Only admins can delete users (except themselves)
CREATE POLICY "Admins can delete users" ON users
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE username = current_setting('app.current_user', true) 
            AND role = 'admin'
        ) AND username != current_setting('app.current_user', true)
    );
