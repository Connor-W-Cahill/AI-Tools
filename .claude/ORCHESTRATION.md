# Claude Code AI Orchestration

**IMPORTANT**: This codebase may have multiple AI tools working simultaneously.

## Required: Check Before Working

Before editing ANY file, run:
```bash
~/.ai-orchestrator/bin/aio status
```

If other AIs are active, coordinate by claiming files:
```bash
~/.ai-orchestrator/bin/aio register claude "$(pwd)"
~/.ai-orchestrator/bin/aio claim file <path>
```

## Quick Reference

```bash
aio status              # See active AIs and claims
aio register claude     # Register this session
aio claim file <path>   # Claim before editing
aio check <path>        # Check if available
aio release all         # Release when done
aio-context handoff "msg"  # Leave notes for other AIs
aio unregister          # Clean exit
```

## Full Protocol

See: `~/.ai-orchestrator/PLAYBOOK.md`
