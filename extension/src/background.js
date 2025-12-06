// src/background.js

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "FETCH_TRANSCRIPT") {
    const videoId = msg.videoId;
    const url = `http://localhost:8000/api/fetch-transcript/${videoId}`;

    (async () => {
      try {
        const res = await fetch(url);
        if (!res.ok) {
          const text = await res.text();
          sendResponse({ ok: false, error: `HTTP ${res.status}: ${text}` });
          return;
        }
        const data = await res.json();
        sendResponse({ ok: true, data });
      } catch (err) {
        sendResponse({ ok: false, error: String(err) });
      }
    })();

    // Let Chrome know we'll respond asynchronously
    return true;
  }
});
