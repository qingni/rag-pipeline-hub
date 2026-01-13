"""VTT (WebVTT) subtitle loader using webvtt-py."""
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Check if webvtt-py is available
WEBVTT_AVAILABLE = False
WEBVTT_UNAVAILABLE_REASON = None

try:
    import webvtt
    WEBVTT_AVAILABLE = True
except ImportError as e:
    WEBVTT_UNAVAILABLE_REASON = f"webvtt-py not installed: {str(e)}. Install with: pip install webvtt-py"


class VTTLoader:
    """Load VTT (WebVTT) subtitle documents using webvtt-py."""
    
    def __init__(self):
        """Initialize VTT loader."""
        self.name = "vtt"
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from VTT subtitle document.
        
        Args:
            file_path: Path to VTT file
            
        Returns:
            Dictionary with extracted content
        """
        if not WEBVTT_AVAILABLE:
            return self._extract_fallback(file_path)
        
        try:
            # Read VTT file
            captions = webvtt.read(file_path)
            
            text_parts = []
            timestamps = []
            
            for caption in captions:
                text_parts.append(caption.text)
                timestamps.append({
                    'start': caption.start,
                    'end': caption.end,
                    'text': caption.text
                })
            
            full_text = '\n'.join(text_parts)
            
            # Create page
            pages = [{
                "page_number": 1,
                "text": full_text,
                "char_count": len(full_text)
            }]
            
            return {
                "success": True,
                "loader": self.name,
                "metadata": {
                    "format": "vtt",
                    "caption_count": len(captions),
                    "timestamps": timestamps[:10]  # First 10 for preview
                },
                "pages": pages,
                "full_text": full_text,
                "total_pages": 1,
                "total_chars": len(full_text)
            }
            
        except Exception as e:
            logger.error(f"VTT extraction failed: {str(e)}", exc_info=True)
            return self._extract_fallback(file_path)
    
    def _extract_fallback(self, file_path: str) -> Dict[str, Any]:
        """Fallback extraction without webvtt-py."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple parsing: remove timestamps and metadata
            lines = content.split('\n')
            text_parts = []
            
            for line in lines:
                line = line.strip()
                # Skip WEBVTT header, timestamps, and empty lines
                if not line or line.startswith('WEBVTT') or '-->' in line:
                    continue
                # Skip numeric cue identifiers
                if line.isdigit():
                    continue
                text_parts.append(line)
            
            full_text = '\n'.join(text_parts)
            
            pages = [{
                "page_number": 1,
                "text": full_text,
                "char_count": len(full_text)
            }]
            
            return {
                "success": True,
                "loader": self.name,
                "metadata": {
                    "format": "vtt",
                    "parsed_with": "fallback"
                },
                "pages": pages,
                "full_text": full_text,
                "total_pages": 1,
                "total_chars": len(full_text)
            }
            
        except Exception as e:
            logger.error(f"VTT fallback extraction failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }
    
    def is_available(self) -> bool:
        """Check if loader is available."""
        return True  # Fallback always available
    
    def get_unavailable_reason(self) -> Optional[str]:
        """Get reason why loader is unavailable."""
        return None


# Global instance
vtt_loader = VTTLoader()
