# 🧪 Molecule Structure Detector

A browser extension for Microsoft Edge that captures molecular structures from images and identifies them using OSRA (Optical Structure Recognition Application).

## Features

- ⌨️ Keyboard shortcut (Alt+M) for quick capture
- 🎯 Drag-to-select region for precise cropping
- 🔬 Real-time molecule recognition using OSRA
- ⚡ Automatic PubChem search in new tab
- 📊 Optimized for ChemDraw and clean diagrams

## Installation

### Requirements
- Microsoft Edge browser
- WSL2 (for Windows users)
- Python 3.8+
- OSRA

### Backend Setup

1. Install OSRA:
```bash
sudo apt-get update
sudo apt-get install osra
```

2. Install Python dependencies:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Start the server:
```bash
python server.py
```

### Extension Setup

1. Open Edge → `edge://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `extension` folder

## Usage

1. Start the backend server
2. Navigate to any chemistry website
3. Press `Alt+M` to activate capture mode
4. Drag to select the molecular structure
5. New tab opens with PubChem search results

## Tech Stack

- **Backend**: Python, Flask, OSRA
- **Frontend**: JavaScript, Chrome Extensions API
- **Recognition**: OSRA (Optical Structure Recognition Application)

## License

MIT License
