# Multi-AI Orchestration Playbook

A system for coordinating Claude, Codex, Gemini CLI, and Amp across projects.

## Quick Start

```bash
# Add to your shell profile
export PATH="$HOME/.ai-orchestrator/bin:$PATH"

# Initialize any project
cd /your/project
aio-init

# Check orchestrator status
aio status
```

## Core Concepts

### 1. Instances
Each AI CLI tool session is an "instance" with:
- Unique ID (e.g., `claude-1707084123-a3f2`)
- Tool type (claude, codex, gemini, amp)
- Current project
- Active claims
- Heartbeat (instances without heartbeat for 5min become "stale")

### 2. Claims
Before editing files, AI tools "claim" them:
- **File claims**: Single file exclusive access
- **Directory claims**: Entire directory tree
- **Task claims**: Beads issue ownership
- **Pattern claims**: Glob patterns (e.g., `*.test.ts`)

### 3. Context
Shared knowledge between AI tools:
- **Decisions**: Architectural choices made
- **Patterns**: Useful code patterns discovered
- **Warnings**: Pitfalls to avoid
- **Learnings**: General insights
- **Handoffs**: Notes for the next AI session

---

## Use Cases

### Case 1: Related Tasks (Same Project)

**Scenario**: Multiple AIs working on the same codebase

```
Terminal 1 (Claude):
  aio register claude
  aio claim directory src/auth/
  aio task "Refactoring auth module" "AI-Tools-abc"
  # Works on src/auth/*

Terminal 2 (Codex):
  aio register codex
  aio claim directory src/api/
  aio task "Adding new API endpoints"
  # Works on src/api/*

Terminal 3 (Gemini):
  aio register gemini
  aio claim file README.md
  aio task "Updating documentation"
  # Works on docs
```

**Key Rule**: Partition by directory or file type to avoid conflicts.

### Case 2: Unrelated Tasks (Different Projects)

**Scenario**: AIs working on completely separate projects

```
Terminal 1 (Claude in ~/project-a):
  aio register claude ~/project-a
  # Full access to project-a

Terminal 2 (Codex in ~/project-b):
  aio register codex ~/project-b
  # Full access to project-b
```

No coordination needed - different projects don't conflict.

### Case 3: Pipeline Processing

**Scenario**: Sequential work where one AI's output feeds another

```
1. Claude generates code:
   aio register claude
   aio claim file src/feature.ts
   aio-context handoff "Implemented feature X, needs tests"
   aio release all
   aio unregister

2. Codex writes tests:
   aio register codex
   aio context get handoff  # See what Claude did
   aio claim file src/feature.test.ts
   # Write tests based on Claude's work
```

### Case 4: Review & Improve

**Scenario**: One AI reviews another's work

```
1. Codex writes initial code:
   aio claim file src/component.tsx
   # Writes code
   aio-context handoff "Initial implementation done, may need optimization"
   aio release all

2. Claude reviews:
   aio claim file src/component.tsx
   aio context get  # See history
   # Reviews and improves
   aio-context decision "Changed state management to useReducer for complexity"
```

---

## Workflow Patterns

### Pattern A: Hub & Spoke
One AI (usually Claude) coordinates, others execute.

```
Claude (Hub):
  - Creates beads issues with `bd create`
  - Assigns work areas to other AIs
  - Reviews and integrates

Codex/Gemini/Amp (Spokes):
  - Check `bd ready` for assigned work
  - Claim their work area
  - Execute and report via handoff
```

### Pattern B: Domain Ownership
Each AI owns a domain permanently.

```
Claude:     Business logic, complex refactoring
Codex:      New feature implementation, algorithms
Gemini:     Documentation, research, explanations
Amp:        Code search, navigation, codebase Q&A
```

### Pattern C: Parallel Sprint
All AIs work simultaneously on independent tasks.

```
# Create issues in parallel
bd create --title="Auth module" --type=task
bd create --title="API endpoints" --type=task
bd create --title="UI components" --type=task
bd create --title="Documentation" --type=task

# Each AI picks one
Claude:  bd update AI-Tools-1 --status=in_progress
Codex:   bd update AI-Tools-2 --status=in_progress
Gemini:  bd update AI-Tools-3 --status=in_progress
Amp:     bd update AI-Tools-4 --status=in_progress
```

---

## Commands Reference

### Instance Management
```bash
aio register <tool> [project]  # Register instance
aio heartbeat                  # Keep alive (every few min)
aio unregister                 # Clean exit
aio cleanup                    # Remove stale instances
aio status                     # View all instances
```

### Claiming Resources
```bash
aio claim file <path>          # Claim single file
aio claim directory <path>     # Claim directory tree
aio claim task <beads-id>      # Claim beads issue
aio check <path>               # Check if available
aio release <claim-id>         # Release specific claim
aio release all                # Release all your claims
```

### Context Sharing
```bash
aio-context decision <msg>     # Log decision
aio-context learning <msg>     # Share learning
aio-context warning <msg>      # Warn about pitfall
aio-context pattern <msg>      # Document pattern
aio-context handoff <msg>      # Leave handoff note
aio-context get [category]     # View context
aio-context export [project]   # Export to markdown
```

### Beads Integration
```bash
bd ready                       # See available issues
bd update <id> --status=in_progress  # Claim issue
bd close <id>                  # Complete issue
bd sync --flush-only           # Export state
```

---

## Best Practices

### DO
- Register immediately when starting
- Claim before editing
- Heartbeat regularly
- Leave handoff notes
- Release claims when done
- Use beads for task tracking

### DON'T
- Edit unclaimed files in shared projects
- Leave sessions running without heartbeat
- Forget to unregister
- Claim more than needed
- Work on same files as another AI

### Conflict Resolution
1. Check `aio status` to see who has claims
2. Wait for stale timeout (5min) if instance seems dead
3. Run `aio cleanup` to remove stale claims
4. Coordinate via handoff notes
5. In emergencies, manually edit state.json

---

## Integration Setup

### Claude Code
Add to `~/.claude/CLAUDE.md` or project's CLAUDE.md:
```markdown
## AI Orchestration

Before editing files, check for claims:
- Run `aio status` to see active instances
- Run `aio check <path>` before editing files
- Claim your work: `aio claim file <path>`
- Release when done: `aio release all`
```

### Codex
Add to instructions:
```
Source the integration hook at start:
source ~/.ai-orchestrator/integrations/codex-hook.sh
```

### Gemini CLI
Add to system instructions:
```
Check ~/.ai-orchestrator/bin/aio status before modifying files.
Claim files with: aio claim file <path>
```

### Amp
Add to configuration:
```
Use aio commands to coordinate with other AI tools.
```

---

## Troubleshooting

### "Already claimed" error
```bash
aio check <path>        # See who owns it
aio status              # See all instances
aio cleanup             # Remove stale (if applicable)
```

### Stale instances
```bash
aio cleanup             # Auto-removes 5min+ stale
```

### Lost claims after crash
```bash
aio register <tool>     # Re-register
aio claim <type> <target>  # Re-claim
```

### State corruption
```bash
# Reset state (loses all context)
echo '{"schemaVersion":1,"instances":{},"claims":{},"context":[]}' > ~/.ai-orchestrator/state.json
```
