// popup.js - Main extension logic

const captureBtn = document.getElementById('captureBtn');
const statusDiv = document.getElementById('status');
const resultsDiv = document.getElementById('results');
const previewContainer = document.getElementById('previewContainer');
const previewImg = document.getElementById('preview');

// Backend server URL - change this if running on different port
const BACKEND_URL = 'http://localhost:5000';

captureBtn.addEventListener('click', async () => {
  try {
    // Disable button during processing
    captureBtn.disabled = true;
    showStatus('Capturing screenshot...', 'info');
    
    // Get the active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    // Capture the visible tab
    const screenshotUrl = await chrome.tabs.captureVisibleTab(null, {
      format: 'png'
    });
    
    // Show preview
    previewImg.src = screenshotUrl;
    previewContainer.style.display = 'block';
    
    showStatus('Analyzing molecular structure...', 'info');
    
    // Convert data URL to blob
    const response = await fetch(screenshotUrl);
    const blob = await response.blob();
    
    // Send to backend for analysis
    const formData = new FormData();
    formData.append('image', blob, 'molecule.png');
    
    const backendResponse = await fetch(`${BACKEND_URL}/analyze-molecule`, {
      method: 'POST',
      body: formData
    });
    
    if (!backendResponse.ok) {
      throw new Error(`Backend error: ${backendResponse.status}`);
    }
    
    const data = await backendResponse.json();
    
    if (data.error) {
      showStatus(`Error: ${data.error}`, 'error');
    } else {
      showStatus('Molecule identified!', 'success');
      displayResults(data);
    }
    
  } catch (error) {
    console.error('Error:', error);
    showStatus(`Error: ${error.message}. Make sure the Python backend is running on ${BACKEND_URL}`, 'error');
  } finally {
    captureBtn.disabled = false;
  }
});

function showStatus(message, type) {
  statusDiv.textContent = message;
  statusDiv.style.display = 'block';
  statusDiv.style.backgroundColor = type === 'error' ? '#fce8e6' : 
                                     type === 'success' ? '#e6f4ea' : '#f1f3f4';
  statusDiv.style.color = type === 'error' ? '#c5221f' : 
                          type === 'success' ? '#137333' : '#5f6368';
}

function displayResults(data) {
  resultsDiv.style.display = 'block';
  
  const html = `
    <div class="molecule-info">
      <h2>${data.name || 'Unknown Compound'}</h2>
      ${data.iupac_name ? `<p><strong>IUPAC Name:</strong> ${data.iupac_name}</p>` : ''}
      ${data.molecular_formula ? `<p><strong>Formula:</strong> ${data.molecular_formula}</p>` : ''}
      ${data.molecular_weight ? `<p><strong>Molecular Weight:</strong> ${data.molecular_weight} g/mol</p>` : ''}
      ${data.inchi ? `<p><strong>InChI:</strong> <code style="font-size: 11px; word-break: break-all;">${data.inchi}</code></p>` : ''}
      ${data.smiles ? `<p><strong>SMILES:</strong> <code>${data.smiles}</code></p>` : ''}
      ${data.description ? `<p style="margin-top: 10px;"><strong>Description:</strong> ${data.description}</p>` : ''}
      
      ${data.pubchem_url ? `<p style="margin-top: 10px;"><a href="${data.pubchem_url}" target="_blank">View on PubChem →</a></p>` : ''}
    </div>
  `;
  
  resultsDiv.innerHTML = html;
}
