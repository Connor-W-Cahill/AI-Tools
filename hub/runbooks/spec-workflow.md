# Spec-Driven Development Runbook

Adapted from Kiro's spec workflow. Use for complex features that need structured design before coding.

## When to Use This

- Feature is non-trivial (>3 files, multiple systems)
- Requirements are unclear or could go multiple ways
- Work will span multiple AI sessions
- You want a paper trail for the design decisions

## Directory Structure

```
.specs/
  <feature-name>/
    requirements.md   # Phase 1: EARS-format requirements
    design.md         # Phase 2: Architecture and design
    tasks.md          # Phase 3: Coding task checklist
```

Create with: `mkdir -p .specs/<feature-name>/`

---

## Phase 1: Requirements

**Prompt to use:**
> "Help me write requirements for [feature]. Create `.specs/<feature-name>/requirements.md` following EARS format."

**Template:** `hub/templates/spec/requirements.md`

**Rules:**
- Generate initial requirements immediately (don't ask 10 questions first)
- User stories: "As a [role], I want [feature], so that [benefit]"
- Acceptance criteria in EARS syntax
- Consider edge cases, UX, technical constraints
- Iterate until user explicitly approves
- **Do NOT proceed to Phase 2 without approval**

---

## Phase 2: Design

**Prompt to use:**
> "Requirements are approved. Create `.specs/<feature-name>/design.md` with the full design."

**Template:** `hub/templates/spec/design.md`

**Required sections:**
1. Overview
2. Architecture
3. Components and Interfaces
4. Data Models
5. Error Handling
6. Testing Strategy

**Rules:**
- Research before designing (check git log, existing code patterns)
- Use Mermaid diagrams where helpful
- Reference requirements by number
- Iterate until user explicitly approves
- **Do NOT proceed to Phase 3 without approval**

---

## Phase 3: Tasks

**Prompt to use:**
> "Design is approved. Create `.specs/<feature-name>/tasks.md` with the implementation task list."

**Template:** `hub/templates/spec/tasks.md`

**Rules:**
- Numbered checkbox list (1, 1.1, 1.2, 2, 2.1...)
- Each task = ~20 min of coding work
- Reference requirements (e.g., `_Requirements: 1.1, 2.3_`)
- Test-driven where possible
- **Only coding tasks** — no deployment, user testing, performance gathering
- Each task builds on previous (no orphaned code)
- Iterate until user explicitly approves

---

## Phase 4: Execution

**For each task:**
1. Read requirements.md, design.md, tasks.md before starting
2. Mark task in-progress: `bd update <id> --status=in_progress`
3. Implement ONE task at a time
4. Verify against requirements referenced in task
5. Stop and let user review before moving to next task

**Prompt to use:**
> "Execute task [N] from `.specs/<feature-name>/tasks.md`"

---

## Beads Integration

Create a beads epic for the feature:
```bash
bd create --title="Implement <feature-name>" --type=feature --priority=2
# Then create sub-tasks for each spec task
bd create --title="[spec] Requirements for <feature>" --type=task
bd create --title="[spec] Design for <feature>" --type=task
bd create --title="[spec] Implement <feature> task 1" --type=task
```
