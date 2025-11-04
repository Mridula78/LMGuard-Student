"""
Quick diagnostic script to test Gemini API connection.
Run this from the backend directory to verify your API key works.

Usage: python test_gemini_connection.py
"""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

def test_gemini_api():
    """Test if Gemini API key is working."""
    
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY not found in environment")
        print("   Make sure you have a .env file with GOOGLE_API_KEY=your_key")
        return False
    
    print(f"✓ Found API key: {api_key[:10]}...")
    
    # Test API call
    payload = {
        "contents": [
            {
                "parts": [{"text": "Hello! Just testing the connection. Reply with 'OK'."}]
            }
        ]
    }
    
    try:
        print("\n🔄 Testing Gemini API connection...")
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            
            print(f"   Status code: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"❌ API Error: {resp.status_code}")
                print(f"   Response: {resp.text}")
                return False
            
            data = resp.json()
            
            # Extract response
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "")
                    print(f"✅ SUCCESS! Gemini responded with: {text}")
                    return True
            
            print(f"❌ Unexpected response format: {data}")
            return False
            
    except httpx.TimeoutException:
        print("❌ ERROR: Request timed out")
        return False
    
    except httpx.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}")
        return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_embedding_api():
    """Test if Gemini embedding API is working."""
    
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        return False
    
    try:
        print("\n🔄 Testing Gemini Embedding API...")
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedText",
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json={"content": {"parts": [{"text": "test embedding"}]}},
            )
            
            print(f"   Status code: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"❌ Embedding API Error: {resp.status_code}")
                print(f"   Response: {resp.text}")
                return False
            
            data = resp.json()
            embedding = data.get("embedding", {})
            values = embedding.get("values", [])
            
            if values:
                print(f"✅ Embedding API working! Got {len(values)}-dimensional vector")
                return True
            else:
                print(f"❌ No embedding values in response: {data}")
                return False
                
    except Exception as e:
        print(f"❌ Embedding API error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("LMGuard - Gemini API Connection Test")
    print("=" * 60)
    
    # Test generation API
    gen_success = test_gemini_api()
    
    # Test embedding API
    emb_success = test_embedding_api()
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print(f"  Gemini Generation API: {'✅ WORKING' if gen_success else '❌ FAILED'}")
    print(f"  Gemini Embedding API:  {'✅ WORKING' if emb_success else '❌ FAILED'}")
    print("=" * 60)
    
    if gen_success and emb_success:
        print("\n🎉 All systems ready! You can now run the backend.")
    else:
        print("\n⚠️  Please fix the issues above before running the backend.")
        print("\nCommon fixes:")
        print("  1. Check your GOOGLE_API_KEY in .env file")
        print("  2. Make sure your API key is valid (get from https://makersuite.google.com/app/apikey)")
        print("  3. Ensure you have internet connection")
        print("  4. Check if you've exceeded API quota (free tier has limits)")