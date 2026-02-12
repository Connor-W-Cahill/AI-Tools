# AI Orchestration Instructions

## Before Starting Any Task

0. Refresh Hub context:
   ```bash
   /home/connor/AI-Tools/hub/scripts/generate-brief.sh
   ```

1. Register with orchestrator:
   ```bash
   source ~/.ai-orchestrator/integrations/<your-tool>-hook.sh
   ```
   Or manually: `aio register <tool> $(pwd)`

2. Check for existing work:
   ```bash
   aio status
   ```

3. Check beads for available tasks:
   ```bash
   bd ready
   ```

## Claiming Work

Before editing files, claim them to prevent conflicts:

```bash
# Claim a single file
aio claim file src/main.ts

# Claim a directory
aio claim directory src/components/

# Claim a beads issue
aio claim task AI-Tools-abc
```

## During Work

- Call `aio heartbeat` periodically (every few minutes)
- Update your current task: `aio task "working on X" "AI-Tools-abc"`
- Share important learnings: `aio-context learning "discovered X works better than Y"`

## Finishing Work

1. Release your claims:
   ```bash
   aio release all
   ```

2. If using beads, close your issues:
   ```bash
   bd close <issue-id>
   ```

3. Leave a handoff note:
   ```bash
   aio-context handoff "completed X, next steps are Y"
   ```

4. Unregister:
   ```bash
   aio unregister
   ```

## Conflict Resolution

If you encounter a claimed file:
1. Check who owns it: `aio check <path>`
2. Either wait, or coordinate via handoff notes
3. In emergencies, `aio cleanup` removes stale (5min+) claims
