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
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat
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


def _otsu_threshold(image):
    """
    Compute the optimal binary threshold using Otsu's method.
    Uses the image histogram to find the threshold that minimizes
    intra-class variance between foreground and background pixels.

    Args:
        image: PIL Image in 'L' (grayscale) mode

    Returns:
        Optimal threshold value (0-255)
    """
    histogram = image.histogram()
    total_pixels = image.size[0] * image.size[1]
    total_sum = sum(i * histogram[i] for i in range(256))

    best_threshold = 128
    best_variance = 0
    weight_bg = 0
    sum_bg = 0

    for t in range(256):
        weight_bg += histogram[t]
        if weight_bg == 0:
            continue
        weight_fg = total_pixels - weight_bg
        if weight_fg == 0:
            break

        sum_bg += t * histogram[t]
        mean_bg = sum_bg / weight_bg
        mean_fg = (total_sum - sum_bg) / weight_fg

        variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if variance > best_variance:
            best_variance = variance
            best_threshold = t

    return best_threshold


def preprocess_image(image):
    """
    Preprocess a browser-captured screenshot for optimal OSRA recognition.
    Handles transparency, colored backgrounds, anti-aliasing, low contrast,
    dark themes, and varying resolutions.

    Args:
        image: PIL Image object (from browser extension screenshot)

    Returns:
        Preprocessed PIL Image ready for OSRA
    """
    # Step 1: Flatten transparency onto white background
    # Browser screenshots may be RGBA PNGs; without this, transparent
    # regions become black and invert the image semantics.
    if image.mode == 'RGBA':
        background = Image.new('RGBA', image.size, (255, 255, 255, 255))
        background.paste(image, mask=image.split()[3])
        image = background.convert('RGB')
    elif image.mode == 'P':
        image = image.convert('RGBA')
        background = Image.new('RGBA', image.size, (255, 255, 255, 255))
        background.paste(image, mask=image.split()[3])
        image = background.convert('RGB')
    elif image.mode != 'RGB':
        image = image.convert('RGB')

    # Step 2: Convert to grayscale
    # OSRA only uses luminance; removing color prevents issues with
    # colored heteroatom labels (blue N, red O) being lost during
    # OSRA's internal conversion.
    image = image.convert('L')

    # Step 3: Inversion detection for dark-theme websites
    # If mean pixel value is dark, the image is likely white-on-dark
    # (dark theme). OSRA expects dark lines on light background.
    mean_val = ImageStat.Stat(image).mean[0]
    if mean_val < 128:
        image = ImageOps.invert(image)

    # Step 4: Remove grey background artifacts (watermarks, shading)
    # Watermarks and background artifacts appear as light-to-mid grey
    # pixels. Actual molecular structure lines are much darker. We
    # suppress anything lighter than a cutoff by pushing it to white,
    # preserving only the dark bond lines and atom labels.
    # Cutoff at ~60% grey (pixel value 160): anything lighter is background.
    image = image.point(lambda p: 255 if p > 160 else p, mode='L')

    # Step 5: Contrast enhancement
    # Web-rendered structures often have light gray lines on slightly
    # off-white backgrounds. Boosting contrast makes faint lines darker
    # and backgrounds whiter before thresholding.
    image = ImageEnhance.Contrast(image).enhance(1.5)

    # Step 6: Binary thresholding (Otsu's method)
    # Produces clean black/white output. Otsu's method adapts to the
    # actual intensity distribution, which varies across websites.
    threshold = _otsu_threshold(image)
    image = image.point(lambda p: 255 if p > threshold else 0, mode='L')

    # Step 7: Noise reduction
    # Median filter removes salt-and-pepper noise from anti-aliasing
    # remnants after thresholding. Size 3 is safe for thin bond lines.
    image = image.filter(ImageFilter.MedianFilter(size=3))

    # Step 8: Crop edge artifacts and add white padding
    # Browser selection captures may include partial UI elements at edges.
    # OSRA also needs whitespace margin around the structure for detection.
    w, h = image.size
    border_crop = 3
    if w > 2 * border_crop + 10 and h > 2 * border_crop + 10:
        image = image.crop((border_crop, border_crop, w - border_crop, h - border_crop))
    image = ImageOps.expand(image, border=15, fill=255)

    # Step 9: Resolution normalization
    # Too-small images lack detail for recognition; too-large images
    # slow processing without accuracy gains.
    w, h = image.size
    min_dim = min(w, h)
    max_dim = max(w, h)

    if min_dim < 400:
        scale = 400 / min_dim
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        w, h = image.size
        max_dim = max(w, h)

    if max_dim > 1500:
        scale = 1500 / max_dim
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

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
