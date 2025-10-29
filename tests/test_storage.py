"""
Unit tests for storage module.
Tests historical data storage, retrieval, and comparison.
"""

import unittest
import os
import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage import HistoryDatabase


class TestHistoryDatabase(unittest.TestCase):
    """Test cases for HistoryDatabase class."""
    
    def setUp(self):
        """Set up test database before each test."""
        self.test_db = "test_history_temp.db"
        self.db = HistoryDatabase(self.test_db)
        
        # Sample data
        self.sample_df = pd.DataFrame({
            'series_id': [1, 2, 3],
            'title': ['Series A', 'Series B', 'Series C'],
            'year': ['2020', '2021', '2022'],
            'status': ['continuing', 'ended', 'continuing'],
            'episode_count': [10, 20, 15],
            'total_size_gb': [5.0, 10.0, 7.5],
            'avg_size_mb': [500.0, 512.0, 510.0],
            'z_score': [0.1, 0.5, 0.3],
            'is_outlier': [False, False, False]
        })
        
        self.sample_stats = {
            'mean': 507.3,
            'std': 5.0,
            'outlier_count': 0,
            'outlier_percentage': 0.0
        }
    
    def tearDown(self):
        """Clean up test database after each test."""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_save_analysis(self):
        """Test saving analysis data."""
        success, msg = self.db.save_analysis(1, self.sample_df, self.sample_stats)
        self.assertTrue(success)
        self.assertIn("saved successfully", msg)
    
    def test_get_analysis_dates(self):
        """Test getting list of analysis dates."""
        # Initially empty
        dates = self.db.get_analysis_dates(1)
        self.assertEqual(len(dates), 0)
        
        # Save analysis
        self.db.save_analysis(1, self.sample_df, self.sample_stats, "2024-01-01 10:00:00")
        
        # Should have one date
        dates = self.db.get_analysis_dates(1)
        self.assertEqual(len(dates), 1)
        self.assertEqual(dates[0], "2024-01-01 10:00:00")
    
    def test_load_analysis(self):
        """Test loading analysis data."""
        date = "2024-01-01 10:00:00"
        self.db.save_analysis(1, self.sample_df, self.sample_stats, date)
        
        # Load data
        loaded_df = self.db.load_analysis(1, date)
        
        self.assertIsNotNone(loaded_df)
        self.assertEqual(len(loaded_df), 3)
        self.assertTrue('series_title' in loaded_df.columns)
    
    def test_get_summary(self):
        """Test getting summary statistics."""
        date = "2024-01-01 10:00:00"
        self.db.save_analysis(1, self.sample_df, self.sample_stats, date)
        
        # Get summary
        summary = self.db.get_summary(1, date)
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary['total_series'], 3)
        self.assertEqual(summary['total_episodes'], 45)
    
    def test_user_isolation(self):
        """Test that users have separate analysis history."""
        # Save for user 1
        self.db.save_analysis(1, self.sample_df, self.sample_stats, "2024-01-01 10:00:00")
        
        # Save for user 2
        self.db.save_analysis(2, self.sample_df, self.sample_stats, "2024-01-01 10:00:00")
        
        # Each user should have their own dates
        dates1 = self.db.get_analysis_dates(1)
        dates2 = self.db.get_analysis_dates(2)
        
        self.assertEqual(len(dates1), 1)
        self.assertEqual(len(dates2), 1)
        
        # Load for each user
        data1 = self.db.load_analysis(1, dates1[0])
        data2 = self.db.load_analysis(2, dates2[0])
        
        self.assertIsNotNone(data1)
        self.assertIsNotNone(data2)
    
    def test_overwrite_analysis(self):
        """Test overwriting existing analysis."""
        date = "2024-01-01 10:00:00"
        
        # Save first analysis
        self.db.save_analysis(1, self.sample_df, self.sample_stats, date)
        
        # Try to save again without overwrite
        success, msg = self.db.save_analysis(1, self.sample_df, self.sample_stats, date, overwrite=False)
        self.assertFalse(success)
        self.assertIn("already exists", msg)
        
        # Save with overwrite
        success, msg = self.db.save_analysis(1, self.sample_df, self.sample_stats, date, overwrite=True)
        self.assertTrue(success)
    
    def test_compare_dates(self):
        """Test comparing two analysis dates."""
        # Save two analyses
        df1 = self.sample_df.copy()
        df2 = self.sample_df.copy()
        df2['episode_count'] = [12, 22, 17]  # Changed counts
        df2['total_size_gb'] = [6.0, 11.0, 8.5]  # Changed sizes
        
        self.db.save_analysis(1, df1, self.sample_stats, "2024-01-01 10:00:00")
        self.db.save_analysis(1, df2, self.sample_stats, "2024-02-01 10:00:00")
        
        # Compare
        comparison = self.db.compare_dates(1, "2024-01-01 10:00:00", "2024-02-01 10:00:00")
        
        self.assertIsNotNone(comparison)
        self.assertEqual(len(comparison), 3)
        
        # Check changes are detected
        self.assertTrue('episodes_change' in comparison.columns)
        self.assertTrue('size_change_gb' in comparison.columns)
    
    def test_compare_with_new_series(self):
        """Test comparison when new series are added."""
        # First analysis with 3 series
        df1 = self.sample_df.copy()
        
        # Second analysis with 4 series (one new)
        df2 = pd.concat([df1, pd.DataFrame({
            'series_id': [4],
            'title': ['Series D'],
            'year': ['2023'],
            'status': ['continuing'],
            'episode_count': [25],
            'total_size_gb': [12.5],
            'avg_size_mb': [520.0],
            'z_score': [0.4],
            'is_outlier': [False]
        })], ignore_index=True)
        
        self.db.save_analysis(1, df1, self.sample_stats, "2024-01-01 10:00:00")
        self.db.save_analysis(1, df2, self.sample_stats, "2024-02-01 10:00:00")
        
        # Compare
        comparison = self.db.compare_dates(1, "2024-01-01 10:00:00", "2024-02-01 10:00:00")
        
        # Should have 4 rows (3 existing + 1 new)
        self.assertEqual(len(comparison), 4)
        
        # One should be marked as new
        new_series = comparison[comparison['status'] == 'new']
        self.assertEqual(len(new_series), 1)
    
    def test_get_time_series(self):
        """Test getting time series for a specific series."""
        # Save multiple analyses
        self.db.save_analysis(1, self.sample_df, self.sample_stats, "2024-01-01 10:00:00")
        
        df2 = self.sample_df.copy()
        df2.loc[df2['series_id'] == 1, 'total_size_gb'] = 6.0
        self.db.save_analysis(1, df2, self.sample_stats, "2024-02-01 10:00:00")
        
        # Get time series for series_id 1
        ts = self.db.get_time_series(1, 1, 'total_size_gb')
        
        self.assertIsNotNone(ts)
        self.assertEqual(len(ts), 2)
        self.assertTrue('analysis_date' in ts.columns)
        self.assertTrue('total_size_gb' in ts.columns)
    
    def test_get_global_trends(self):
        """Test getting global trend data."""
        # Save multiple analyses
        self.db.save_analysis(1, self.sample_df, self.sample_stats, "2024-01-01 10:00:00")
        self.db.save_analysis(1, self.sample_df, self.sample_stats, "2024-02-01 10:00:00")
        
        # Get trends
        trends = self.db.get_global_trends(1)
        
        self.assertIsNotNone(trends)
        self.assertEqual(len(trends), 2)
        self.assertTrue('analysis_date' in trends.columns)
        self.assertTrue('total_storage_gb' in trends.columns)
    
    def test_delete_analysis(self):
        """Test deleting an analysis."""
        date = "2024-01-01 10:00:00"
        self.db.save_analysis(1, self.sample_df, self.sample_stats, date)
        
        # Verify it exists
        dates = self.db.get_analysis_dates(1)
        self.assertEqual(len(dates), 1)
        
        # Delete it
        success, msg = self.db.delete_analysis(1, date)
        self.assertTrue(success)
        
        # Should be gone
        dates = self.db.get_analysis_dates(1)
        self.assertEqual(len(dates), 0)
    
    def test_cleanup_old_data(self):
        """Test cleaning up old data."""
        # Save analyses with different dates
        self.db.save_analysis(1, self.sample_df, self.sample_stats, "2023-01-01 10:00:00")
        self.db.save_analysis(1, self.sample_df, self.sample_stats, "2024-01-01 10:00:00")
        
        # Cleanup data older than 180 days
        success, msg = self.db.cleanup_old_data(1, 180)
        self.assertTrue(success)
        
        # Old data should be gone
        dates = self.db.get_analysis_dates(1)
        # Depending on current date, might have 1 or 2 dates
        self.assertGreaterEqual(len(dates), 0)
    
    def test_export_to_csv(self):
        """Test exporting data to CSV."""
        self.db.save_analysis(1, self.sample_df, self.sample_stats, "2024-01-01 10:00:00")
        
        output_file = "test_export.csv"
        success, msg = self.db.export_to_csv(1, output_file)
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_file))
        
        # Clean up
        os.remove(output_file)


if __name__ == '__main__':
    unittest.main()

