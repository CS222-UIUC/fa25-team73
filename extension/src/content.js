// LiveCheck Content Script for YouTube
const API_BASE = 'http://localhost:8000';

// Extract video ID from URL
function getVideoId() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('v');
}

// Fetch transcript via backend (uses YouTube Data API v3)
async function fetchTranscript(videoId) {
  try {
    console.log('LiveCheck: Fetching transcript from backend for', videoId);

    // Call backend to get transcript
    // Backend handles YouTube API complexity
    const response = await fetch(`${API_BASE}/api/fetch-transcript/${videoId}`);

    if (!response.ok) {
      console.log('LiveCheck: Backend transcript fetch failed:', response.status);
      return null;
    }

    const data = await response.json();

    if (!data.transcript || data.transcript.length === 0) {
      console.log('LiveCheck: No transcript returned from backend');
      return null;
    }

    console.log(`LiveCheck: Success! Got ${data.transcript.length} transcript segments (via ${data.method})`);
    return data.transcript;

  } catch (error) {
    console.error('LiveCheck: Error fetching transcript:', error);
    return null;
  }
}

// Call backend API
async function verifyClaims(videoId, transcript) {
  try {
    const response = await fetch(`${API_BASE}/api/verify-transcript`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_id: videoId, transcript })
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error verifying claims:', error);
    return null;
  }
}

// Create overlay element
function createOverlay(claim) {
  const overlay = document.createElement('div');
  overlay.className = `livecheck-overlay verdict-${claim.verdict.toLowerCase()}`;
  overlay.innerHTML = `
    <div class="livecheck-claim">${claim.claim}</div>
    <div class="livecheck-verdict">${claim.verdict}</div>
    <div class="livecheck-confidence">${Math.round(claim.confidence * 100)}% confident</div>
  `;

  overlay.style.cssText = `
    position: fixed;
    bottom: 100px;
    right: 20px;
    max-width: 400px;
    padding: 16px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    z-index: 10000;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    animation: slideIn 0.3s ease-out;
  `;

  if (claim.verdict === 'True') {
    overlay.style.borderLeft = '4px solid #28a745';
  } else if (claim.verdict === 'False') {
    overlay.style.borderLeft = '4px solid #dc3545';
  } else if (claim.verdict === 'Mixed') {
    overlay.style.borderLeft = '4px solid #ffc107';
  } else {
    overlay.style.borderLeft = '4px solid #6c757d';
  }

  return overlay;
}

// Show overlay at the right time
function showOverlayAtTime(claim) {
  const video = document.querySelector('video');
  if (!video) return;

  let shown = false;

  const checkTime = () => {
    if (!shown && video.currentTime >= claim.timestamp &&
        video.currentTime < claim.timestamp + 5) {
      const overlay = createOverlay(claim);
      document.body.appendChild(overlay);
      shown = true;

      setTimeout(() => {
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 300);
        shown = false;
      }, 5000);
    }
  };

  video.addEventListener('timeupdate', checkTime);
}

// Split transcript into chunks by time
function chunkTranscript(transcript, chunkDurationSeconds = 300) {
  // 300 seconds = 5 minutes per chunk
  const chunks = [];
  let currentChunk = [];
  let chunkStartTime = 0;

  for (const segment of transcript) {
    // Start new chunk if we've exceeded duration
    if (segment.start >= chunkStartTime + chunkDurationSeconds && currentChunk.length > 0) {
      chunks.push(currentChunk);
      currentChunk = [];
      chunkStartTime = segment.start;
    }
    currentChunk.push(segment);
  }

  // Add final chunk
  if (currentChunk.length > 0) {
    chunks.push(currentChunk);
  }

  return chunks;
}

// Main processing function with chunked processing
async function processVideo() {
  const videoId = getVideoId();
  if (!videoId) return;

  console.log('LiveCheck: Processing video', videoId);

  // Check cache first
  const cached = await chrome.storage.local.get(videoId);
  if (cached[videoId] && cached[videoId].status === 'complete') {
    console.log('LiveCheck: Using cached claims');
    if (cached[videoId].claims) {
      cached[videoId].claims.forEach(showOverlayAtTime);
    }
    return;
  }

  // Set processing status
  await chrome.storage.local.set({
    [videoId]: {
      status: 'processing',
      claims: [],
      chunksTotal: 0,
      chunksProcessed: 0
    }
  });

  // Fetch transcript
  const transcript = await fetchTranscript(videoId);
  if (!transcript || transcript.length === 0) {
    console.log('LiveCheck: No transcript available');
    await chrome.storage.local.set({
      [videoId]: { status: 'no_transcript', claims: [] }
    });
    return;
  }

  console.log(`LiveCheck: Got transcript with ${transcript.length} segments`);

  // Split into chunks (5-minute segments)
  const chunks = chunkTranscript(transcript, 300);
  console.log(`LiveCheck: Split into ${chunks.length} chunks`);

  // Update status with chunk count
  await chrome.storage.local.set({
    [videoId]: {
      status: 'processing',
      claims: [],
      chunksTotal: chunks.length,
      chunksProcessed: 0
    }
  });

  // Process chunks in parallel
  const allClaims = [];
  const chunkPromises = chunks.map(async (chunk, index) => {
    console.log(`LiveCheck: Processing chunk ${index + 1}/${chunks.length}`);

    try {
      const result = await verifyClaims(`${videoId}_chunk_${index}`, chunk);

      if (result && result.claims) {
        // Add claims to the accumulated list
        allClaims.push(...result.claims);

        // Update storage with new claims immediately
        await chrome.storage.local.set({
          [videoId]: {
            status: 'processing',
            claims: allClaims,
            chunksTotal: chunks.length,
            chunksProcessed: index + 1
          }
        });

        // Display overlays for new claims immediately
        result.claims.forEach(showOverlayAtTime);

        console.log(`LiveCheck: Chunk ${index + 1} complete - found ${result.claims.length} claims`);
      }
    } catch (error) {
      console.error(`LiveCheck: Error processing chunk ${index + 1}:`, error);
    }
  });

  // Wait for all chunks to complete
  await Promise.all(chunkPromises);

  console.log(`LiveCheck: All chunks complete - total ${allClaims.length} claims`);

  // Mark as complete
  await chrome.storage.local.set({
    [videoId]: {
      status: 'complete',
      claims: allClaims,
      chunksTotal: chunks.length,
      chunksProcessed: chunks.length
    }
  });
}

// Watch for video changes
let lastVideoId = null;

function checkForNewVideo() {
  const videoId = getVideoId();
  if (videoId && videoId !== lastVideoId) {
    lastVideoId = videoId;
    setTimeout(processVideo, 2000); // Give video time to load
  }
}

// Initial check
checkForNewVideo();

// Watch for navigation
setInterval(checkForNewVideo, 1000);

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  .livecheck-overlay {
    transition: opacity 0.3s ease-out;
  }

  .livecheck-claim {
    font-weight: bold;
    margin-bottom: 8px;
    font-size: 14px;
  }

  .livecheck-verdict {
    font-size: 16px;
    font-weight: bold;
    margin-bottom: 4px;
  }

  .livecheck-confidence {
    font-size: 12px;
    color: #666;
  }
`;
document.head.appendChild(style);

console.log('LiveCheck: Content script loaded');
