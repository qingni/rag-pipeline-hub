"""File storage management."""
import os
import shutil
import hashlib
from pathlib import Path
from typing import BinaryIO
from ..config import settings


class FileStorageManager:
    """Manage file upload and storage operations."""
    
    def __init__(self):
        """Initialize file storage manager."""
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def save_upload(self, file: BinaryIO, filename: str) -> tuple[str, str]:
        """
        Save uploaded file to storage.
        
        Args:
            file: File object to save
            filename: Original filename
            
        Returns:
            Tuple of (storage_path, content_hash)
        """
        # Generate unique filename
        file_hash = self._calculate_hash(file)
        file.seek(0)  # Reset file pointer
        
        # Create subdirectory based on first 2 chars of hash
        subdir = self.upload_dir / file_hash[:2]
        subdir.mkdir(exist_ok=True)
        
        # Save file
        storage_path = subdir / f"{file_hash}_{filename}"
        with open(storage_path, "wb") as f:
            shutil.copyfileobj(file, f)
        
        return str(storage_path), file_hash
    
    def save_upload_bytes(self, content: bytes, filename: str) -> tuple[str, str]:
        """
        Save uploaded file bytes to storage (for async operations).
        
        Args:
            content: File content as bytes
            filename: Original filename
            
        Returns:
            Tuple of (storage_path, content_hash)
        """
        # Calculate hash from bytes
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Create subdirectory based on first 2 chars of hash
        subdir = self.upload_dir / file_hash[:2]
        subdir.mkdir(exist_ok=True)
        
        # Save file
        storage_path = subdir / f"{file_hash}_{filename}"
        with open(storage_path, "wb") as f:
            f.write(content)
        
        return str(storage_path), file_hash
    
    def get_file_path(self, storage_path: str) -> Path:
        """
        Get full path to stored file.
        
        Args:
            storage_path: Relative or absolute storage path
            
        Returns:
            Path object
        """
        path = Path(storage_path)
        if not path.is_absolute():
            path = Path(settings.UPLOAD_DIR) / path
        return path
    
    def delete_file(self, storage_path: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            storage_path: Path to file
            
        Returns:
            True if deleted successfully
        """
        try:
            path = self.get_file_path(storage_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False
    
    def _calculate_hash(self, file: BinaryIO) -> str:
        """
        Calculate SHA256 hash of file.
        
        Args:
            file: File object
            
        Returns:
            Hexadecimal hash string
        """
        sha256 = hashlib.sha256()
        for chunk in iter(lambda: file.read(8192), b""):
            sha256.update(chunk)
        return sha256.hexdigest()


# Global instance
file_storage = FileStorageManager()
