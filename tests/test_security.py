"""
Unit tests for security module.
Tests token encryption, decryption, and key management.
"""

import unittest
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from security import TokenManager


class TestTokenManager(unittest.TestCase):
    """Test cases for TokenManager class."""
    
    def setUp(self):
        """Set up test files before each test."""
        self.test_db = "test_tokens_temp.db"
        self.test_key = "test_master_temp.key"
        self.manager = TokenManager(self.test_db, self.test_key)
    
    def tearDown(self):
        """Clean up test files after each test."""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if os.path.exists(self.test_key):
            os.remove(self.test_key)
    
    def test_master_key_creation(self):
        """Test that master key is created on initialization."""
        self.assertTrue(os.path.exists(self.test_key))
        
        with open(self.test_key, 'rb') as f:
            key = f.read()
        
        # Key should be 44 bytes (Fernet key)
        self.assertEqual(len(key), 44)
    
    def test_master_key_persistence(self):
        """Test that master key persists across instances."""
        # Get key from first instance
        with open(self.test_key, 'rb') as f:
            key1 = f.read()
        
        # Create new instance
        manager2 = TokenManager(self.test_db, self.test_key)
        
        # Key should be the same
        with open(self.test_key, 'rb') as f:
            key2 = f.read()
        
        self.assertEqual(key1, key2)
    
    def test_save_token(self):
        """Test saving a token."""
        success, msg = self.manager.save_token(
            1,
            "http://localhost:8989",
            "test_api_key_12345"
        )
        
        self.assertTrue(success)
        self.assertIn("saved successfully", msg)
    
    def test_load_token(self):
        """Test loading a saved token."""
        # Save token
        self.manager.save_token(
            1,
            "http://localhost:8989",
            "test_api_key_12345"
        )
        
        # Load token
        success, data, msg = self.manager.load_token(1)
        
        self.assertTrue(success)
        self.assertIsNotNone(data)
        self.assertEqual(data['sonarr_url'], "http://localhost:8989")
        self.assertEqual(data['api_token'], "test_api_key_12345")
    
    def test_has_token(self):
        """Test checking if user has token."""
        # Initially no token
        self.assertFalse(self.manager.has_token(1))
        
        # Save token
        self.manager.save_token(1, "http://localhost:8989", "api_key")
        
        # Now has token
        self.assertTrue(self.manager.has_token(1))
    
    def test_delete_token(self):
        """Test deleting a token."""
        # Save token
        self.manager.save_token(1, "http://localhost:8989", "api_key")
        self.assertTrue(self.manager.has_token(1))
        
        # Delete token
        success, msg = self.manager.delete_token(1)
        self.assertTrue(success)
        
        # Token should be gone
        self.assertFalse(self.manager.has_token(1))
    
    def test_update_token(self):
        """Test updating an existing token."""
        # Save initial token
        self.manager.save_token(1, "http://localhost:8989", "old_key")
        
        # Update token
        self.manager.save_token(1, "http://newhost:8989", "new_key")
        
        # Load token
        success, data, msg = self.manager.load_token(1)
        
        self.assertEqual(data['sonarr_url'], "http://newhost:8989")
        self.assertEqual(data['api_token'], "new_key")
    
    def test_multiple_users(self):
        """Test that different users have separate tokens."""
        # Save tokens for two users
        self.manager.save_token(1, "http://user1:8989", "key1")
        self.manager.save_token(2, "http://user2:8989", "key2")
        
        # Load tokens
        _, data1, _ = self.manager.load_token(1)
        _, data2, _ = self.manager.load_token(2)
        
        # Each user should have their own token
        self.assertEqual(data1['sonarr_url'], "http://user1:8989")
        self.assertEqual(data2['sonarr_url'], "http://user2:8989")
    
    def test_encrypted_storage(self):
        """Test that tokens are stored encrypted."""
        import sqlite3
        
        # Save token
        self.manager.save_token(1, "http://localhost:8989", "secret_key")
        
        # Check database directly
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT encrypted_token FROM user_tokens WHERE user_id = ?", (1,))
        encrypted = cursor.fetchone()[0]
        conn.close()
        
        # Encrypted data should not contain plain text
        self.assertNotIn("secret_key", encrypted)
        self.assertNotIn("localhost", encrypted)
    
    def test_empty_url(self):
        """Test that empty URL is rejected."""
        success, msg = self.manager.save_token(1, "", "api_key")
        self.assertFalse(success)
        self.assertIn("cannot be empty", msg)
    
    def test_empty_token(self):
        """Test that empty token is rejected."""
        success, msg = self.manager.save_token(1, "http://localhost:8989", "")
        self.assertFalse(success)
        self.assertIn("cannot be empty", msg)
    
    def test_load_nonexistent_token(self):
        """Test loading token for user who has none."""
        success, data, msg = self.manager.load_token(999)
        self.assertFalse(success)
        self.assertIsNone(data)
        self.assertIn("token found", msg.lower())
    
    def test_delete_nonexistent_token(self):
        """Test deleting token that doesn't exist."""
        success, msg = self.manager.delete_token(999)
        self.assertTrue(success)  # Should succeed but report nothing deleted
    
    def test_encryption_consistency(self):
        """Test that same data encrypts differently each time (due to salt/IV)."""
        import sqlite3
        
        # Save same token twice for different users
        self.manager.save_token(1, "http://same:8989", "same_key")
        self.manager.save_token(2, "http://same:8989", "same_key")
        
        # Get encrypted values
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT encrypted_token FROM user_tokens WHERE user_id = ?", (1,))
        encrypted1 = cursor.fetchone()[0]
        cursor.execute("SELECT encrypted_token FROM user_tokens WHERE user_id = ?", (2,))
        encrypted2 = cursor.fetchone()[0]
        conn.close()
        
        # Even though data is same, encrypted values should differ (Fernet includes timestamp/IV)
        self.assertNotEqual(encrypted1, encrypted2)
        
        # But both should decrypt to same value
        _, data1, _ = self.manager.load_token(1)
        _, data2, _ = self.manager.load_token(2)
        self.assertEqual(data1, data2)


if __name__ == '__main__':
    unittest.main()

