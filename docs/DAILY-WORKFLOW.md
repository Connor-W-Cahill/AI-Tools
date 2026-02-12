# Daily Workflow — AI-Tools Infrastructure

## Morning Startup (2 minutes)

```bash
# 1. Check service health
systemctl --user status voice-orchestrator litellm | grep Active

# 2. Verify local AI stack
curl -s localhost:11434/api/tags | grep qwen  # Ollama
curl -s localhost:4000/health                  # LiteLLM

# 3. Review today's work
bd ready                    # Available tasks
ai b                        # Regenerate daily brief
cat ~/AI-Tools/hub/context/current.md

# 4. Check who else is working (if multi-AI session)
aio status
```

**If services are down:**
```bash
systemctl --user restart voice-orchestrator
systemctl --user restart litellm
```

## Choosing the Right AI Tool

### Decision Tree

**Quick focused edits to existing code?**
→ `ad-local` (FREE) or `ad-cheap` ($0.25/MTok)

**Complex multi-file refactoring, architecture decisions?**
→ `ai c` (Claude Code, ~$3/MTok but worth it)

**Shell automation, system tasks, needs direct execution?**
→ `ai x` (Codex, fast and autonomous)

**Research, reading large docs, exploring unfamiliar topics?**
→ `ai g` (Gemini, huge context, free tier)

**Quick terminal questions, simple scripts?**
→ `ai q` (Qwen local, FREE)

**Hands-free while coding/reading?**
→ "Hey Jarvis" or `Super+Shift+V` (voice orchestrator)

### Cost Optimization Rules

1. **Start cheap, escalate as needed**
   - Try `ad-local` (free) first for simple edits
   - Upgrade to `ad-cheap` if local struggles
   - Use `ad-smart` for complex logic
   - Reserve `ad-max` (opus) for critical decisions only

2. **Use voice for free tier routing**
   - "Hey Jarvis, what's the weather?" → Ollama (free)
   - "Hey Jarvis, refactor auth module" → Codex (paid, but necessary)

3. **Batch similar tasks**
   - Don't spawn separate AI sessions for related edits
   - Use one Aider session for multiple file changes

4. **Monitor spend**
   - Check Langfuse (localhost:3001) weekly
   - Review token usage patterns
   - Adjust model choices if costs spike

## Common Workflows

### Starting a Task

```bash
# 1. Find work
bd ready                    # or: ai r

# 2. Claim it
bd update 42 --status=in_progress   # or: ai t 42

# 3. Review context
bd show 42                  # Read full description
python3 ~/AI-Tools/rag/knowledge_base.py search "related keywords"

# 4. Launch appropriate AI
ai c                        # Claude for complex work
# or
ad-cheap                    # Aider for focused edits

# 5. Work...

# 6. Complete
bd close 42 --reason="implemented X, tested Y"   # or: ai d 42
```

### Creating New Tasks

```bash
# Quick syntax
ai n implement user auth    # Creates task from words

# Detailed
bd new --title="Fix login timeout" --description="Users report..."
```

### Multi-AI Coordination

When working alongside other AIs (or planning to switch):

```bash
# Before starting
aio status                  # Check active sessions

# Register yourself (auto via `ai` launcher, but manual if needed)
aio register claude

# Before editing files
aio claim file /path/to/important.py

# After done
aio release all             # Auto on exit, but good habit
aio-context handoff "completed auth refactor, tests pass"
```

**Rule:** Never edit files claimed by other AIs. Check `aio status` first.

### Voice Orchestrator Usage

**Wake word mode:**
```
You: "Hey Jarvis"
Jarvis: [chime]
You: "What's running in tmux?"
Jarvis: "You have three sessions: main, dev, and monitor"
You: "Tell the dev window to run tests"
Jarvis: "Running tests in dev window"
You: "End conversation"
```

**Hotkey mode:**
Press `Super+Shift+V`, speak immediately (no wake word needed).

**Screen awareness:**
```
You: "Hey Jarvis, what's in the terminal window?"
Jarvis: [reads visible text via OCR or GPT-4o vision]

You: "Click the submit button"
Jarvis: [uses xdotool to click]
```

**Conversation tips:**
- Stays open until you say "end conversation" / "goodbye" / "Jarvis end"
- Rolling 10-turn memory
- Simple questions → Ollama (instant, free)
- Complex reasoning → Codex (slower, paid)

### RAG Knowledge Search

Before asking AIs about project context:

```bash
# Search indexed knowledge
python3 ~/AI-Tools/rag/knowledge_base.py search "authentication flow"
python3 ~/AI-Tools/rag/knowledge_base.py search "database schema"

# Check stats
python3 ~/AI-Tools/rag/knowledge_base.py stats

# Reindex after major changes
python3 ~/AI-Tools/rag/knowledge_base.py reindex
```

RAG auto-injects context into voice orchestrator and can be manually referenced in other sessions.

### Quick Reference Lookups

**Using local Qwen (free, instant):**
```bash
ai q
> "What's the bash syntax for read timeout?"
> "Explain Python asyncio.gather"
```

