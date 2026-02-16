"""
Test script for the molecule detection backend.
This creates a dummy image and tests the API endpoint.
"""

import requests
from PIL import Image
from io import BytesIO

def test_backend():
    """Test the backend API"""
    
    print("🧪 Testing Molecule Detection Backend")
    print("=" * 50)
    
    # Check if server is running
    try:
        health_response = requests.get('http://localhost:5000/health', timeout=5)
        print("✓ Server is running")
        print(f"  Status: {health_response.json()}")
    except requests.exceptions.ConnectionError:
        print("✗ Error: Server is not running!")
        print("  Please start the server with: python server.py")
        return
    
    print()
    
    # Create a dummy image (white rectangle)
    print("Creating test image...")
    img = Image.new('RGB', (400, 300), color='white')
    
    # Save to bytes
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    # Test the analyze endpoint
    print("Sending image to /analyze-molecule endpoint...")
    
    files = {'image': ('test.png', img_bytes, 'image/png')}
    response = requests.post('http://localhost:5000/analyze-molecule', files=files)
    
    if response.status_code == 200:
        print("✓ Request successful!\n")
        data = response.json()
        
        print("Results:")
        print("=" * 50)
        print(f"Molecule Name: {data.get('name', 'N/A')}")
        print(f"Formula: {data.get('molecular_formula', 'N/A')}")
        print(f"Weight: {data.get('molecular_weight', 'N/A')} g/mol")
        print(f"SMILES: {data.get('smiles', 'N/A')}")
        print(f"PubChem: {data.get('pubchem_url', 'N/A')}")
        
        if data.get('description'):
            print(f"\nDescription: {data['description'][:100]}...")
        
        print("\n✓ Backend is working correctly!")
        print("\nYou can now use the browser extension to capture")
        print("molecular structures from web pages.")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  {response.text}")

if __name__ == '__main__':
    test_backend()
