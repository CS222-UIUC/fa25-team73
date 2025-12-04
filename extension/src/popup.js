// LiveCheck Popup Script
function formatTimestamp(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

async function loadClaims() {
  const container = document.getElementById('claims-container');

  try {
    // Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab.url || !tab.url.includes('youtube.com/watch')) {
      container.innerHTML = '<div class="no-claims">Please open a YouTube video</div>';
      return;
    }

    // Extract video ID
    const url = new URL(tab.url);
    const videoId = url.searchParams.get('v');

    if (!videoId) {
      container.innerHTML = '<div class="no-claims">No video ID found</div>';
      return;
    }

    // Get data from storage
    const result = await chrome.storage.local.get(videoId);
    const videoData = result[videoId];

    // Check status
    if (!videoData) {
      container.innerHTML = '<div class="no-claims">Video not yet processed.<br>LiveCheck will start analyzing soon...</div>';
      return;
    }

    const status = videoData.status || 'unknown';
    const claims = videoData.claims || [];

    // Display status-specific messages
    if (status === 'processing') {
      const chunksTotal = videoData.chunksTotal || 0;
      const chunksProcessed = videoData.chunksProcessed || 0;

      // Show processing status at the top
      let message = 'Processing transcript...';
      if (chunksTotal > 0) {
        const percentage = Math.round((chunksProcessed / chunksTotal) * 100);
        message = `Processing: ${chunksProcessed}/${chunksTotal} segments (${percentage}%)`;
      }

      // If we have claims already, show them below the status
      if (claims.length > 0) {
        container.innerHTML = `<div class="processing-header">${message}</div>`;

        claims.forEach(claim => {
          const div = document.createElement('div');
          div.className = `claim verdict-${claim.verdict.toLowerCase()}`;
          div.innerHTML = `
            <div class="claim-header">${claim.verdict} (${Math.round(claim.confidence * 100)}%)</div>
            <div>${claim.claim}</div>
            <div class="timestamp">At ${formatTimestamp(claim.timestamp)}</div>
          `;
          container.appendChild(div);
        });
      } else {
        container.innerHTML = `<div class="no-claims status-processing">${message}<br>Analyzing...</div>`;
      }
      return;
    }

    if (status === 'no_transcript') {
      container.innerHTML = '<div class="no-claims status-error">No transcript available<br>This video doesn\'t have captions.</div>';
      return;
    }

    if (status === 'error') {
      container.innerHTML = '<div class="no-claims status-error">Error processing video<br>Check console for details.</div>';
      return;
    }

    if (status === 'complete' && claims.length === 0) {
      container.innerHTML = '<div class="no-claims status-success">Analysis complete<br>No factual claims found in this video.</div>';
      return;
    }

    if (claims.length === 0) {
      container.innerHTML = '<div class="no-claims">No claims found yet.</div>';
      return;
    }

    // Display claims
    container.innerHTML = '';

    // Show cached indicator if applicable
    if (videoData.cached) {
      const cachedMsg = document.createElement('div');
      cachedMsg.className = 'cached-indicator';
      cachedMsg.textContent = 'Cached results';
      container.appendChild(cachedMsg);
    }

    claims.forEach(claim => {
      const div = document.createElement('div');
      div.className = `claim verdict-${claim.verdict.toLowerCase()}`;
      div.innerHTML = `
        <div class="claim-header">${claim.verdict} (${Math.round(claim.confidence * 100)}%)</div>
        <div>${claim.claim}</div>
        <div class="timestamp">At ${formatTimestamp(claim.timestamp)}</div>
      `;
      container.appendChild(div);
    });

  } catch (error) {
    console.error('Error loading claims:', error);
    container.innerHTML = '<div class="no-claims">Error loading claims</div>';
  }
}

// Load claims when popup opens
document.addEventListener('DOMContentLoaded', () => {
  loadClaims();

  // Auto-refresh every 2 seconds to show progress
  setInterval(loadClaims, 2000);
});