**Using Open WebUI (http://localhost:3000):**
- Chat interface for Ollama models
- Keeps conversation history
- Good for exploratory research

**Using Gemini (free tier, huge context):**
```bash
ai g
> "Read this 50-page API doc and explain the auth flow"
```

## Daily Patterns

### Morning: Planning & Context

```bash
ai b                        # Refresh daily brief
bd ready                    # See available tasks
ai g                        # Use Gemini to review docs/plan
```

### Midday: Execution

```bash
ad-cheap                    # Focused implementation
# or
ai c                        # Complex refactoring
```

### Afternoon: Testing & Cleanup

```bash
ai x                        # Codex for shell automation, test scripts
bd sync                     # Sync tasks to git
```

### Evening: Review & Handoff

```bash
bd stats                    # Check project health
aio-context handoff "completed X, blocked on Y, tomorrow: Z"
bd sync --flush-only        # Final sync
```

### Weekly: Maintenance

```bash
# Monday: Cost review
open http://localhost:3001  # Langfuse dashboard

# Wednesday: RAG refresh
python3 ~/AI-Tools/rag/knowledge_base.py reindex

# Friday: Service health
journalctl --user -u voice-orchestrator -n 50
journalctl --user -u litellm -n 50
```

## End of Day Shutdown

```bash
# 1. Complete active tasks
bd close <id> --reason="..."

# 2. Sync beads
bd sync --flush-only

# 3. Release claims
aio release all

# 4. Handoff context (if multi-AI workflow)
aio-context handoff "summary of day's work"

# 5. Optional: stop services to free resources
systemctl --user stop voice-orchestrator  # If not using overnight
# Keep LiteLLM running — minimal overhead
```

## Troubleshooting

### Voice orchestrator not responding

```bash
# Check status
systemctl --user status voice-orchestrator

# View logs
journalctl --user -u voice-orchestrator -n 50

# Restart
systemctl --user restart voice-orchestrator

# Test wake word manually
python3 ~/AI-Tools/voice-interface/orchestrator/wake_word.py
```

### LiteLLM proxy errors

```bash
# Check logs
journalctl --user -u litellm -n 50

# Test endpoints
curl localhost:4000/health
curl localhost:4000/model/info

# Restart
systemctl --user restart litellm
```

### Ollama slow or unresponsive

```bash
# Check process
ps aux | grep ollama

# Test directly
curl localhost:11434/api/tags

# Restart
systemctl restart ollama  # System-wide service
```

### Aider can't reach LiteLLM

```bash
# Verify proxy is running
curl localhost:4000/health

# Test model availability
curl localhost:4000/v1/models

# Check config
cat ~/AI-Tools/litellm/config.yaml
cat ~/AI-Tools/litellm/env
```

### RAG search returns nothing

```bash
# Check ChromaDB
ls -lh ~/.local/share/ai-knowledge/

# Reindex
python3 ~/AI-Tools/rag/knowledge_base.py reindex

# Verify stats
python3 ~/AI-Tools/rag/knowledge_base.py stats
```

## Pro Tips

1. **Default to free tier first**
   - Voice questions → often handled by Ollama
   - Simple edits → `ad-local` before `ad-cheap`
   - Research → Gemini free tier generous

2. **Batch AI sessions**
   - Launch one Aider session for multiple related edits
   - Use Claude Code for entire feature vs. multiple tools

3. **Let RAG do the work**
   - Search knowledge base before asking AIs to "remember" things
   - AIs inject RAG context automatically when relevant

4. **Voice for flow state**
   - Keep hands on keyboard
   - "Hey Jarvis, run tests" vs. switching to terminal
   - "Hey Jarvis, what's that error mean?" vs. copying to browser

5. **Monitor don't micromanage**
   - Check Langfuse weekly, not daily
   - Trust the fallback chains in LiteLLM config
   - Let voice orchestrator route simple/complex automatically

6. **Task hygiene**
   - Close tasks same day when possible
   - `bd sync` at least daily
   - Keep task descriptions actionable

7. **Hub context as single source of truth**
   - Update `hub/context/current.md` when priorities shift
   - All AIs read it on launch
   - Better than re-explaining context to each tool

## Quick Reference Card

```bash
# Task management
ai r              # ready: find work
ai t ID           # take: claim task
ai d ID           # done: complete task
ai n words        # new: create task

# AI tools
ai c              # Claude Code (complex)
ai x              # Codex (shell/auto)
ai g              # Gemini (research)
ai ad             # Aider (default)
ad-local          # Aider + Qwen (FREE)
ad-cheap          # Aider + Haiku ($)
ad-smart          # Aider + Sonnet ($$)
ad-max            # Aider + Opus ($$$)

# Multi-AI
aio status        # Check active sessions
aio claim file X  # Claim before editing

# Voice
Hey Jarvis        # Wake word
Super+Shift+V     # Hotkey trigger

# Knowledge
python3 ~/AI-Tools/rag/knowledge_base.py search "query"

# Monitoring
localhost:3000    # Open WebUI (chat)
localhost:3001    # Langfuse (metrics)
localhost:5678    # n8n (automation)
```

## Philosophy

**The goal is to work smarter, not harder:**
- Free local models for 80% of tasks
- Paid APIs only when necessary
- Voice for hands-free flow
- RAG for persistent memory
- Beads for never losing track

**If you find yourself:**
- Typing the same explanation to multiple AIs → update hub context
- Paying for simple tasks → use free tier first
- Forgetting what you worked on → improve task hygiene
- Repeating searches → index in RAG

**The system works best when:**
- Services run in background (minimal overhead)
- You choose the right tool for each job
- Tasks stay up-to-date
- Knowledge base stays current

## Metrics That Matter

Track these weekly (Langfuse dashboard):

- **Token cost per completed task** — optimize if rising
- **Free vs. paid request ratio** — aim for 70%+ free
- **Average task completion time** — detect blockers
- **Voice orchestrator routing accuracy** — tune thresholds if misrouting

Don't track everything. Track what changes behavior.
