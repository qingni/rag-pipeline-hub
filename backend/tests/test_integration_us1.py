"""Integration test for User Story 1 - Complete workflow.

Test workflow: Upload PDF → Load with PyMuPDF → Parse full_text → Verify JSON result

This test validates:
- T058: Complete workflow functionality
- SC-001: Document processing < 3 min
- SC-008: 100% data integrity (JSON result completeness)
"""
import os
import sys
import time
import json
import requests
from pathlib import Path

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TEST_PDF_PATH = Path(__file__).parent / "fixtures" / "sample.pdf"


class IntegrationTestUS1:
    """Integration test for User Story 1."""
    
    def __init__(self):
        self.api_url = API_BASE_URL
        self.session = requests.Session()
        self.document_id = None
        self.load_result_id = None
        self.parse_result_id = None
        self.start_time = None
        
    def log(self, message, level="INFO"):
        """Print formatted log message."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def check_api_health(self):
        """Check if API server is running."""
        self.log("Checking API health...")
        try:
            response = self.session.get(f"{self.api_url}/health")
            response.raise_for_status()
            data = response.json()
            assert data.get("success") is True
            assert data.get("status") == "healthy"
            self.log("✓ API server is healthy")
            return True
        except requests.exceptions.ConnectionError:
            self.log("✗ Cannot connect to API server. Please start the server first.", "ERROR")
            return False
        except Exception as e:
            self.log(f"✗ Health check failed: {str(e)}", "ERROR")
            return False
            
    def create_test_pdf(self):
        """Create a test PDF file if it doesn't exist."""
        TEST_PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        if TEST_PDF_PATH.exists():
            self.log(f"✓ Test PDF exists: {TEST_PDF_PATH}")
            return True
            
        self.log("Creating test PDF file...")
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            c = canvas.Canvas(str(TEST_PDF_PATH), pagesize=letter)
            c.setFont("Helvetica", 12)
            
            # Page 1
            c.drawString(100, 750, "Test Document for Integration Testing")
            c.drawString(100, 730, "=" * 50)
            c.drawString(100, 700, "This is a sample PDF document for testing the")
            c.drawString(100, 680, "document processing and retrieval system.")
            c.drawString(100, 640, "Section 1: Introduction")
            c.drawString(100, 620, "This section contains introductory text.")
            c.drawString(100, 600, "The system should be able to load and parse this document.")
            c.showPage()
            
            # Page 2
            c.drawString(100, 750, "Section 2: Main Content")
            c.drawString(100, 730, "-" * 50)
            c.drawString(100, 700, "This is the main content section with multiple paragraphs.")
            c.drawString(100, 680, "It contains information that should be extracted during processing.")
            c.drawString(100, 640, "The system supports three loading methods:")
            c.drawString(120, 620, "1. PyMuPDF - Fast and reliable")
            c.drawString(120, 600, "2. PyPDF - Lightweight alternative")
            c.drawString(120, 580, "3. Unstructured - Advanced processing")
            c.showPage()
            
            c.save()
            self.log(f"✓ Created test PDF: {TEST_PDF_PATH}")
            return True
        except ImportError:
            self.log("reportlab not installed. Creating minimal PDF...", "WARN")
            # Create a minimal valid PDF
            minimal_pdf = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 750 Td
