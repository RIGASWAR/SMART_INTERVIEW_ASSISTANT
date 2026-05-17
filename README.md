# 🤖 AI-Powered Smart Interview Assistant

A production-ready, full-stack web application for AI-driven mock interview preparation.
Built with Python Flask, SQLite, and a sleek dark UI.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 Auth | Secure signup / login with hashed passwords |
| 🎤 Speech-to-Text | Browser-native speech recognition — no API key needed |
| 🤖 AI Questions | Role-based, difficulty-adjusted question bank |
| 📷 Emotion Detection | Webcam-based live emotion & confidence feedback |
| 📄 Resume Upload | Upload PDF/TXT résumé; skills auto-detected |
| 📊 AI Scoring | Multi-factor answer scoring (keywords, structure, length) |
| 📈 Dashboard | Score trends, history table, analytics charts |
| 🌙 Dark UI | Premium dark theme with gradient accents |
| 🗄️ SQLite | Zero-config local database — no server needed |

---

## 📁 Folder Structure

```
smart_interview_assistant/
├── app.py                  ← Flask backend (all routes + logic)
├── requirements.txt
├── README.md
├── instance/
│   └── interview.db        ← SQLite DB (auto-created on first run)
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── main.js         ← Webcam, emotion polling, shared utils
│   │   └── interview.js    ← Interview session state machine
│   └── uploads/            ← Uploaded résumés (auto-created)
└── templates/
    ├── base.html
    ├── login.html
    ├── signup.html
    ├── dashboard.html
    ├── interview.html
    └── results.html
```

---

## 🚀 Quick Start (3 steps)

### 1. Install Python 3.9+
Make sure Python 3.9 or newer is installed:
```bash
python --version
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
python app.py
```

Open your browser at **http://127.0.0.1:5000**

---

## 🎯 Usage Guide

1. **Sign up** — create a free account (no email verification needed)
2. **Upload résumé** (optional) — drag & drop a PDF or TXT file on the Dashboard
3. **New Interview** — choose your role, difficulty, and number of questions
4. **Allow camera** — for live emotion & confidence tracking
5. **Answer questions** — type your answers or click **Start Speaking** to use voice
6. **See results** — get a detailed breakdown with scores per question
7. **Track progress** — revisit the Dashboard to see your score trend

---

## 🛠️ Troubleshooting

### `ModuleNotFoundError: No module named 'flask'`
```bash
pip install -r requirements.txt
# or, if using pip3:
pip3 install -r requirements.txt
```

### Port 5000 already in use
```bash
# macOS: disable AirPlay Receiver in System Settings → General → AirDrop & Handoff
# or run on a different port:
python app.py --port 5001
# (edit the port in app.py line at the bottom)
```

### Camera not working
- Make sure you are on **http://localhost:5000** (not a remote URL) — browsers only grant camera access on localhost or HTTPS
- Click **Allow** when the browser asks for camera permission
- Use **Chrome** or **Edge** for best speech-to-text support

### Speech-to-text not working
- Speech recognition requires **Chrome** or **Edge**
- Make sure your microphone is connected and allowed in browser settings
- The text area is always editable — you can type your answer directly

### Database errors
Delete `instance/interview.db` and restart the app — the DB will be recreated automatically.

---

## 🔧 Configuration

Edit the top of `app.py` to customise:

| Setting | Default | Description |
|---|---|---|
| `SECRET_KEY` | `"interview-assistant-secret-2024"` | Session secret (change in production) |
| `UPLOAD_FOLDER` | `static/uploads` | Résumé storage path |
| `MAX_CONTENT_LENGTH` | 5 MB | Max upload size |
| Port | 5000 | Change in `app.run(port=5000)` |

---

## 🏗️ Architecture

```
Browser
  ├── HTML/CSS/JS (templates/ + static/)
  │     ├── Webcam API  → captures frames for emotion
  │     └── Web Speech API → speech-to-text transcription
  │
  └── HTTP ↔ Flask (app.py)
              ├── /api/start_interview  → generates questions
              ├── /api/submit_answer   → scores + stores answer
              ├── /api/finish_interview→ computes final metrics
              ├── /api/emotion_update  → returns simulated emotion
              └── SQLite (instance/interview.db)
```

---

## 📜 License

MIT — free for personal and commercial use.
