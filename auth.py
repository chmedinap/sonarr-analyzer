"""
Authentication module for user management with role-based access control.
Supports admin and read-only user roles with secure password hashing.
"""

import sqlite3
import hashlib
import secrets
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from datetime import datetime
import bcrypt


class UserManager:
    """Manages user authentication and authorization with SQLite database."""
    
    def __init__(self, db_path: str = "data/users.db"):
        """
        Initialize user manager.
        
        Args:
            db_path: Path to SQLite database file for user data
        """
        self.db_path = Path(db_path)
        # Ensure parent directory exists with proper permissions
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise PermissionError(
                f"Cannot create directory {self.db_path.parent}. "
                f"Please ensure the data directory is writable by UID 1000 (appuser). "
                f"For bind mounts, run: sudo chown -R 1000:1000 /path/to/data"
            ) from e
        self._init_database()
    
    def _init_database(self):
        """Create user database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'readonly')),
                created_at TEXT NOT NULL,
                last_login TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # User sessions table (for tracking active sessions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_username 
            ON users(username)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_token 
            ON sessions(session_token)
        """)
        
        conn.commit()
        conn.close()
    
    def _hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            password: Plain text password to verify
            password_hash: Stored password hash
            
        Returns:
            True if password matches
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False
    
    def has_users(self) -> bool:
        """
        Check if any users exist in the database.
        
        Returns:
            True if at least one user exists
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            
            conn.close()
            return count > 0
        except Exception:
            return False
    
    def has_admin(self) -> bool:
        """
        Check if at least one admin user exists.
        
        Returns:
            True if an admin exists
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            count = cursor.fetchone()[0]
            
            conn.close()
            return count > 0
        except Exception:
            return False
    
    def create_user(
        self,
        username: str,
        password: str,
        role: str = 'readonly'
    ) -> Tuple[bool, str]:
        """
        Create a new user.
        
        Args:
            username: Username (must be unique)
            password: Plain text password (will be hashed)
            role: User role ('admin' or 'readonly')
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate inputs
            if not username or not password:
                return False, "Username and password cannot be empty"
            
            if len(username) < 3:
                return False, "Username must be at least 3 characters"
            
            if len(password) < 8:
                return False, "Password must be at least 8 characters"
            
            if role not in ['admin', 'readonly']:
                return False, "Role must be 'admin' or 'readonly'"
            
            # Check if username exists
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                conn.close()
                return False, "Username already exists"
            
            # Hash password
            password_hash = self._hash_password(password)
            
            # Insert user
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, created_at)
                VALUES (?, ?, ?, ?)
            """, (username, password_hash, role, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            return True, f"User '{username}' created successfully with {role} role"
            
        except Exception as e:
            return False, f"Error creating user: {str(e)}"
    
    def authenticate(
        self,
        username: str,
        password: str
    ) -> Tuple[bool, Optional[Dict], str]:
        """
        Authenticate user with username and password.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            Tuple of (success, user_dict, message)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, username, password_hash, role, is_active
                FROM users
                WHERE username = ?
            """, (username,))
            
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return False, None, "Invalid username or password"
            
            user_id, username, password_hash, role, is_active = row
            
            if not is_active:
                conn.close()
                return False, None, "User account is disabled"
            
            # Verify password
            if not self._verify_password(password, password_hash):
                conn.close()
                return False, None, "Invalid username or password"
            
            # Update last login
            cursor.execute("""
                UPDATE users 
                SET last_login = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), user_id))
            
            conn.commit()
            conn.close()
            
            user_dict = {
                'id': user_id,
                'username': username,
                'role': role
            }
            
            return True, user_dict, "Authentication successful"
            
        except Exception as e:
            return False, None, f"Authentication error: {str(e)}"
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """
        Get user information by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User dictionary or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, username, role, created_at, last_login, is_active
                FROM users
                WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'username': row[1],
                'role': row[2],
                'created_at': row[3],
                'last_login': row[4],
                'is_active': row[5] == 1
            }
            
        except Exception:
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        Get user information by username.
        
        Args:
            username: Username
            
        Returns:
            User dictionary or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, username, role, created_at, last_login, is_active
                FROM users
                WHERE username = ?
            """, (username,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'username': row[1],
                'role': row[2],
                'created_at': row[3],
                'last_login': row[4],
                'is_active': row[5] == 1
            }
            
        except Exception:
            return None
    
    def list_users(self) -> List[Dict]:
        """
        Get list of all users.
        
        Returns:
            List of user dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, username, role, created_at, last_login, is_active
                FROM users
                ORDER BY created_at DESC
            """)
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    'id': row[0],
                    'username': row[1],
                    'role': row[2],
                    'created_at': row[3],
                    'last_login': row[4],
                    'is_active': row[5] == 1
                })
            
            conn.close()
            return users
            
        except Exception:
            return []
    
    def update_password(
        self,
        user_id: int,
        new_password: str
    ) -> Tuple[bool, str]:
        """
        Update user password.
        
        Args:
            user_id: User ID
            new_password: New plain text password
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if len(new_password) < 8:
                return False, "Password must be at least 8 characters"
            
            password_hash = self._hash_password(new_password)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users 
                SET password_hash = ?
                WHERE id = ?
            """, (password_hash, user_id))
            
            if cursor.rowcount == 0:
                conn.close()
                return False, "User not found"
            
            conn.commit()
            conn.close()
            
            return True, "Password updated successfully"
            
        except Exception as e:
            return False, f"Error updating password: {str(e)}"
    
    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """
        Delete a user.
        
        Args:
            user_id: User ID to delete
            
        Returns:
            Tuple of (success, message)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if this is the last admin
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE role = 'admin' AND id != ?
            """, (user_id,))
            
            admin_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            
            if user and user[0] == 'admin' and admin_count == 0:
                conn.close()
                return False, "Cannot delete the last admin user"
            
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            
            if cursor.rowcount == 0:
                conn.close()
                return False, "User not found"
            
            conn.commit()
            conn.close()
            
            return True, "User deleted successfully"
            
        except Exception as e:
            return False, f"Error deleting user: {str(e)}"
    
    def is_admin(self, user_id: int) -> bool:
        """
        Check if user has admin role.
        
        Args:
            user_id: User ID
            
        Returns:
            True if user is admin
        """
        user = self.get_user(user_id)
        return user is not None and user['role'] == 'admin'


def test_user_manager():
    """Test user manager functionality."""
    print("Testing UserManager...")
    
    # Use test database
    manager = UserManager("test_users.db")
    
    # Create admin user
    success, msg = manager.create_user("admin", "admin123", "admin")
    print(f"Create admin: {success} - {msg}")
    
    # Create read-only user
    success, msg = manager.create_user("viewer", "viewer123", "readonly")
    print(f"Create viewer: {success} - {msg}")
    
    # Test authentication
    success, user, msg = manager.authenticate("admin", "admin123")
    print(f"Auth (correct): {success} - {msg}")
    if user:
        print(f"  User: {user}")
    
    success, user, msg = manager.authenticate("admin", "wrongpass")
    print(f"Auth (wrong): {success} - {msg}")
    
    # List users
    users = manager.list_users()
    print(f"\nAll users: {len(users)}")
    for u in users:
        print(f"  - {u['username']} ({u['role']})")
    
    print("\nTest complete!")


if __name__ == "__main__":
    test_user_manager()