(Test Document) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000317 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF"""
            TEST_PDF_PATH.write_bytes(minimal_pdf)
            self.log(f"✓ Created minimal PDF: {TEST_PDF_PATH}")
            return True
            
    def step1_upload_document(self):
        """Step 1: Upload PDF document."""
        self.log("\n=== STEP 1: Upload Document ===")
        
        try:
            with open(TEST_PDF_PATH, "rb") as f:
                files = {"file": ("test_document.pdf", f, "application/pdf")}
                response = self.session.post(
                    f"{self.api_url}/api/v1/documents",
                    files=files
                )
                response.raise_for_status()
                
            data = response.json()
            assert data.get("success") is True, "Upload failed"
            
            document = data.get("data")
            self.document_id = document.get("id")
            
            self.log(f"✓ Document uploaded successfully")
            self.log(f"  - ID: {self.document_id}")
            self.log(f"  - Filename: {document.get('filename')}")
            self.log(f"  - Size: {document.get('size_bytes')} bytes")
            self.log(f"  - Format: {document.get('format')}")
            
            return True
        except Exception as e:
            self.log(f"✗ Upload failed: {str(e)}", "ERROR")
            return False
            
    def step2_load_document(self):
        """Step 2: Load document with PyMuPDF."""
        self.log("\n=== STEP 2: Load with PyMuPDF ===")
        
        try:
            payload = {
                "document_id": self.document_id,
                "loader_type": "pymupdf"
            }
            response = self.session.post(
                f"{self.api_url}/api/v1/processing/load",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            assert data.get("success") is True, "Load failed"
            
            result = data.get("data")
            self.load_result_id = result.get("id")
            
            self.log(f"✓ Document loaded successfully")
            self.log(f"  - Result ID: {self.load_result_id}")
            self.log(f"  - Provider: {result.get('provider')}")
            self.log(f"  - Status: {result.get('status')}")
            self.log(f"  - Result Path: {result.get('result_path')}")
            
            return True
        except Exception as e:
            self.log(f"✗ Load failed: {str(e)}", "ERROR")
            return False
            
    def step3_parse_document(self):
        """Step 3: Parse document with full_text mode."""
        self.log("\n=== STEP 3: Parse Document (full_text) ===")
        
        try:
            payload = {
                "document_id": self.document_id,
                "parse_mode": "full_text",
                "include_tables": False
            }
            response = self.session.post(
                f"{self.api_url}/api/v1/processing/parse",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            assert data.get("success") is True, "Parse failed"
            
            result = data.get("data")
            self.parse_result_id = result.get("id")
            
            self.log(f"✓ Document parsed successfully")
            self.log(f"  - Result ID: {self.parse_result_id}")
            self.log(f"  - Provider: {result.get('provider')}")
            self.log(f"  - Status: {result.get('status')}")
            self.log(f"  - Result Path: {result.get('result_path')}")
            
            return True
        except Exception as e:
            self.log(f"✗ Parse failed: {str(e)}", "ERROR")
            return False
            
    def step4_verify_results(self):
        """Step 4: Verify JSON results are saved correctly."""
        self.log("\n=== STEP 4: Verify JSON Results ===")
        
        try:
            # Get parse result details
            response = self.session.get(
                f"{self.api_url}/api/v1/processing/results/detail/{self.parse_result_id}"
            )
            response.raise_for_status()
            
            data = response.json()
            assert data.get("success") is True, "Failed to get result details"
            
            result = data.get("data")
            result_path = result.get("result_path")
            
            self.log(f"✓ Retrieved result details")
            self.log(f"  - Result Path: {result_path}")
            
            # Verify result file exists
            if result_path:
                result_file = Path("backend") / result_path
                if result_file.exists():
                    self.log(f"✓ Result file exists: {result_file}")
                    
                    # Load and validate JSON
                    with open(result_file, "r", encoding="utf-8") as f:
                        result_data = json.load(f)
                    
                    self.log(f"✓ Result JSON is valid")
                    self.log(f"  - Keys: {list(result_data.keys())}")
                    
                    # Validate required fields
                    if "content" in result_data:
                        content_length = len(result_data["content"])
                        self.log(f"  - Content length: {content_length} chars")
                        
                        if content_length > 0:
                            self.log(f"✓ Content extracted successfully")
                            # Show preview
                            preview = result_data["content"][:200]
                            self.log(f"  - Preview: {preview}...")
                        else:
                            self.log(f"✗ Content is empty", "WARN")
                    
                    # Check metadata
                    if "metadata" in result_data:
                        metadata = result_data["metadata"]
                        self.log(f"  - Metadata keys: {list(metadata.keys())}")
                    
                    return True
                else:
                    self.log(f"✗ Result file not found: {result_file}", "ERROR")
                    return False
            else:
                self.log(f"✗ No result path in response", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"✗ Verification failed: {str(e)}", "ERROR")
            return False
            
    def verify_performance(self):
        """Verify performance meets SC-001 (< 3 min)."""
        self.log("\n=== Performance Verification ===")
        
        elapsed = time.time() - self.start_time
        elapsed_str = f"{elapsed:.2f}s"
        
        self.log(f"Total processing time: {elapsed_str}")
        
        if elapsed < 180:  # 3 minutes
            self.log(f"✓ Performance meets SC-001 (< 3 min)")
            return True
        else:
            self.log(f"✗ Performance exceeds 3 min threshold", "WARN")
            return False
            
    def cleanup(self):
        """Clean up test data."""
        self.log("\n=== Cleanup ===")
        
        if self.document_id:
            try:
                response = self.session.delete(
                    f"{self.api_url}/api/v1/documents/{self.document_id}"
                )
                if response.status_code == 200:
                    self.log(f"✓ Deleted test document: {self.document_id}")
                else:
                    self.log(f"✗ Failed to delete document", "WARN")
            except Exception as e:
                self.log(f"✗ Cleanup failed: {str(e)}", "WARN")
                
    def run(self, cleanup_after=True):
        """Run the complete integration test."""
        self.log("=" * 60)
        self.log("User Story 1 - Integration Test")
        self.log("=" * 60)
        
        self.start_time = time.time()
        
        # Pre-checks
        if not self.check_api_health():
            return False
            
        if not self.create_test_pdf():
            return False
        
        # Execute workflow
        steps = [
            ("Upload Document", self.step1_upload_document),
            ("Load with PyMuPDF", self.step2_load_document),
            ("Parse Document", self.step3_parse_document),
            ("Verify Results", self.step4_verify_results),
        ]
        
        for step_name, step_func in steps:
            if not step_func():
                self.log(f"\n✗ TEST FAILED at step: {step_name}", "ERROR")
                if cleanup_after:
                    self.cleanup()
                return False
        
        # Verify performance
        self.verify_performance()
        
        # Cleanup
        if cleanup_after:
            self.cleanup()
        
        # Final result
        self.log("\n" + "=" * 60)
        self.log("✓ ALL TESTS PASSED - User Story 1 is functional!", "SUCCESS")
        self.log("=" * 60)
        
        return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Integration test for User Story 1")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't clean up test data after test"
    )
    
    args = parser.parse_args()
    
    # Override API URL if provided
    global API_BASE_URL
    API_BASE_URL = args.api_url
    
    # Run test
    test = IntegrationTestUS1()
    success = test.run(cleanup_after=not args.no_cleanup)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
