#!/usr/bin/env python3
"""
Whisper Voice Input MCP Server
Allows Claude Code to receive voice input via local Whisper speech recognition.
Uses OpenAI Whisper for privacy-focused, offline speech-to-text.
"""

import json
import os
import re
import sys
import tempfile
import wave
from pathlib import Path
from typing import Any, Optional

import speech_recognition as sr
import whisper
import numpy as np


# MCP Protocol helpers
def send_response(response: dict):
    """Send a JSON-RPC response to stdout."""
    output = json.dumps(response)
    sys.stdout.write(output + "\n")
    sys.stdout.flush()


def read_request() -> dict:
    """Read a JSON-RPC request from stdin."""
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line)


class WhisperVoiceMCPServer:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.whisper_models = {}  # Cache loaded models
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)

        # Set Whisper download directory
        os.environ["WHISPER_CACHE_DIR"] = str(self.models_dir)

    def initialize_microphone(self):
        """Initialize the microphone if not already done."""
        if self.microphone is None:
            self.microphone = sr.Microphone()
            # Adjust for ambient noise on first use
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

    def get_whisper_model(self, model_name: str = "base.en"):
        """
        Load and cache a Whisper model.

        Args:
            model_name: Model to load (tiny.en, base.en, small.en, medium.en)

        Returns:
            Loaded Whisper model
        """
        if model_name not in self.whisper_models:
            print(f"Loading Whisper model '{model_name}'...", file=sys.stderr)
            try:
                # Load model with specific download directory
                self.whisper_models[model_name] = whisper.load_model(
                    model_name,
                    download_root=str(self.models_dir)
                )
                print(f"Model '{model_name}' loaded successfully", file=sys.stderr)
            except Exception as e:
                print(f"Error loading model: {e}", file=sys.stderr)
                raise

        return self.whisper_models[model_name]

    def transcribe_audio_with_whisper(
        self,
        audio_data: sr.AudioData,
        model_name: str = "base.en"
    ) -> Optional[str]:
        """
        Transcribe audio using Whisper.

        Args:
            audio_data: Audio data from speech_recognition
            model_name: Whisper model to use

        Returns:
            Transcribed text or None if failed
        """
        try:
            # Get the Whisper model (cached)
            model = self.get_whisper_model(model_name)

            # Convert audio data to the format Whisper expects
            # AudioData is in 16-bit PCM format
            wav_bytes = audio_data.get_wav_data()

            # Write to temporary file (Whisper works best with files)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(wav_bytes)
                tmp_path = tmp_file.name

            try:
                # Transcribe with Whisper
                result = model.transcribe(
                    tmp_path,
                    language="en",
                    fp16=False  # Disable FP16 for CPU-only systems
                )

                return result["text"].strip()

            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except:
                    pass

        except Exception as e:
            print(f"Whisper transcription error: {e}", file=sys.stderr)
            return None

    def listen_for_voice(
        self,
        model: str = "base.en",
        timeout: int = 10,
        phrase_time_limit: int = 30,
        stop_phrase: str = "stop claude"
    ) -> dict:
        """
        Listen for voice input and return transcribed text using Whisper.
        Stops when the stop phrase is detected or silence is detected.

        Args:
            model: Whisper model to use (tiny.en, base.en, small.en, medium.en)
            timeout: Max seconds to wait for speech to start
            phrase_time_limit: Max seconds for each chunk
            stop_phrase: Phrase to stop listening (default: "stop claude")

        Returns:
            Dict with success status, transcribed text, and message
        """
        # Validate model name
        valid_models = ["tiny.en", "base.en", "small.en", "medium.en"]
        if model not in valid_models:
            return {
                "success": False,
                "text": "",
                "message": f"Invalid model '{model}'. Must be one of: {', '.join(valid_models)}"
            }

        try:
            self.initialize_microphone()

            accumulated_text = []
            chunk_duration = 4  # Listen in 4-second chunks
            max_chunks = 30  # Max ~2 minutes of listening

            print(f"Listening with Whisper model '{model}'... (say '{stop_phrase}' to finish)", file=sys.stderr)

            for chunk_num in range(max_chunks):
                try:
                    with self.microphone as source:
                        # For first chunk, use the provided timeout
                        # For subsequent chunks, use a shorter timeout
                        current_timeout = timeout if chunk_num == 0 else 3

                        audio = self.recognizer.listen(
                            source,
                            timeout=current_timeout,
                            phrase_time_limit=chunk_duration
                        )

                    # Transcribe this chunk with Whisper
                    chunk_text = self.transcribe_audio_with_whisper(audio, model)

                    if chunk_text:
                        print(f"   heard: {chunk_text}", file=sys.stderr)

                        # Check if stop phrase is in this chunk
                        if stop_phrase.lower() in chunk_text.lower():
                            # Remove stop phrase and add remaining text
                            cleaned = re.sub(
                                re.escape(stop_phrase),
                                '',
                                chunk_text,
                                flags=re.IGNORECASE
                            ).strip()
                            if cleaned:
                                accumulated_text.append(cleaned)
                            print("Stop phrase detected", file=sys.stderr)
                            break

                        accumulated_text.append(chunk_text)
                    else:
                        # Silence or unintelligible - continue listening
                        pass

                except sr.WaitTimeoutError:
                    # No speech in this chunk
                    if chunk_num == 0:
                        return {
                            "success": False,
                            "text": "",
                            "message": "No speech detected within timeout period"
                        }
                    # If we already have some text and hit silence, stop
                    if accumulated_text:
                        print("Silence detected, stopping", file=sys.stderr)
                        break

            full_text = " ".join(accumulated_text)

            if not full_text:
                return {
                    "success": False,
                    "text": "",
                    "message": "No speech was transcribed"
                }

            return {
                "success": True,
                "text": full_text,
                "message": f"Transcribed: {full_text}",
                "model": model
            }

        except Exception as e:
            return {
                "success": False,
                "text": "",
                "message": f"Error: {str(e)}"
            }

    def list_microphones(self) -> dict:
        """List available microphone devices."""
        try:
            mics = sr.Microphone.list_microphone_names()
            return {
                "success": True,
                "microphones": mics,
                "count": len(mics)
            }
        except Exception as e:
            return {
                "success": False,
                "microphones": [],
                "message": f"Error listing microphones: {e}"
            }

    def handle_request(self, request: dict) -> dict:
        """Handle incoming JSON-RPC requests."""
        method = request.get("method", "")
        request_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "whisper-voice-input",
                        "version": "1.0.0"
                    }
                }
            }

        elif method == "notifications/initialized":
            return None  # No response needed for notifications

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "listen",
                            "description": "Listen for voice input from the microphone and transcribe it to text using local Whisper model. Continues listening until user says 'stop claude' or silence is detected. Runs completely offline for privacy.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "model": {
                                        "type": "string",
                                        "enum": ["tiny.en", "base.en", "small.en", "medium.en"],
                                        "description": "Whisper model to use (default: base.en). Larger models are more accurate but slower.",
                                        "default": "base.en"
                                    },
                                    "timeout": {
                                        "type": "integer",
                                        "description": "Max seconds to wait for speech to start (default: 10)",
                                        "default": 10
                                    },
                                    "phrase_time_limit": {
                                        "type": "integer",
                                        "description": "Max seconds per listening chunk (default: 30)",
                                        "default": 30
                                    },
                                    "stop_phrase": {
                                        "type": "string",
                                        "description": "Phrase to stop listening (default: 'stop claude')",
                                        "default": "stop claude"
                                    }
                                },
                                "required": []
                            }
                        },
                        {
                            "name": "list_microphones",
                            "description": "List all available microphone devices on the system",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    ]
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})

            if tool_name == "listen":
                result = self.listen_for_voice(
                    model=tool_args.get("model", "base.en"),
                    timeout=tool_args.get("timeout", 10),
                    phrase_time_limit=tool_args.get("phrase_time_limit", 30),
                    stop_phrase=tool_args.get("stop_phrase", "stop claude")
                )
            elif tool_name == "list_microphones":
                result = self.list_microphones()
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }

    def run(self):
        """Main server loop."""
        while True:
            try:
                request = read_request()
                if request is None:
                    break

                response = self.handle_request(request)
                if response is not None:
                    send_response(response)

            except json.JSONDecodeError as e:
                send_response({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {e}"
                    }
                })
            except Exception as e:
                print(f"Server error: {e}", file=sys.stderr)


if __name__ == "__main__":
    server = WhisperVoiceMCPServer()
    server.run()
