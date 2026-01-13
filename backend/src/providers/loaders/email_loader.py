"""Email (EML) document loader using Python's email module."""
from typing import Dict, Any, Optional
from pathlib import Path
import email
from email import policy
from email.parser import BytesParser
import logging

logger = logging.getLogger(__name__)


class EmailLoader:
    """Load EML email documents using Python's email module."""
    
    def __init__(self):
        """Initialize Email loader."""
        self.name = "email"
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from EML email document.
        
        Args:
            file_path: Path to EML file
            
        Returns:
            Dictionary with extracted content
        """
        try:
            # Read email file
            with open(file_path, 'rb') as f:
                msg = BytesParser(policy=policy.default).parse(f)
            
            # Extract headers
            subject = msg.get('Subject', '')
            from_addr = msg.get('From', '')
            to_addr = msg.get('To', '')
            date = msg.get('Date', '')
            
            # Extract body
            body_parts = []
            attachments = []
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition', ''))
                    
                    # Skip attachments for text extraction
                    if 'attachment' in content_disposition:
                        attachments.append({
                            'filename': part.get_filename(),
                            'content_type': content_type
                        })
                        continue
                    
                    if content_type == 'text/plain':
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_parts.append(payload.decode('utf-8', errors='ignore'))
                    elif content_type == 'text/html':
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_text = self._html_to_text(payload.decode('utf-8', errors='ignore'))
                            body_parts.append(html_text)
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body_parts.append(payload.decode('utf-8', errors='ignore'))
            
            body = '\n\n'.join(body_parts)
            
            # Create full text with headers
            full_text = f"""Subject: {subject}
From: {from_addr}
To: {to_addr}
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
                    "from": from_addr,
                    "to": to_addr,
                    "date": date,
                    "format": "eml",
                    "attachment_count": len(attachments),
                    "attachments": attachments
                },
                "pages": pages,
                "full_text": full_text,
                "total_pages": 1,
                "total_chars": len(full_text)
            }
            
        except Exception as e:
            logger.error(f"Email extraction failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            for element in soup(['script', 'style']):
                element.decompose()
            return soup.get_text(separator='\n', strip=True)
        except ImportError:
            # Basic HTML tag removal
            import re
            text = re.sub(r'<[^>]+>', '', html)
            return text.strip()
    
    def is_available(self) -> bool:
        """Check if loader is available."""
        return True
    
    def get_unavailable_reason(self) -> Optional[str]:
        """Get reason why loader is unavailable."""
        return None


# Global instance
email_loader = EmailLoader()
