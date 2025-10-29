"""
Integration tests for role enforcement and system interactions.
Tests the complete flow from user creation to analysis execution.
"""

import unittest
import os
import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth import UserManager
from security import TokenManager
from storage import HistoryDatabase


class TestRoleEnforcement(unittest.TestCase):
    """Test role-based access control."""
    
    def setUp(self):
        """Set up test managers before each test."""
        self.test_user_db = "test_users_int.db"
        self.test_token_db = "test_tokens_int.db"
        self.test_key = "test_master_int.key"
        self.test_history_db = "test_history_int.db"
        
        self.user_mgr = UserManager(self.test_user_db)
        self.token_mgr = TokenManager(self.test_token_db, self.test_key)
        self.history_db = HistoryDatabase(self.test_history_db)
    
    def tearDown(self):
        """Clean up test files after each test."""
        for f in [self.test_user_db, self.test_token_db, self.test_key, self.test_history_db]:
            if os.path.exists(f):
                os.remove(f)
    
    def test_admin_can_create_users(self):
        """Test that admin role is tracked correctly."""
        # Create admin
        self.user_mgr.create_user("admin", "admin123", "admin")
        admin = self.user_mgr.get_user_by_username("admin")
        
        # Verify admin role
        self.assertEqual(admin['role'], "admin")
        self.assertTrue(self.user_mgr.is_admin(admin['id']))
    
    def test_readonly_user_role(self):
        """Test that readonly role is tracked correctly."""
        # Create readonly user
        self.user_mgr.create_user("viewer", "viewer123", "readonly")
        viewer = self.user_mgr.get_user_by_username("viewer")
        
        # Verify readonly role
        self.assertEqual(viewer['role'], "readonly")
        self.assertFalse(self.user_mgr.is_admin(viewer['id']))
    
    def test_user_token_workflow(self):
        """Test complete workflow: create user → save token → load token."""
        # Create user
        self.user_mgr.create_user("testuser", "password123", "admin")
        user = self.user_mgr.get_user_by_username("testuser")
        
        # Save token
        success, msg = self.token_mgr.save_token(
            user['id'],
            "http://localhost:8989",
            "api_key_12345"
        )
        self.assertTrue(success)
        
        # Load token
        success, data, msg = self.token_mgr.load_token(user['id'])
        self.assertTrue(success)
        self.assertEqual(data['sonarr_url'], "http://localhost:8989")
        self.assertEqual(data['api_token'], "api_key_12345")
    
    def test_user_analysis_workflow(self):
        """Test complete workflow: create user → save analysis → load analysis."""
        # Create user
        self.user_mgr.create_user("analyst", "password123", "admin")
        user = self.user_mgr.get_user_by_username("analyst")
        
        # Create sample analysis data
        df = pd.DataFrame({
            'series_id': [1, 2],
            'title': ['Series A', 'Series B'],
            'year': ['2020', '2021'],
            'status': ['continuing', 'ended'],
            'episode_count': [10, 20],
            'total_size_gb': [5.0, 10.0],
            'avg_size_mb': [500.0, 512.0],
            'z_score': [0.1, 0.5],
            'is_outlier': [False, False]
        })
        
        stats = {
            'mean': 506.0,
            'std': 6.0,
            'outlier_count': 0,
            'outlier_percentage': 0.0
        }
        
        # Save analysis
        success, msg = self.history_db.save_analysis(user['id'], df, stats)
        self.assertTrue(success)
        
        # Load analysis
        dates = self.history_db.get_analysis_dates(user['id'])
        self.assertEqual(len(dates), 1)
        
        loaded_df = self.history_db.load_analysis(user['id'], dates[0])
        self.assertIsNotNone(loaded_df)
        self.assertEqual(len(loaded_df), 2)
    
    def test_user_data_isolation(self):
        """Test that users cannot access each other's data."""
        # Create two users
        self.user_mgr.create_user("user1", "password123", "admin")
        self.user_mgr.create_user("user2", "password123", "admin")
        
        user1 = self.user_mgr.get_user_by_username("user1")
        user2 = self.user_mgr.get_user_by_username("user2")
        
        # Save tokens for each user
        self.token_mgr.save_token(user1['id'], "http://user1:8989", "key1")
        self.token_mgr.save_token(user2['id'], "http://user2:8989", "key2")
        
        # Each user should only see their own token
        _, data1, _ = self.token_mgr.load_token(user1['id'])
        _, data2, _ = self.token_mgr.load_token(user2['id'])
        
        self.assertEqual(data1['sonarr_url'], "http://user1:8989")
        self.assertEqual(data2['sonarr_url'], "http://user2:8989")
        
        # User 1 cannot see user 2's token
        self.assertNotEqual(data1['api_token'], data2['api_token'])
    
    def test_analysis_data_isolation(self):
        """Test that users have separate analysis histories."""
        # Create two users
        self.user_mgr.create_user("user1", "password123", "admin")
        self.user_mgr.create_user("user2", "password123", "admin")
        
        user1 = self.user_mgr.get_user_by_username("user1")
        user2 = self.user_mgr.get_user_by_username("user2")
        
        # Create sample data
        df = pd.DataFrame({
            'series_id': [1],
            'title': ['Series A'],
            'year': ['2020'],
            'status': ['continuing'],
            'episode_count': [10],
            'total_size_gb': [5.0],
            'avg_size_mb': [500.0],
            'z_score': [0.1],
            'is_outlier': [False]
        })
        
        stats = {'mean': 500.0, 'std': 0.0, 'outlier_count': 0, 'outlier_percentage': 0.0}
        
        # Save analysis for both users
        self.history_db.save_analysis(user1['id'], df, stats, "2024-01-01 10:00:00")
        self.history_db.save_analysis(user2['id'], df, stats, "2024-01-01 10:00:00")
        
        # Each user should see only their own analysis
        dates1 = self.history_db.get_analysis_dates(user1['id'])
        dates2 = self.history_db.get_analysis_dates(user2['id'])
        
        self.assertEqual(len(dates1), 1)
        self.assertEqual(len(dates2), 1)
        
        # But they should be separate records
        data1 = self.history_db.load_analysis(user1['id'], dates1[0])
        data2 = self.history_db.load_analysis(user2['id'], dates2[0])
        
        # Both should have data, but they're isolated
        self.assertIsNotNone(data1)
        self.assertIsNotNone(data2)
    
    def test_password_change_security(self):
        """Test that password changes invalidate old credentials."""
        # Create user
        self.user_mgr.create_user("changetest", "oldpass123", "admin")
        
        # Verify old password works
        success, user, _ = self.user_mgr.authenticate("changetest", "oldpass123")
        self.assertTrue(success)
        
        # Change password
        self.user_mgr.update_password(user['id'], "newpass456")
        
        # Old password should no longer work
        success, _, _ = self.user_mgr.authenticate("changetest", "oldpass123")
        self.assertFalse(success)
        
        # New password should work
        success, _, _ = self.user_mgr.authenticate("changetest", "newpass456")
        self.assertTrue(success)
    
    def test_user_deletion_cleanup(self):
        """Test that deleting user preserves data integrity."""
        # Create two admins
        self.user_mgr.create_user("admin1", "password123", "admin")
        self.user_mgr.create_user("admin2", "password123", "admin")
        
        admin1 = self.user_mgr.get_user_by_username("admin1")
        admin2 = self.user_mgr.get_user_by_username("admin2")
        
        # Save tokens for both
        self.token_mgr.save_token(admin1['id'], "http://admin1:8989", "key1")
        self.token_mgr.save_token(admin2['id'], "http://admin2:8989", "key2")
        
        # Delete admin1
        success, _ = self.user_mgr.delete_user(admin1['id'])
        self.assertTrue(success)
        
        # admin1 should be gone
        deleted_user = self.user_mgr.get_user(admin1['id'])
        self.assertIsNone(deleted_user)
        
        # admin2 should still exist
        existing_user = self.user_mgr.get_user(admin2['id'])
        self.assertIsNotNone(existing_user)
        
        # admin2's token should still work
        success, data, _ = self.token_mgr.load_token(admin2['id'])
        self.assertTrue(success)


class TestSecurityValidation(unittest.TestCase):
    """Test security-related validation."""
    
    def setUp(self):
        """Set up test managers."""
        self.test_user_db = "test_sec_val.db"
        self.user_mgr = UserManager(self.test_user_db)
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_user_db):
            os.remove(self.test_user_db)
    
    def test_password_complexity(self):
        """Test password length requirements."""
        # Too short
        success, _ = self.user_mgr.create_user("test", "short", "admin")
        self.assertFalse(success)
        
        # Minimum length
        success, _ = self.user_mgr.create_user("test", "12345678", "admin")
        self.assertTrue(success)
    
    def test_username_requirements(self):
        """Test username requirements."""
        # Too short
        success, _ = self.user_mgr.create_user("ab", "password123", "admin")
        self.assertFalse(success)
        
        # Minimum length
        success, _ = self.user_mgr.create_user("abc", "password123", "admin")
        self.assertTrue(success)
    
    def test_unique_username_constraint(self):
        """Test that usernames must be unique."""
        self.user_mgr.create_user("duplicate", "password123", "admin")
        
        # Second user with same name should fail
        success, _ = self.user_mgr.create_user("duplicate", "different456", "admin")
        self.assertFalse(success)


if __name__ == '__main__':
    unittest.main()

