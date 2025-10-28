"""
Security module for encrypting and managing Sonarr credentials.
Uses Fernet symmetric encryption (AES-128) from cryptography library.
"""

import os
import json
import base64
from pathlib import Path
from typing import Optional, Tuple
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CredentialManager:
    """Manages encrypted storage of Sonarr credentials."""
    
    def __init__(self, credentials_file: str = ".sonarr_credentials.enc"):
        """
        Initialize credential manager.
        
        Args:
            credentials_file: Path to encrypted credentials file
        """
        self.credentials_file = Path(credentials_file)
        self.salt_file = Path(".sonarr_salt")
    
    def _derive_key(self, passphrase: str, salt: bytes) -> bytes:
        """
        Derive encryption key from passphrase using PBKDF2.
        
        Args:
            passphrase: User's master passphrase
            salt: Random salt for key derivation
            
        Returns:
            Derived encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        return key
    
    def _get_or_create_salt(self) -> bytes:
        """
        Get existing salt or create new one.
        
        Returns:
            Salt bytes
        """
        if self.salt_file.exists():
            with open(self.salt_file, 'rb') as f:
                return f.read()
        else:
            salt = os.urandom(16)
            with open(self.salt_file, 'wb') as f:
                f.write(salt)
            # Set restrictive permissions
            os.chmod(self.salt_file, 0o600)
            return salt
    
    def save_credentials(
        self,
        base_url: str,
        api_key: str,
        passphrase: str
    ) -> Tuple[bool, str]:
        """
        Encrypt and save Sonarr credentials.
        
        Args:
            base_url: Sonarr base URL
            api_key: Sonarr API key
            passphrase: Master passphrase for encryption
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate inputs
            if not base_url or not api_key:
                return False, "URL and API key cannot be empty"
            
            if len(passphrase) < 8:
                return False, "Passphrase must be at least 8 characters"
            
            # Get or create salt
            salt = self._get_or_create_salt()
            
            # Derive encryption key
            key = self._derive_key(passphrase, salt)
            fernet = Fernet(key)
            
            # Prepare data
            data = {
                'base_url': base_url,
                'api_key': api_key
            }
            
            # Encrypt
            json_data = json.dumps(data).encode()
            encrypted_data = fernet.encrypt(json_data)
            
            # Save to file
            with open(self.credentials_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Set restrictive permissions (Unix-like systems)
            try:
                os.chmod(self.credentials_file, 0o600)
            except:
                pass  # Windows doesn't support chmod
            
            return True, "Credentials saved successfully"
            
        except Exception as e:
            return False, f"Error saving credentials: {str(e)}"
    
    def load_credentials(
        self,
        passphrase: str
    ) -> Tuple[bool, Optional[dict], str]:
        """
        Decrypt and load Sonarr credentials.
        
        Args:
            passphrase: Master passphrase for decryption
            
        Returns:
            Tuple of (success, credentials_dict, message)
        """
        try:
            # Check if credentials file exists
            if not self.credentials_file.exists():
                return False, None, "No saved credentials found"
            
            if not self.salt_file.exists():
                return False, None, "Encryption salt file not found"
            
            # Read salt
            with open(self.salt_file, 'rb') as f:
                salt = f.read()
            
            # Derive key
            key = self._derive_key(passphrase, salt)
            fernet = Fernet(key)
            
            # Read encrypted data
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt
            try:
                decrypted_data = fernet.decrypt(encrypted_data)
                credentials = json.loads(decrypted_data.decode())
                
                return True, credentials, "Credentials loaded successfully"
                
            except InvalidToken:
                return False, None, "Invalid passphrase"
            
        except Exception as e:
            return False, None, f"Error loading credentials: {str(e)}"
    
    def credentials_exist(self) -> bool:
        """
        Check if encrypted credentials file exists.
        
        Returns:
            True if credentials are saved
        """
        return self.credentials_file.exists() and self.salt_file.exists()
    
    def delete_credentials(self) -> Tuple[bool, str]:
        """
        Delete saved credentials and salt files.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            deleted_files = []
            
            if self.credentials_file.exists():
                self.credentials_file.unlink()
                deleted_files.append("credentials")
            
            if self.salt_file.exists():
                self.salt_file.unlink()
                deleted_files.append("salt")
            
            if deleted_files:
                return True, f"Deleted: {', '.join(deleted_files)}"
            else:
                return True, "No credentials found to delete"
                
        except Exception as e:
            return False, f"Error deleting credentials: {str(e)}"


def test_encryption():
    """Test encryption/decryption functionality."""
    print("Testing credential encryption...")
    
    manager = CredentialManager(".test_creds.enc")
    
    # Test data
    test_url = "http://localhost:8989"
    test_key = "test_api_key_12345"
    test_pass = "my_secure_password"
    
    # Save
    success, msg = manager.save_credentials(test_url, test_key, test_pass)
    print(f"Save: {success} - {msg}")
    
    # Load with correct passphrase
    success, creds, msg = manager.load_credentials(test_pass)
    print(f"Load (correct): {success} - {msg}")
    if success:
        print(f"  URL: {creds['base_url']}")
        print(f"  Key: {'*' * 20}{creds['api_key'][-4:]}")
    
    # Load with wrong passphrase
    success, creds, msg = manager.load_credentials("wrong_password")
    print(f"Load (wrong): {success} - {msg}")
    
    # Delete
    success, msg = manager.delete_credentials()
    print(f"Delete: {success} - {msg}")
    
    print("\nTest complete!")


if __name__ == "__main__":
    test_encryption()

