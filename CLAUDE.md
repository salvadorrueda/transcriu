# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Live speech-to-text dictation in Catalan (`ca-ES`) for an old, low-resource computer with an Internet connection. A single CLI script (`transcriu.py`) captures microphone audio locally and sends each phrase to the free Google Web Speech API (no API key) via the `SpeechRecognition` library. All heavy processing happens in the cloud.

## Commands

```bash
# System dependencies (Debian/Ubuntu)
sudo apt install portaudio19-dev flac xclip

# Setup (venv required: Debian's system Python is externally managed)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run (the script re-execs itself into .venv automatically)
./transcriu.py              # live dictation, Catalan by default
./transcriu.py --mics       # list microphone devices
./transcriu.py -o notes.txt # also append output to a file
```

There are no tests or linters configured.

## Architecture and constraints

- Everything lives in `transcriu.py`: venv re-exec bootstrap (so `./transcriu.py` works without activating the venv) → argparse CLI → ambient-noise calibration → listen loop (`recognizer.listen` splits on pauses) → `recognize_google(language=...)` → print, copy whole session to clipboard (pyperclip; disabled with a single warning if no clipboard backend), append to `-o` file. Errors inside the loop (`UnknownValueError`, `RequestError`) are reported and skipped so a bad fragment never kills a dictation session.
- **The key constraint is minimal local resource usage.** Do not add local ML models (Whisper etc.), heavy dependencies, or background services — recognition must stay in the cloud and the local footprint tiny.
- User-facing strings (CLI help, messages, README) are in Catalan.
