// content.js - Handles screenshot region selection

let isSelecting = false;
let startX, startY;
let overlay = null;
let selectionBox = null;
let instruction = null;

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'startSelection') {
    startSelection();
  }
});

function startSelection() {
  if (isSelecting) return;
  isSelecting = true;
  
  // Create full-screen overlay
  overlay = document.createElement('div');
  overlay.style.cssText = `
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    background: rgba(0, 0, 0, 0.3) !important;
    z-index: 2147483647 !important;
    cursor: crosshair !important;
  `;
  
  // Create selection box
  selectionBox = document.createElement('div');
  selectionBox.style.cssText = `
    position: fixed !important;
    border: 2px dashed #1a73e8 !important;
    background: rgba(26, 115, 232, 0.1) !important;
    z-index: 2147483647 !important;
    display: none !important;
    pointer-events: none !important;
  `;
  
  // Create instruction text
  instruction = document.createElement('div');
  instruction.style.cssText = `
    position: fixed !important;
    top: 20px !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    background: #1a73e8 !important;
    color: white !important;
    padding: 12px 24px !important;
    border-radius: 4px !important;
    font-family: Arial, sans-serif !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    z-index: 2147483647 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
    pointer-events: none !important;
  `;
  instruction.textContent = 'Drag to select molecule structure • Press ESC to cancel';
  
  document.body.appendChild(overlay);
  document.body.appendChild(selectionBox);
  document.body.appendChild(instruction);
  
  // Event listeners
  overlay.addEventListener('mousedown', handleMouseDown);
  overlay.addEventListener('mousemove', handleMouseMove);
  overlay.addEventListener('mouseup', handleMouseUp);
  document.addEventListener('keydown', handleEscape);
}

function handleMouseDown(e) {
  e.preventDefault();
  startX = e.clientX;
  startY = e.clientY;
  selectionBox.style.display = 'block';
  updateSelectionBox(e.clientX, e.clientY);
}

function handleMouseMove(e) {
  if (startX === undefined) return;
  e.preventDefault();
  updateSelectionBox(e.clientX, e.clientY);
}

function updateSelectionBox(currentX, currentY) {
  const left = Math.min(startX, currentX);
  const top = Math.min(startY, currentY);
  const width = Math.abs(currentX - startX);
  const height = Math.abs(currentY - startY);
  
  selectionBox.style.left = left + 'px';
  selectionBox.style.top = top + 'px';
  selectionBox.style.width = width + 'px';
  selectionBox.style.height = height + 'px';
}

function handleMouseUp(e) {
  e.preventDefault();
  
  const endX = e.clientX;
  const endY = e.clientY;
  
  const left = Math.min(startX, endX);
  const top = Math.min(startY, endY);
  const width = Math.abs(endX - startX);
  const height = Math.abs(endY - startY);
  
  // Minimum size check
  if (width < 20 || height < 20) {
    cleanup();
    return;
  }
  
  // Update instruction
  instruction.textContent = '🔬 Processing molecule...';
  instruction.style.background = '#ea8600';
  
  // Capture after brief delay
  setTimeout(() => {
    captureSelection(left, top, width, height);
  }, 100);
}

function captureSelection(left, top, width, height) {
  // Send bounds to background script for capture
  chrome.runtime.sendMessage({
    action: 'captureWithBounds',
    bounds: {
      left: left,
      top: top,
      width: width,
      height: height,
      dpr: window.devicePixelRatio
    }
  }, (response) => {
    cleanup();
  });
}

function handleEscape(e) {
  if (e.key === 'Escape') {
    cleanup();
  }
}

function cleanup() {
  isSelecting = false;
  startX = startY = undefined;
  
  if (overlay) {
    overlay.remove();
    overlay = null;
  }
  if (selectionBox) {
    selectionBox.remove();
    selectionBox = null;
  }
  if (instruction) {
    instruction.remove();
    instruction = null;
  }
  
  document.removeEventListener('keydown', handleEscape);
}
