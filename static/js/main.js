/**
 * InterviewAI — main.js
 * Shared utilities: webcam init, emotion polling, helpers
 */

// ── Webcam ─────────────────────────────────────────────────────────────────────

let webcamStream = null;

/**
 * Request webcam access and pipe stream into a <video> element.
 * @param {string} videoId - id of the target <video> element
 * @returns {Promise<MediaStream|null>}
 */
async function startWebcam(videoId = "webcamPreview") {
  const video = document.getElementById(videoId);
  const offDiv = document.getElementById("webcamOff");

  if (!navigator.mediaDevices?.getUserMedia) {
    console.warn("Webcam API not supported in this browser.");
    return null;
  }

  try {
    webcamStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: 640, height: 480 },
      audio: false,
    });
    if (video) {
      video.srcObject = webcamStream;
      video.style.display = "block";
    }
    if (offDiv) offDiv.style.display = "none";
    return webcamStream;
  } catch (err) {
    console.warn("Webcam access denied or unavailable:", err.message);
    return null;
  }
}

function stopWebcam() {
  if (webcamStream) {
    webcamStream.getTracks().forEach(t => t.stop());
    webcamStream = null;
  }
}

/**
 * Capture one frame from a <video> element as a base64 JPEG string.
 * @param {HTMLVideoElement} video
 * @returns {string} base64 data URL
 */
function captureFrame(video) {
  const canvas = document.createElement("canvas");
  canvas.width  = video.videoWidth  || 320;
  canvas.height = video.videoHeight || 240;
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.6);
}

// ── Emotion Polling ────────────────────────────────────────────────────────────

const EMOTION_EMOJIS = {
  confident:    "😎",
  nervous:      "😬",
  calm:         "😌",
  engaged:      "🤓",
  thoughtful:   "🤔",
  focused:      "🎯",
  uncertain:    "😕",
  enthusiastic: "🤩",
};

let emotionPollInterval = null;
let currentEmotion    = "neutral";
let currentConfidence = 0;

/**
 * Start polling the /api/emotion_update endpoint every `ms` milliseconds.
 * Updates all emotion display elements on the page.
 */
function startEmotionPolling(videoId = "webcamActive", ms = 3000) {
  const video = document.getElementById(videoId);

  emotionPollInterval = setInterval(async () => {
    let frameData = null;
    if (video && video.readyState >= 2) {
      try { frameData = captureFrame(video); } catch { /* ignore */ }
    }

    try {
      const res  = await fetch("/api/emotion_update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ frame: frameData }),
      });
      const data = await res.json();
      currentEmotion    = data.emotion;
      currentConfidence = data.confidence;
      updateEmotionUI(data.emotion, data.confidence);
    } catch {
      /* network error — keep last known state */
    }
  }, ms);
}

function stopEmotionPolling() {
  if (emotionPollInterval) {
    clearInterval(emotionPollInterval);
    emotionPollInterval = null;
  }
}

function updateEmotionUI(emotion, confidence) {
  const emoji = EMOTION_EMOJIS[emotion] || "😐";

  // Dashboard setup page live indicator
  const emotionText = document.getElementById("emotionText");
  if (emotionText) emotionText.textContent = `${emoji} ${capitalise(emotion)}`;

  // Active interview emotion badge
  const badge = document.getElementById("emotionBadge");
  if (badge) badge.textContent = `${emoji} ${capitalise(emotion)}`;

  // Metric cards
  const metricEmotion = document.getElementById("metricEmotion");
  if (metricEmotion) metricEmotion.textContent = capitalise(emotion);

  const metricConfidence = document.getElementById("metricConfidence");
  if (metricConfidence) metricConfidence.textContent = confidence + "%";
}

// ── Timer ──────────────────────────────────────────────────────────────────────

let timerSeconds = 0;
let timerInterval = null;

function startTimer() {
  timerSeconds  = 0;
  timerInterval = setInterval(() => {
    timerSeconds++;
    const m = String(Math.floor(timerSeconds / 60)).padStart(2, "0");
    const s = String(timerSeconds % 60).padStart(2, "0");
    const el = document.getElementById("timerDisplay");
    if (el) el.textContent = `${m}:${s}`;
  }, 1000);
}

function stopTimer() {
  clearInterval(timerInterval);
  return timerSeconds;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function capitalise(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// Auto-start webcam on setup page
document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("webcamPreview")) {
    startWebcam("webcamPreview").then(stream => {
      if (stream) startEmotionPolling("webcamPreview", 4000);
    });
  }
});
