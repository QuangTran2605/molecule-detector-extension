"""
Molecule Detection Backend Server - Production Version
This Flask server receives images from the browser extension,
uses OSRA for real molecule recognition, and returns SMILES strings.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import tempfile
import os
from PIL import Image
from io import BytesIO

app = Flask(__name__)
CORS(app)  # Enable CORS for browser extension

def recognize_molecule_with_osra(image_path):
    """
    Use OSRA (Optical Structure Recognition Application) to recognize
    molecular structures from images.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        SMILES string or None if recognition failed
    """
    try:
        # Run OSRA command
        # Options:
        # -f smi: output SMILES format
        # -p: disable perception of functional groups (faster)
        result = subprocess.run(
            ['osra', '-f', 'smi', image_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            smiles = result.stdout.strip()
            if smiles:
                # OSRA outputs format: "SMILES name"
                # Extract just the SMILES part
                smiles_parts = smiles.split()
                if smiles_parts:
                    return smiles_parts[0]
        
        print(f"OSRA stderr: {result.stderr}")
        return None
        
    except subprocess.TimeoutExpired:
        print("OSRA timeout")
        return None
    except FileNotFoundError:
        print("OSRA not found. Please install: sudo apt-get install osra")
        return None
    except Exception as e:
        print(f"OSRA error: {e}")
        return None


def preprocess_image(image):
    """
    Preprocess image for better OSRA recognition.
    For ChemDraw images, minimal processing is needed.
    
    Args:
        image: PIL Image object
        
    Returns:
        Preprocessed PIL Image
    """
    # Convert to RGB if necessary
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # For ChemDraw structures, we can use the image as-is
    # If needed, we could add:
    # - Grayscale conversion
    # - Contrast enhancement
    # - Noise reduction
    
    return image


@app.route('/analyze-molecule', methods=['POST'])
def analyze_molecule():
    """
    Main endpoint that receives an image and returns SMILES string.
    """
    try:
        # Check if image was uploaded
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        image_file = request.files['image']
        
        # Open and preprocess image
        image = Image.open(image_file)
        image = preprocess_image(image)
        
        # Save to temporary file for OSRA
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_path = temp_file.name
            image.save(temp_path, 'PNG')
        
        try:
            # Run OSRA recognition
            print(f"Running OSRA on {temp_path}...")
            smiles = recognize_molecule_with_osra(temp_path)
            
            if smiles:
                print(f"Recognized SMILES: {smiles}")
                return jsonify({
                    'success': True,
                    'smiles': smiles
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Could not recognize molecular structure. Make sure the image contains a clear chemical structure diagram.'
                }), 200
                
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint - also checks if OSRA is available"""
    osra_available = False
    try:
        result = subprocess.run(['osra', '--version'], capture_output=True, timeout=5)
        osra_available = result.returncode == 0
    except:
        pass
    
    return jsonify({
        'status': 'ok',
        'message': 'Molecule detector backend is running',
        'osra_available': osra_available
    }), 200


if __name__ == '__main__':
    print("=" * 70)
    print("🧪 Molecule Detection Backend Server - Production Version")
    print("=" * 70)
    print("Server starting on http://localhost:5000")
    print()
    print("Requirements:")
    print("  - OSRA installed: sudo apt-get install osra")
    print("  - Python packages: pip install flask flask-cors pillow")
    print()
    print("Endpoints:")
    print("  POST /analyze-molecule - Analyze molecule from image (returns SMILES)")
    print("  GET  /health          - Health check (includes OSRA status)")
    print("=" * 70)
    print()
    
    # Check OSRA availability
    try:
        result = subprocess.run(['osra', '--version'], capture_output=True, timeout=5)
        if result.returncode == 0:
            print("✓ OSRA is installed and ready")
        else:
            print("✗ OSRA check failed")
    except FileNotFoundError:
        print("✗ WARNING: OSRA not found!")
        print("  Install with: sudo apt-get install osra")
    except Exception as e:
        print(f"✗ Error checking OSRA: {e}")
    
    print()
    app.run(debug=True, port=5000, host='0.0.0.0')
