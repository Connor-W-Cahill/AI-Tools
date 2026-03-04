# Spec-Driven Development Steering

## Context
Use when designing a new feature that's complex enough to need requirements + design before coding.
Based on Kiro's spec workflow.

## When to Use Spec Mode
- Feature touches 3+ files or components
- Requirements are ambiguous
- Multiple implementation approaches exist
- Work will span multiple sessions

## Spec Workflow
See full runbook: `hub/runbooks/spec-workflow.md`

### Phase 1: Requirements (EARS format)
Create `.specs/<feature-name>/requirements.md`:
- User stories: "As a [role], I want [feature], so that [benefit]"
- Acceptance criteria in EARS syntax:
  - `WHEN [event] THEN [system] SHALL [response]`
  - `IF [precondition] THEN [system] SHALL [response]`

### Phase 2: Design
Create `.specs/<feature-name>/design.md` with:
- Overview, Architecture, Components & Interfaces, Data Models, Error Handling, Testing Strategy

### Phase 3: Tasks
Create `.specs/<feature-name>/tasks.md`:
- Numbered checkbox list
- Each task = ~20 min coding work
- Reference requirements (e.g., _Requirements: 1.1, 2.3_)
- Test-driven where possible

## Rules
- **One phase at a time** — get explicit approval before moving to next phase
- **Only coding tasks** in the task list (no deployment, user testing, docs)
- **Each task builds on the previous** — no orphaned code
- **Stop after each task** — let user review before continuing
