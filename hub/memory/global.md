# Global Memory

## Task Tracking
- Use `bd` (beads) for all task tracking — never markdown TODO files
- `bd ready` to find available work, `bd close <id>` to finish
- `bd sync` at end of every session

## Local AI Infrastructure
- **Ollama**: localhost:11434, models: qwen2.5:3b, nomic-embed-text. GPU: GTX 1050 Ti (4GB)
- **LiteLLM Proxy**: localhost:4000, unified API for claude-sonnet/haiku/opus, gpt-4o/mini, qwen2.5:3b
  - Config: `litellm/config.yaml`, env: `litellm/env`
  - Fallback chains: claude -> gpt-4o -> local qwen
- **Open WebUI**: localhost:3000, chat UI connected to Ollama
- **Langfuse**: localhost:3001, LLM observability (tracks all LiteLLM requests)
- **n8n**: localhost:5678, workflow automation

## RAG Knowledge Base
- Search project history: `python3 ~/AI-Tools/rag/knowledge_base.py search "<query>"`
- Stats: `python3 ~/AI-Tools/rag/knowledge_base.py stats`
- Reindex: `python3 ~/AI-Tools/rag/knowledge_base.py reindex`
- Indexed: beads tasks, aio-context, project docs (~150 chunks)

## Voice Orchestrator (Jarvis)
- Service: `voice-orchestrator.service` (systemd user unit)
- Wake word: "Hey Jarvis" or hotkey Super+Shift+V
- Brain: Codex CLI with local LLM routing (simple -> Ollama, complex -> Codex)
- Screen awareness: GPT-4o vision + tesseract OCR fallback

## Multi-AI Coordination
- Register before editing: `aio register <tool>`, `aio claim file <path>`
- Check conflicts: `aio status`
- Handoff notes: `aio-context handoff "summary"`

## Hub CLI
- `ai c` (Claude), `ai x` (Codex), `ai g` (Gemini), `ai a` (Amp), `ai o` (OpenCode), `ai q` (Qwen), `ai ad` (Aider)
