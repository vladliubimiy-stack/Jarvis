# Jarvis voice assistant

A small Russian-language voice controller for the SmartBox MQTT topics. The current feature set is light and shutter commands, local Ollama intent parsing, speech-to-text, and spoken replies.

## Setup on Windows

1. Install Python and Ollama. In Ollama, download the model configured below (default: qwen2.5:3b).
2. Open PowerShell in this folder and create a virtual environment:
   powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
3. Copy .env.example to .env. Set the MQTT broker address, unique MQTT username/password, microphone index, and Ollama settings. Use 127.0.0.1 only when the broker runs on the same computer.
4. Configure the MQTT broker with a password file and topic ACL. Do not enable anonymous access for a broker that controls devices.
5. Download the model and start Jarvis:
   powershell
   ollama pull qwen2.5:3b
   .\start_jarvis.bat

The microphone index is machine-specific. List/test available microphones with the SpeechRecognition tools and adjust MICROPHONE_INDEX in your local .env.

## Speech and privacy

The language model runs through the local Ollama HTTP API. Speech recognition currently calls Google's recognition service, so audio processing requires internet access and is not fully local. Do not use this setup for sensitive audio until a local speech recognizer is configured.

## Command safety

The fast parser accepts only explicit commands that name a supported device and action. Negated, bare, conflicting, and status-only phrases are rejected. Other phrases go to the Ollama fallback, whose prompt also requires an explicit request. MQTT delivery confirmation means the broker accepted a message; the current firmware does not yet publish authoritative relay or shutter state.

## Checks

Run the dependency-free parser checks with:
   powershell
   python -m unittest discover -s tests
