# DevOps / Infrastructure Steering

## Context
Use this when working on: systemd services, Docker/Compose, Bash scripts, Ollama, LiteLLM, Langfuse, n8n, networking, VMs, ISO/USB.

## Key Services & Paths
- LiteLLM: `litellm/config.yaml`, `litellm/env`, service: `litellm.service`
- Voice Orchestrator: `voice-interface/orchestrator/`, service: `voice-orchestrator.service`
- RAG: `rag/knowledge_base.py`, data: `~/.local/share/ai-knowledge/`
- Docker stack: `langfuse/`, `n8n/` — managed via `docker compose`
- Ollama: system service, models at default Ollama path

## Rules (from Devin/best practice)
1. **Always check current state before changes**: `systemctl --user status <svc>`, `journalctl --user -u <svc> -n 30`
2. **Run validation after changes**: restart service, verify with `systemctl is-active`
3. **Include rollback steps** for destructive changes
4. **Never skip hooks** (`--no-verify`) unless user explicitly requests
5. **Environment issues**: report, then work around (use CI or manual testing); don't fix env issues autonomously

## Common Commands
```bash
# Service management
systemctl --user status <service>
journalctl --user -u <service> --no-pager -n 50
systemctl --user restart <service>

# Docker
docker compose -f langfuse/docker-compose.yml up -d
docker compose ps

# LiteLLM
curl http://localhost:4000/models | jq '.data[].id'
curl http://localhost:4000/health

# Ollama
ollama list
curl http://localhost:11434/api/tags | jq '.models[].name'
```
