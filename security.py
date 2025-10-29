"""
Security module for encrypting and managing per-user Sonarr credentials.
Uses Fernet symmetric encryption (AES-128) with a master encryption key.
"""

import os
import json
import base64
import sqlite3
from pathlib import Path
from typing import Optional, Tuple, Dict
from cryptography.fernet import Fernet, InvalidToken


class TokenManager:
    """Manages encrypted storage of per-user Sonarr API tokens."""
    
    def __init__(self, db_path: str = "data/tokens.db", key_file: str = "data/.master.key"):
        """
        Initialize token manager with master encryption key.
        
        Args:
            db_path: Path to SQLite database for encrypted tokens
            key_file: Path to master encryption key file
        """
        self.db_path = Path(db_path)
        self.key_file = Path(key_file)
        self.db_path.parent.mkdir(exist_ok=True)
        self.key_file.parent.mkdir(exist_ok=True)
        
        # Initialize or load master key
        self.master_key = self._get_or_create_master_key()
        self.fernet = Fernet(self.master_key)
        
        # Initialize database
        self._init_database()
    
    def _get_or_create_master_key(self) -> bytes:
        """
        Get existing master key or create a new one.
        The master key is used to encrypt all user tokens.
        
        Returns:
            Master encryption key
        """
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new Fernet key
            key = Fernet.generate_key()
            
            # Save to file with restrictive permissions
            with open(self.key_file, 'wb') as f:
                f.write(key)
            
            # Set restrictive permissions (Unix-like systems)
            try:
                os.chmod(self.key_file, 0o600)
            except:
                pass  # Windows doesn't support chmod
            
            return key
    
    def _init_database(self):
        """Create tokens database table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_tokens (
                user_id INTEGER PRIMARY KEY,
                sonarr_url TEXT NOT NULL,
                encrypted_token TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_token(
        self,
        user_id: int,
        sonarr_url: str,
        api_token: str
    ) -> Tuple[bool, str]:
        """
        Encrypt and save Sonarr token for a user.
        
        Args:
            user_id: User ID
            sonarr_url: Sonarr base URL
            api_token: Sonarr API key/token
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate inputs
            if not sonarr_url or not api_token:
                return False, "URL and API token cannot be empty"
            
            # Prepare data
            data = {
                'sonarr_url': sonarr_url,
                'api_token': api_token
            }
            
            # Encrypt
            json_data = json.dumps(data).encode()
            encrypted_data = self.fernet.encrypt(json_data)
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            from datetime import datetime
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_tokens (user_id, sonarr_url, encrypted_token, updated_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, sonarr_url, encrypted_data.decode('utf-8'), datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            return True, "Sonarr token saved successfully"
            
        except Exception as e:
            return False, f"Error saving token: {str(e)}"
    
    def load_token(
        self,
        user_id: int
    ) -> Tuple[bool, Optional[Dict], str]:
        """
        Decrypt and load Sonarr token for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (success, credentials_dict, message)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT sonarr_url, encrypted_token
                FROM user_tokens
                WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return False, None, "No Sonarr token found for this user"
            
            sonarr_url, encrypted_token = row
            
            # Decrypt
            try:
                decrypted_data = self.fernet.decrypt(encrypted_token.encode('utf-8'))
                data = json.loads(decrypted_data.decode())
                
                return True, data, "Token loaded successfully"
                
            except InvalidToken:
                return False, None, "Invalid encryption key"
            
        except Exception as e:
            return False, None, f"Error loading token: {str(e)}"
    
    def has_token(self, user_id: int) -> bool:
        """
        Check if user has a saved token.
        
        Args:
            user_id: User ID
            
        Returns:
            True if user has a saved token
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM user_tokens WHERE user_id = ?
            """, (user_id,))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count > 0
            
        except Exception:
            return False
    
    def delete_token(self, user_id: int) -> Tuple[bool, str]:
        """
        Delete saved token for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (success, message)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM user_tokens WHERE user_id = ?", (user_id,))
            
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if deleted:
                return True, "Token deleted successfully"
            else:
                return True, "No token found to delete"
                
        except Exception as e:
            return False, f"Error deleting token: {str(e)}"


def test_token_manager():
    """Test token encryption/decryption functionality."""
    print("Testing TokenManager...")
    
    manager = TokenManager("test_tokens.db", "test_master.key")
    
    # Test data
    test_user_id = 1
    test_url = "http://localhost:8989"
    test_token = "test_api_token_12345"
    
    # Save token
    success, msg = manager.save_token(test_user_id, test_url, test_token)
    print(f"Save token: {success} - {msg}")
    
    # Check if token exists
    has_token = manager.has_token(test_user_id)
    print(f"Has token: {has_token}")
    
    # Load token
    success, data, msg = manager.load_token(test_user_id)
    print(f"Load token: {success} - {msg}")
    if success:
        print(f"  URL: {data['sonarr_url']}")
        print(f"  Token: {'*' * 20}{data['api_token'][-4:]}")
    
    # Delete token
    success, msg = manager.delete_token(test_user_id)
    print(f"Delete token: {success} - {msg}")
    
    print("\nTest complete!")


if __name__ == "__main__":
    test_token_manager()

