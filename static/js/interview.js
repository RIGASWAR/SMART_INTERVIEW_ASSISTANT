/**
 * InterviewAI — interview.js
 * Manages the full interview session:
 *   - Setup → Start → Q&A loop → Finish → Redirect to Results
 */

// ── State ──────────────────────────────────────────────────────────────────────
let interviewId    = null;
let questions      = [];
let currentQIndex  = 0;
let jobRole        = "General";
let recognition    = null;   // SpeechRecognition instance
let isRecording    = false;
let timerHandle    = null;
let elapsedSeconds = 0;

// ── Start Interview ────────────────────────────────────────────────────────────

async function startInterview() {
  jobRole = document.getElementById("jobRole").value;
  const difficulty     = document.getElementById("difficulty").value;
  const questionCount  = document.getElementById("questionCount").value;

  const btn = document.querySelector('.btn-large');
  btn.textContent = "Starting…";
  btn.disabled = true;

  try {
    const res  = await fetch("/api/start_interview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_role: jobRole, difficulty, question_count: questionCount }),
    });
    const data = await res.json();

    if (!data.success) throw new Error(data.error || "Failed to start interview");

    interviewId = data.interview_id;
    questions   = data.questions;

    // Switch panels
    document.getElementById("setupPanel").classList.add("hidden");
    document.getElementById("activePanel").classList.remove("hidden");

    // Start webcam on active panel
    stopWebcam();  // stop preview webcam
    stopEmotionPolling();
    await startWebcam("webcamActive");
    startEmotionPolling("webcamActive", 3000);

    // Start global timer
    startTimer();

    // Show first question
    showQuestion(0);
  } catch (err) {
    alert("Error starting interview: " + err.message);
    btn.textContent = "Begin Interview";
    btn.disabled = false;
  }
}

// ── Display Question ───────────────────────────────────────────────────────────

function showQuestion(index) {
  if (index >= questions.length) {
    finishInterview();
    return;
  }

  currentQIndex = index;
  const q = questions[index];

  // Animate card swap
  const card = document.getElementById("questionCard");
  card.style.opacity = "0";
  card.style.transform = "translateY(10px)";

  setTimeout(() => {
    document.getElementById("questionNum").textContent  = `Question ${index + 1} of ${questions.length}`;
    document.getElementById("questionText").textContent = q;
    document.getElementById("progressFill").style.width = ((index / questions.length) * 100) + "%";
    document.getElementById("progressLabel").textContent = `Q${index + 1} / ${questions.length}`;
    document.getElementById("answerText").value = "";
    document.getElementById("liveFeedback").classList.add("hidden");

    card.style.transition = "all .3s ease";
    card.style.opacity    = "1";
    card.style.transform  = "translateY(0)";
  }, 200);

  // Update metric
  document.getElementById("metricDone").textContent = index;
}

// ── Submit Answer ──────────────────────────────────────────────────────────────

async function submitAnswer() {
  const answer = document.getElementById("answerText").value.trim();

  // Stop mic if running
  if (isRecording) toggleMic();

  const res  = await fetch("/api/submit_answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      interview_id: interviewId,
      question:     questions[currentQIndex],
      answer,
      emotion:      currentEmotion,
      confidence:   currentConfidence || Math.round(Math.random() * 30 + 60),
      job_role:     jobRole,
    }),
  });
  const data = await res.json();

  if (data.success) {
    // Show live feedback
    const fb = document.getElementById("liveFeedback");
    document.getElementById("feedbackScore").textContent = data.score + "%";
    document.getElementById("feedbackText").textContent  = data.feedback;
    fb.classList.remove("hidden");

    // Update last score metric
    document.getElementById("metricScore").textContent = data.score + "%";
    document.getElementById("metricDone").textContent  = currentQIndex + 1;

    // Brief pause then next question
    setTimeout(() => showQuestion(currentQIndex + 1), 1800);
  }
}

// ── End / Finish Interview ─────────────────────────────────────────────────────

function endInterview() {
  if (!confirm("Are you sure you want to end the interview early?")) return;
  finishInterview();
}

async function finishInterview() {
  const duration = stopTimer();
  stopEmotionPolling();
  stopWebcam();

  // Show loading overlay
  document.getElementById("finishOverlay").classList.remove("hidden");

  try {
    const res  = await fetch("/api/finish_interview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ interview_id: interviewId, duration_sec: duration }),
    });
    const data = await res.json();

    if (data.success) {
      window.location.href = `/results/${interviewId}`;
    } else {
      alert("Could not finalise interview: " + (data.error || "unknown error"));
      document.getElementById("finishOverlay").classList.add("hidden");
    }
  } catch (err) {
    alert("Network error: " + err.message);
    document.getElementById("finishOverlay").classList.add("hidden");
  }
}

// ── Speech Recognition ─────────────────────────────────────────────────────────

function toggleMic() {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    alert("Speech recognition is not supported in this browser. Please use Chrome or Edge.");
    return;
  }

  if (isRecording) {
    // Stop recording
    recognition.stop();
    isRecording = false;
    document.getElementById("micBtn").classList.remove("recording");
    document.getElementById("micBtnText").textContent = "Start Speaking";
    document.getElementById("recordingIndicator").classList.add("hidden");
    return;
  }

  // Start recording
  recognition = new SpeechRecognition();
  recognition.continuous    = true;
  recognition.interimResults = true;
  recognition.lang          = "en-US";
  recognition.maxAlternatives = 1;

  const textarea = document.getElementById("answerText");
  let finalTranscript = textarea.value;  // preserve existing text

  recognition.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const t = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += (finalTranscript ? " " : "") + t;
      } else {
        interim = t;
      }
    }
    textarea.value = finalTranscript + (interim ? " " + interim : "");
    // Auto-scroll textarea
    textarea.scrollTop = textarea.scrollHeight;
  };

  recognition.onerror = (event) => {
    console.warn("Speech recognition error:", event.error);
    if (event.error !== "no-speech") {
      isRecording = false;
      document.getElementById("micBtn").classList.remove("recording");
      document.getElementById("micBtnText").textContent = "Start Speaking";
      document.getElementById("recordingIndicator").classList.add("hidden");
    }
  };

  recognition.onend = () => {
    if (isRecording) {
      // Restart automatically if still in recording mode (handles Chrome's 60s limit)
      try { recognition.start(); } catch { /* already stopped */ }
    }
  };

  recognition.start();
  isRecording = true;
  document.getElementById("micBtn").classList.add("recording");
  document.getElementById("micBtnText").textContent = "Stop Speaking";
  document.getElementById("recordingIndicator").classList.remove("hidden");
}
