# Python Development Steering

## Context
Use when writing Python scripts, services, or libraries in this project.

## Environment
- System Python: 3.8 (for rag/, voice-interface/, scripts/)
- LiteLLM venv: `litellm/.venv/` (Python 3.12 via uv) — activate with `. litellm/.venv/bin/activate`
- RAG requires pysqlite3-binary monkey-patch (already in knowledge_base.py)

## Key Libraries Available
- `anthropic` — Claude API (check `agents/` for usage patterns)
- `openai` — via LiteLLM proxy at localhost:4000
- `chromadb` — RAG storage (requires pysqlite3 patch on Python 3.8)
- `edge-tts`, `openai-whisper` — voice interface
- `openwakeword` — wake word detection

## Rules (from Devin/Augment best practice)
1. **Check git log before similar changes**: `git log --oneline -20 -- <path>` to see how it was done before
2. **Always use package managers**: `pip install`, `uv add` — don't manually edit requirements.txt
3. **Run existing tests** before submitting: `python -m pytest` or equivalent
4. **No inline comments** unless logic is genuinely non-obvious
5. **Fix root cause**, not symptoms — don't patch around broken tests

## Testing (TDD required)
```bash
python -m pytest --cov=. --cov-report=term-missing
```
- Write failing test FIRST (RED), then minimal implementation (GREEN), then refactor
- 80%+ coverage required for new code
- Mock external deps (requests, Ollama, LiteLLM) in unit tests
- Never modify tests to pass — fix the code

## Patterns
- Use LiteLLM proxy for AI calls (no hardcoded API keys in scripts)
- Base URL: `http://localhost:4000/v1`, any model in litellm/config.yaml
- For local-only work: use Ollama directly at `http://localhost:11434`
- Immutability: return new dicts/lists, don't mutate arguments
