#!/usr/bin/env python3
"""
Test script for embedding from chunking results.

This script demonstrates the new workflow:
1. Load a document
2. Chunk the document
3. Embed the chunks (automatic)

Usage:
    python test_embedding_from_chunks.py
"""
import os
import sys
import requests
import json
from pathlib import Path

# API base URL
BASE_URL = "http://localhost:8000/api"

def test_embedding_from_chunking_result():
    """Test embedding from a specific chunking result ID."""
    print("\n=== Test 1: Embed from Chunking Result ===")
    
    # Example: Get a chunking result first
    # This would typically come from the chunking API
    result_id = input("Enter chunking result ID (or press Enter to skip): ").strip()
    
    if not result_id:
        print("Skipping test 1...")
        return
    
    # Request embedding for all chunks in the result
    request_data = {
        "result_id": result_id,
        "model": "qwen3-embedding-8b",
        "max_retries": 3,
        "timeout": 60
    }
    
    print(f"\nSending request to {BASE_URL}/embedding/from-chunking-result")
    print(f"Request data: {json.dumps(request_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/embedding/from-chunking-result",
            json=request_data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Success!")
            print(f"Request ID: {result['request_id']}")
            print(f"Status: {result['status']}")
            print(f"Vectors generated: {len(result['vectors'])}")
            print(f"Failures: {len(result['failures'])}")
            
            if result['vectors']:
                first_vector = result['vectors'][0]
                print(f"\nFirst vector sample:")
                print(f"  - Index: {first_vector['index']}")
                print(f"  - Dimension: {first_vector['dimension']}")
                print(f"  - Text length: {first_vector['text_length']}")
                print(f"  - Vector preview: [{first_vector['vector'][0]:.6f}, {first_vector['vector'][1]:.6f}, ...]")
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.json())
    
    except Exception as e:
        print(f"\n❌ Exception: {e}")


def test_embedding_from_document():
    """Test embedding from a document's latest chunking result."""
    print("\n=== Test 2: Embed from Document (Latest Chunking Result) ===")
    
    # Example: Get document ID
    document_id = input("Enter document ID (or press Enter to skip): ").strip()
    
    if not document_id:
        print("Skipping test 2...")
        return
    
    # Optional: filter by strategy type
    strategy_type = input("Enter strategy type (character/paragraph/heading/semantic, or press Enter for any): ").strip()
    
    # Request embedding for latest chunking result
    request_data = {
        "document_id": document_id,
        "model": "qwen3-embedding-8b",
        "max_retries": 3,
        "timeout": 60
    }
    
    if strategy_type:
        request_data["strategy_type"] = strategy_type
    
    print(f"\nSending request to {BASE_URL}/embedding/from-document")
    print(f"Request data: {json.dumps(request_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/embedding/from-document",
            json=request_data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Success!")
            print(f"Request ID: {result['request_id']}")
            print(f"Status: {result['status']}")
            print(f"Vectors generated: {len(result['vectors'])}")
            print(f"Failures: {len(result['failures'])}")
            
            # Show metadata
            metadata = result['metadata']
            print(f"\nMetadata:")
            print(f"  - Model: {metadata['model']}")
            print(f"  - Batch size: {metadata['batch_size']}")
            print(f"  - Successful: {metadata['successful_count']}")
            print(f"  - Failed: {metadata['failed_count']}")
            print(f"  - Processing time: {metadata['processing_time_ms']:.2f}ms")
            print(f"  - Vectors/second: {metadata['vectors_per_second']:.2f}")
            
            if result['vectors']:
                print(f"\nVector dimensions: {result['vectors'][0]['dimension']}")
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.json())
    
    except Exception as e:
        print(f"\n❌ Exception: {e}")


def test_single_text_embedding():
    """Test traditional single text embedding (for comparison)."""
    print("\n=== Test 3: Single Text Embedding (Traditional) ===")
    
    text = input("Enter text to embed (or press Enter to skip): ").strip()
    
    if not text:
        print("Skipping test 3...")
        return
    
    request_data = {
        "text": text,
        "model": "qwen3-embedding-8b",
        "max_retries": 3,
        "timeout": 60
    }
    
    print(f"\nSending request to {BASE_URL}/embedding/single")
    
    try:
        response = requests.post(
            f"{BASE_URL}/embedding/single",
            json=request_data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Success!")
            print(f"Request ID: {result['request_id']}")
            print(f"Vector dimension: {result['vector']['dimension']}")
            print(f"Text length: {result['vector']['text_length']}")
            print(f"Processing time: {result['metadata']['processing_time_ms']:.2f}ms")
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.json())
    
    except Exception as e:
        print(f"\n❌ Exception: {e}")


def list_available_models():
    """List all available embedding models."""
    print("\n=== Available Embedding Models ===")
    
    try:
        response = requests.get(f"{BASE_URL}/embedding/models")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nTotal models: {result['count']}")
            
            for model in result['models']:
                print(f"\n{model['name']}:")
                print(f"  - Dimension: {model['dimension']}")
                print(f"  - Provider: {model['provider']}")
                print(f"  - Description: {model['description']}")
                print(f"  - Multilingual: {'Yes' if model['supports_multilingual'] else 'No'}")
                print(f"  - Max batch size: {model['max_batch_size']}")
        else:
            print(f"❌ Error: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Exception: {e}")


def main():
    """Main test runner."""
    print("=" * 60)
    print("Embedding from Chunking Results - Test Script")
    print("=" * 60)
    
    # Check if backend is running
    try:
        response = requests.get(f"{BASE_URL}/embedding/health", timeout=5)
        print(f"\n✅ Backend is running (status: {response.json()['status']})")
    except Exception as e:
        print(f"\n❌ Backend is not accessible: {e}")
        print(f"Please start the backend server first:")
        print(f"  cd backend && python -m uvicorn src.main:app --reload")
        sys.exit(1)
    
    # List available models
    list_available_models()
    
    # Run tests
    print("\n" + "=" * 60)
    print("Choose a test to run:")
    print("1. Embed from chunking result ID")
    print("2. Embed from document ID (latest chunking result)")
    print("3. Single text embedding (traditional)")
    print("4. Run all tests")
    print("0. Exit")
    print("=" * 60)
    
    choice = input("\nEnter your choice: ").strip()
    
    if choice == "1":
        test_embedding_from_chunking_result()
    elif choice == "2":
        test_embedding_from_document()
    elif choice == "3":
        test_single_text_embedding()
    elif choice == "4":
        test_embedding_from_chunking_result()
        test_embedding_from_document()
        test_single_text_embedding()
    elif choice == "0":
        print("\nExiting...")
    else:
        print("\n❌ Invalid choice")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
