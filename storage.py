"""
Storage module for managing historical analysis data in SQLite.
Provides functions to save, load, and compare analysis results over time.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple, Dict
import json


class HistoryDatabase:
    """Manages SQLite database for historical analysis data."""
    
    def __init__(self, db_path: str = "sonarr_history.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self):
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main history table for series data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_date TEXT NOT NULL,
                series_id INTEGER NOT NULL,
                series_title TEXT NOT NULL,
                year TEXT,
                status TEXT,
                episode_count INTEGER,
                total_size_gb REAL,
                avg_size_mb REAL,
                z_score REAL,
                is_outlier INTEGER,
                UNIQUE(analysis_date, series_id)
            )
        """)
        
        # Summary table for overall statistics per analysis date
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_date TEXT UNIQUE NOT NULL,
                total_series INTEGER,
                total_episodes INTEGER,
                total_storage_gb REAL,
                mean_avg_size_mb REAL,
                std_avg_size_mb REAL,
                outlier_count INTEGER,
                outlier_percentage REAL
            )
        """)
        
        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_date 
            ON history(analysis_date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_series 
            ON history(series_id, analysis_date)
        """)
        
        conn.commit()
        conn.close()
    
    def save_analysis(
        self,
        df: pd.DataFrame,
        stats: Dict,
        analysis_date: Optional[str] = None,
        overwrite: bool = False
    ) -> Tuple[bool, str]:
        """
        Save analysis results to database.
        
        Args:
            df: DataFrame with series analysis results
            stats: Dictionary with global statistics
            analysis_date: Date string (ISO format), defaults to now
            overwrite: If True, replace existing data for this date
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if analysis_date is None:
                analysis_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check if data for this date already exists
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT COUNT(*) FROM history WHERE analysis_date = ?",
                (analysis_date,)
            )
            exists = cursor.fetchone()[0] > 0
            
            if exists and not overwrite:
                conn.close()
                return False, f"Data for {analysis_date} already exists. Set overwrite=True to replace."
            
            # Delete existing data if overwriting
            if exists and overwrite:
                cursor.execute(
                    "DELETE FROM history WHERE analysis_date = ?",
                    (analysis_date,)
                )
                cursor.execute(
                    "DELETE FROM analysis_summary WHERE analysis_date = ?",
                    (analysis_date,)
                )
            
            # Insert series data
            series_data = []
            for _, row in df.iterrows():
                series_data.append((
                    analysis_date,
                    int(row['series_id']),
                    row['title'],
                    str(row.get('year', 'N/A')),
                    row.get('status', 'Unknown'),
                    int(row['episode_count']),
                    float(row['total_size_gb']),
                    float(row['avg_size_mb']),
                    float(row['z_score']),
                    1 if row['is_outlier'] else 0
                ))
            
            cursor.executemany("""
                INSERT INTO history (
                    analysis_date, series_id, series_title, year, status,
                    episode_count, total_size_gb, avg_size_mb, z_score, is_outlier
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, series_data)
            
            # Insert summary data
            cursor.execute("""
                INSERT INTO analysis_summary (
                    analysis_date, total_series, total_episodes, total_storage_gb,
                    mean_avg_size_mb, std_avg_size_mb, outlier_count, outlier_percentage
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis_date,
                len(df),
                int(df['episode_count'].sum()),
                float(df['total_size_gb'].sum()),
                float(stats.get('mean', 0)),
                float(stats.get('std', 0)),
                int(stats.get('outlier_count', 0)),
                float(stats.get('outlier_percentage', 0))
            ))
            
            conn.commit()
            conn.close()
            
            return True, f"Analysis saved successfully ({len(df)} series)"
            
        except Exception as e:
            return False, f"Error saving analysis: {str(e)}"
    
    def get_analysis_dates(self) -> List[str]:
        """
        Get list of all available analysis dates.
        
        Returns:
            List of date strings
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT analysis_date 
                FROM history 
                ORDER BY analysis_date DESC
            """)
            
            dates = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return dates
            
        except Exception as e:
            print(f"Error getting dates: {e}")
            return []
    
    def load_analysis(self, analysis_date: str) -> Optional[pd.DataFrame]:
        """
        Load analysis data for a specific date.
        
        Args:
            analysis_date: Date string to load
            
        Returns:
            DataFrame with analysis data or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            df = pd.read_sql_query("""
                SELECT * FROM history 
                WHERE analysis_date = ?
                ORDER BY avg_size_mb DESC
            """, conn, params=(analysis_date,))
            
            conn.close()
            
            if len(df) == 0:
                return None
            
            # Convert is_outlier back to boolean
            df['is_outlier'] = df['is_outlier'].astype(bool)
            
            return df
            
        except Exception as e:
            print(f"Error loading analysis: {e}")
            return None
    
    def get_summary(self, analysis_date: str) -> Optional[Dict]:
        """
        Get summary statistics for a specific analysis date.
        
        Args:
            analysis_date: Date string
            
        Returns:
            Dictionary with summary statistics or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM analysis_summary 
                WHERE analysis_date = ?
            """, (analysis_date,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row is None:
                return None
            
            return {
                'analysis_date': row[1],
                'total_series': row[2],
                'total_episodes': row[3],
                'total_storage_gb': row[4],
                'mean_avg_size_mb': row[5],
                'std_avg_size_mb': row[6],
                'outlier_count': row[7],
                'outlier_percentage': row[8]
            }
            
        except Exception as e:
            print(f"Error getting summary: {e}")
            return None
    
    def compare_dates(
        self,
        date1: str,
        date2: str
    ) -> Optional[pd.DataFrame]:
        """
        Compare analysis results between two dates.
        
        Args:
            date1: First date (older)
            date2: Second date (newer)
            
        Returns:
            DataFrame with comparison results
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Load both datasets
            df1 = pd.read_sql_query("""
                SELECT series_id, series_title, episode_count, 
                       total_size_gb, avg_size_mb, is_outlier
                FROM history 
                WHERE analysis_date = ?
            """, conn, params=(date1,))
            
            df2 = pd.read_sql_query("""
                SELECT series_id, series_title, episode_count, 
                       total_size_gb, avg_size_mb, is_outlier
                FROM history 
                WHERE analysis_date = ?
            """, conn, params=(date2,))
            
            conn.close()
            
            if len(df1) == 0 or len(df2) == 0:
                return None
            
            # Merge on series_id
            comparison = df1.merge(
                df2,
                on='series_id',
                how='outer',
                suffixes=('_old', '_new')
            )
            
            # Fill NaN values (series that appeared/disappeared)
            comparison['series_title'] = comparison['series_title_new'].fillna(
                comparison['series_title_old']
            )
            
            # Calculate differences
            comparison['episodes_change'] = (
                comparison['episode_count_new'].fillna(0) - 
                comparison['episode_count_old'].fillna(0)
            ).astype(int)
            
            comparison['size_change_gb'] = (
                comparison['total_size_gb_new'].fillna(0) - 
                comparison['total_size_gb_old'].fillna(0)
            )
            
            comparison['avg_size_change_mb'] = (
                comparison['avg_size_mb_new'].fillna(0) - 
                comparison['avg_size_mb_old'].fillna(0)
            )
            
            # Calculate percentage changes
            comparison['size_change_pct'] = (
                comparison['size_change_gb'] / 
                comparison['total_size_gb_old'].replace(0, float('nan'))
            ) * 100
            
            # Detect new/removed series
            comparison['status'] = 'existing'
            comparison.loc[comparison['episode_count_old'].isna(), 'status'] = 'new'
            comparison.loc[comparison['episode_count_new'].isna(), 'status'] = 'removed'
            
            # Clean up columns
            comparison = comparison[[
                'series_id', 'series_title', 'status',
                'episode_count_old', 'episode_count_new', 'episodes_change',
                'total_size_gb_old', 'total_size_gb_new', 'size_change_gb', 'size_change_pct',
                'avg_size_mb_old', 'avg_size_mb_new', 'avg_size_change_mb'
            ]]
            
            # Sort by absolute size change
            comparison['abs_size_change'] = comparison['size_change_gb'].abs()
            comparison = comparison.sort_values('abs_size_change', ascending=False)
            comparison = comparison.drop('abs_size_change', axis=1)
            
            return comparison
            
        except Exception as e:
            print(f"Error comparing dates: {e}")
            return None
    
    def get_time_series(
        self,
        series_id: Optional[int] = None,
        metric: str = 'total_size_gb'
    ) -> Optional[pd.DataFrame]:
        """
        Get time series data for a specific metric.
        
        Args:
            series_id: Optional series ID to filter by
            metric: Metric to retrieve (total_size_gb, avg_size_mb, episode_count)
            
        Returns:
            DataFrame with time series data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            if series_id:
                query = f"""
                    SELECT analysis_date, series_title, {metric}
                    FROM history 
                    WHERE series_id = ?
                    ORDER BY analysis_date
                """
                df = pd.read_sql_query(query, conn, params=(series_id,))
            else:
                query = f"""
                    SELECT analysis_date, SUM({metric}) as {metric}
                    FROM history 
                    GROUP BY analysis_date
                    ORDER BY analysis_date
                """
                df = pd.read_sql_query(query, conn)
            
            conn.close()
            
            return df
            
        except Exception as e:
            print(f"Error getting time series: {e}")
            return None
    
    def get_global_trends(self) -> Optional[pd.DataFrame]:
        """
        Get global trend data from all analyses.
        
        Returns:
            DataFrame with trend data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            df = pd.read_sql_query("""
                SELECT * FROM analysis_summary 
                ORDER BY analysis_date
            """, conn)
            
            conn.close()
            
            return df
            
        except Exception as e:
            print(f"Error getting trends: {e}")
            return None
    
    def delete_analysis(self, analysis_date: str) -> Tuple[bool, str]:
        """
        Delete analysis data for a specific date.
        
        Args:
            analysis_date: Date to delete
            
        Returns:
            Tuple of (success, message)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM history WHERE analysis_date = ?",
                (analysis_date,)
            )
            
            cursor.execute(
                "DELETE FROM analysis_summary WHERE analysis_date = ?",
                (analysis_date,)
            )
            
            deleted_rows = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_rows > 0:
                return True, f"Deleted analysis from {analysis_date}"
            else:
                return False, "No data found for this date"
                
        except Exception as e:
            return False, f"Error deleting analysis: {str(e)}"
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> Tuple[bool, str]:
        """
        Delete analysis data older than specified days.
        
        Args:
            days_to_keep: Number of days to keep
            
        Returns:
            Tuple of (success, message)
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime("%Y-%m-%d")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM history WHERE analysis_date < ?",
                (cutoff_date,)
            )
            
            cursor.execute(
                "DELETE FROM analysis_summary WHERE analysis_date < ?",
                (cutoff_date,)
            )
            
            deleted_rows = cursor.rowcount
            conn.commit()
            conn.close()
            
            return True, f"Cleaned up {deleted_rows} old records (kept last {days_to_keep} days)"
            
        except Exception as e:
            return False, f"Error cleaning up data: {str(e)}"
    
    def export_to_csv(self, output_path: str) -> Tuple[bool, str]:
        """
        Export entire history database to CSV.
        
        Args:
            output_path: Path for output CSV file
            
        Returns:
            Tuple of (success, message)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            df = pd.read_sql_query("SELECT * FROM history ORDER BY analysis_date, series_title", conn)
            
            conn.close()
            
            df.to_csv(output_path, index=False)
            
            return True, f"Exported {len(df)} records to {output_path}"
            
        except Exception as e:
            return False, f"Error exporting: {str(e)}"


if __name__ == "__main__":
    # Test database functionality
    print("Testing history database...")
    
    db = HistoryDatabase("test_history.db")
    
    # Create sample data
    sample_df = pd.DataFrame({
        'series_id': [1, 2, 3],
        'title': ['Test Series 1', 'Test Series 2', 'Test Series 3'],
        'year': [2020, 2021, 2022],
        'status': ['continuing', 'ended', 'continuing'],
        'episode_count': [10, 20, 15],
        'total_size_gb': [5.0, 10.0, 7.5],
        'avg_size_mb': [500, 512, 510],
        'z_score': [0.1, 0.5, 0.3],
        'is_outlier': [False, False, False]
    })
    
    sample_stats = {
        'mean': 507.3,
        'std': 5.0,
        'outlier_count': 0,
        'outlier_percentage': 0.0
    }
    
    # Test save
    success, msg = db.save_analysis(sample_df, sample_stats)
    print(f"Save: {success} - {msg}")
    
    # Test load
    dates = db.get_analysis_dates()
    print(f"Available dates: {dates}")
    
    if dates:
        loaded_df = db.load_analysis(dates[0])
        print(f"Loaded {len(loaded_df)} series")
        
        summary = db.get_summary(dates[0])
        print(f"Summary: {summary}")
    
    print("\nTest complete!")

