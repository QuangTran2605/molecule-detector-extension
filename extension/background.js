// background.js - Service worker for handling keyboard shortcuts

const BACKEND_URL = 'http://localhost:5000';

// Store selection coordinates temporarily
let currentSelection = null;

// Listen for keyboard shortcut (Alt+M)
chrome.commands.onCommand.addListener((command) => {
  if (command === 'capture-molecule') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, { action: 'startSelection' });
      }
    });
  }
});

// Listen for messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'captureWithBounds') {
    handleCaptureWithBounds(request.bounds, sender.tab.id);
    sendResponse({ success: true });
  }
  return true;
});

async function handleCaptureWithBounds(bounds, tabId) {
  try {
    // Capture the visible tab
    const dataUrl = await chrome.tabs.captureVisibleTab(null, {
      format: 'png'
    });
    
    // Crop the image based on bounds
    const croppedImage = await cropImage(dataUrl, bounds);
    
    // Send to backend for processing
    await processAndOpenDatabase(croppedImage);
    
  } catch (error) {
    console.error('Error capturing:', error);
  }
}

async function cropImage(dataUrl, bounds) {
  // Convert data URL to blob
  const response = await fetch(dataUrl);
  const blob = await response.blob();
  
  // Create image bitmap (works in service workers)
  const imageBitmap = await createImageBitmap(blob);
  
  // Account for device pixel ratio
  const dpr = bounds.dpr || 1;
  
  // Create canvas and crop
  const canvas = new OffscreenCanvas(bounds.width, bounds.height);
  const ctx = canvas.getContext('2d');
  
  ctx.drawImage(
    imageBitmap,
    bounds.left * dpr,
    bounds.top * dpr,
    bounds.width * dpr,
    bounds.height * dpr,
    0,
    0,
    bounds.width,
    bounds.height
  );
  
  // Convert to blob and then to data URL
  const croppedBlob = await canvas.convertToBlob({ type: 'image/png' });
  const reader = new FileReader();
  
  return new Promise((resolve) => {
    reader.onloadend = () => resolve(reader.result);
    reader.readAsDataURL(croppedBlob);
  });
}

async function processAndOpenDatabase(imageDataUrl) {
  try {
    // Convert to blob
    const response = await fetch(imageDataUrl);
    const blob = await response.blob();
    
    // Send to backend
    const formData = new FormData();
    formData.append('image', blob, 'molecule.png');
    
    const backendResponse = await fetch(`${BACKEND_URL}/analyze-molecule`, {
      method: 'POST',
      body: formData
    });
    
    if (!backendResponse.ok) {
      console.error('Backend error:', backendResponse.status);
      return;
    }
    
    const data = await backendResponse.json();
    
    if (data.smiles) {
      // Open PubChem search in new tab immediately
      openDatabaseSearch(data.smiles);
    } else if (data.error) {
      console.error('Recognition error:', data.error);
    }
    
  } catch (error) {
    console.error('Error processing screenshot:', error);
  }
}

function openDatabaseSearch(smiles) {
  // Open PubChem structure search
  const pubchemUrl = `https://pubchem.ncbi.nlm.nih.gov/#query=${encodeURIComponent(smiles)}`;
  
  chrome.tabs.create({
    url: pubchemUrl,
    active: true
  });
}
