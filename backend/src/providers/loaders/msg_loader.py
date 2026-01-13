"""MSG (Outlook) document loader using extract-msg."""
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Check if extract-msg is available
MSG_AVAILABLE = False
MSG_UNAVAILABLE_REASON = None

try:
    import extract_msg
    MSG_AVAILABLE = True
except ImportError as e:
    MSG_UNAVAILABLE_REASON = f"extract-msg not installed: {str(e)}. Install with: pip install extract-msg"


class MSGLoader:
    """Load MSG (Outlook) documents using extract-msg."""
    
    def __init__(self):
        """Initialize MSG loader."""
        self.name = "msg"
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from MSG document.
        
        Args:
            file_path: Path to MSG file
            
        Returns:
            Dictionary with extracted content
        """
        if not MSG_AVAILABLE:
            return {
                "success": False,
                "loader": self.name,
                "error": MSG_UNAVAILABLE_REASON
            }
        
        try:
            # Read MSG file
            msg = extract_msg.Message(file_path)
            
            # Extract headers
            subject = msg.subject or ''
            sender = msg.sender or ''
            to = msg.to or ''
            date = str(msg.date) if msg.date else ''
            
            # Extract body
            body = msg.body or ''
            
            # Get attachments info
            attachments = []
            for attachment in msg.attachments:
                attachments.append({
                    'filename': attachment.longFilename or attachment.shortFilename,
                    'size': len(attachment.data) if attachment.data else 0
                })
            
            msg.close()
            
            # Create full text with headers
            full_text = f"""Subject: {subject}
From: {sender}
To: {to}
Date: {date}

{body}"""
            
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
                    "subject": subject,
                    "from": sender,
                    "to": to,
                    "date": date,
                    "format": "msg",
                    "attachment_count": len(attachments),
                    "attachments": attachments
                },
                "pages": pages,
                "full_text": full_text,
                "total_pages": 1,
                "total_chars": len(full_text)
            }
            
        except Exception as e:
            logger.error(f"MSG extraction failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }
    
    def is_available(self) -> bool:
        """Check if loader is available."""
        return MSG_AVAILABLE
    
    def get_unavailable_reason(self) -> Optional[str]:
        """Get reason why loader is unavailable."""
        return MSG_UNAVAILABLE_REASON


# Global instance
msg_loader = MSGLoader()
