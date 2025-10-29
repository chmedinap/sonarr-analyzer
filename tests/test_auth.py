"""
Unit tests for authentication module.
Tests user creation, login, password hashing, and role management.
"""

import unittest
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth import UserManager


class TestUserManager(unittest.TestCase):
    """Test cases for UserManager class."""
    
    def setUp(self):
        """Set up test database before each test."""
        self.test_db = "test_users_temp.db"
        self.manager = UserManager(self.test_db)
    
    def tearDown(self):
        """Clean up test database after each test."""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_create_admin_user(self):
        """Test creating an admin user."""
        success, msg = self.manager.create_user("admin", "admin12345", "admin")
        self.assertTrue(success)
        self.assertIn("created successfully", msg)
        
        # Verify user was created
        user = self.manager.get_user_by_username("admin")
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], "admin")
        self.assertEqual(user['role'], "admin")
    
    def test_create_readonly_user(self):
        """Test creating a read-only user."""
        success, msg = self.manager.create_user("viewer", "viewer123", "readonly")
        self.assertTrue(success)
        
        user = self.manager.get_user_by_username("viewer")
        self.assertIsNotNone(user)
        self.assertEqual(user['role'], "readonly")
    
    def test_password_too_short(self):
        """Test that short passwords are rejected."""
        success, msg = self.manager.create_user("test", "short", "admin")
        self.assertFalse(success)
        self.assertIn("at least 8 characters", msg)
    
    def test_username_too_short(self):
        """Test that short usernames are rejected."""
        success, msg = self.manager.create_user("ab", "password123", "admin")
        self.assertFalse(success)
        self.assertIn("at least 3 characters", msg)
    
    def test_duplicate_username(self):
        """Test that duplicate usernames are rejected."""
        self.manager.create_user("user1", "password123", "admin")
        success, msg = self.manager.create_user("user1", "password456", "admin")
        self.assertFalse(success)
        self.assertIn("already exists", msg)
    
    def test_invalid_role(self):
        """Test that invalid roles are rejected."""
        success, msg = self.manager.create_user("test", "password123", "invalid")
        self.assertFalse(success)
        self.assertIn("must be", msg)
    
    def test_authenticate_correct_password(self):
        """Test authentication with correct password."""
        self.manager.create_user("testuser", "testpass123", "admin")
        
        success, user, msg = self.manager.authenticate("testuser", "testpass123")
        self.assertTrue(success)
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], "testuser")
        self.assertEqual(user['role'], "admin")
    
    def test_authenticate_wrong_password(self):
        """Test authentication with wrong password."""
        self.manager.create_user("testuser", "testpass123", "admin")
        
        success, user, msg = self.manager.authenticate("testuser", "wrongpass")
        self.assertFalse(success)
        self.assertIsNone(user)
        self.assertIn("Invalid", msg)
    
    def test_authenticate_nonexistent_user(self):
        """Test authentication with nonexistent user."""
        success, user, msg = self.manager.authenticate("nouser", "password123")
        self.assertFalse(success)
        self.assertIsNone(user)
    
    def test_password_hashing(self):
        """Test that passwords are properly hashed."""
        import sqlite3
        
        self.manager.create_user("hashtest", "mypassword", "admin")
        
        # Check database directly
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", ("hashtest",))
        stored_hash = cursor.fetchone()[0]
        conn.close()
        
        # Hash should not be the plain password
        self.assertNotEqual(stored_hash, "mypassword")
        # Should be bcrypt hash (starts with $2b$)
        self.assertTrue(stored_hash.startswith("$2b$"))
    
    def test_has_users(self):
        """Test has_users method."""
        self.assertFalse(self.manager.has_users())
        
        self.manager.create_user("user1", "password123", "admin")
        self.assertTrue(self.manager.has_users())
    
    def test_has_admin(self):
        """Test has_admin method."""
        self.assertFalse(self.manager.has_admin())
        
        self.manager.create_user("readonly_user", "password123", "readonly")
        self.assertFalse(self.manager.has_admin())
        
        self.manager.create_user("admin_user", "password123", "admin")
        self.assertTrue(self.manager.has_admin())
    
    def test_list_users(self):
        """Test listing all users."""
        self.manager.create_user("user1", "password123", "admin")
        self.manager.create_user("user2", "password456", "readonly")
        
        users = self.manager.list_users()
        self.assertEqual(len(users), 2)
        
        usernames = [u['username'] for u in users]
        self.assertIn("user1", usernames)
        self.assertIn("user2", usernames)
    
    def test_get_user_by_id(self):
        """Test getting user by ID."""
        self.manager.create_user("testuser", "password123", "admin")
        
        user = self.manager.get_user_by_username("testuser")
        user_id = user['id']
        
        user2 = self.manager.get_user(user_id)
        self.assertIsNotNone(user2)
        self.assertEqual(user2['username'], "testuser")
    
    def test_is_admin(self):
        """Test is_admin method."""
        self.manager.create_user("admin", "password123", "admin")
        self.manager.create_user("viewer", "password123", "readonly")
        
        admin_user = self.manager.get_user_by_username("admin")
        viewer_user = self.manager.get_user_by_username("viewer")
        
        self.assertTrue(self.manager.is_admin(admin_user['id']))
        self.assertFalse(self.manager.is_admin(viewer_user['id']))
    
    def test_update_password(self):
        """Test updating user password."""
        self.manager.create_user("testuser", "oldpass123", "admin")
        
        user = self.manager.get_user_by_username("testuser")
        
        # Update password
        success, msg = self.manager.update_password(user['id'], "newpass456")
        self.assertTrue(success)
        
        # Old password should not work
        success, _, _ = self.manager.authenticate("testuser", "oldpass123")
        self.assertFalse(success)
        
        # New password should work
        success, _, _ = self.manager.authenticate("testuser", "newpass456")
        self.assertTrue(success)
    
    def test_delete_user(self):
        """Test deleting a user."""
        self.manager.create_user("admin", "password123", "admin")
        self.manager.create_user("todelete", "password123", "readonly")
        
        user = self.manager.get_user_by_username("todelete")
        
        success, msg = self.manager.delete_user(user['id'])
        self.assertTrue(success)
        
        # User should no longer exist
        deleted_user = self.manager.get_user_by_username("todelete")
        self.assertIsNone(deleted_user)
    
    def test_cannot_delete_last_admin(self):
        """Test that last admin cannot be deleted."""
        self.manager.create_user("admin", "password123", "admin")
        
        admin = self.manager.get_user_by_username("admin")
        
        success, msg = self.manager.delete_user(admin['id'])
        self.assertFalse(success)
        self.assertIn("last admin", msg)
    
    def test_can_delete_admin_if_others_exist(self):
        """Test that admin can be deleted if other admins exist."""
        self.manager.create_user("admin1", "password123", "admin")
        self.manager.create_user("admin2", "password123", "admin")
        
        admin1 = self.manager.get_user_by_username("admin1")
        
        success, msg = self.manager.delete_user(admin1['id'])
        self.assertTrue(success)


if __name__ == '__main__':
    unittest.main()

