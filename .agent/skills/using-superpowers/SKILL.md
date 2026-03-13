---
name: using-superpowers
description: Use when starting any conversation - establishes how to find and use skills, requiring skill loading via view_file before ANY response including clarifying questions
---

Only load a skill when the task clearly and directly matches its described use case. Do not load skills speculatively.


## How to Access Skills

**In Antigravity:** Use `view_file` to load a skill from `.agent/skills/<skill-name>/SKILL.md` (or `~/.gemini/skills/<skill-name>/SKILL.md` when needed). When you load a skill, follow it directly.

**In other environments:** Check your platform's documentation for how skills are loaded.

# Using Skills

## The Rule

**Invoke relevant or requested skills BEFORE any response or action.** Even a 1% chance a skill might apply means that you should invoke the skill to check. If an invoked skill turns out to be wrong for the situation, you don't need to use it.

## Automatic Memory Initialization (REQUIRED)
If you see `.agent/memory.md` in the project root, you **MUST** initialize the context session before invoking any other skills:
1. Try to read today's log at `.agent/sessions/<YYYY-MM-DD>.md`.
2. **If missing (New Day):** Read yesterday's log and `.agent/memory.md`, then create today's log summarizing where you left off.
3. **If present (Resume/Crash Recovery):** Read today's log and `.agent/memory.md`, then append `[INFO] Context Restored` to today's log.
4. **Post-Action Log Hook:** Whenever you complete an action, you must append it to the active session log. Before writing to the log, you MUST ensure no PII is included (replace with `[REDACTED_LGPD]`).

```dot
digraph skill_flow {
    "User message received" [shape=doublecircle];
    "About to EnterPlanMode?" [shape=doublecircle];
    "Already brainstormed?" [shape=diamond];
    "Invoke brainstorming skill" [shape=box];
    "Might any skill apply?" [shape=diamond];
    "Load skill via view_file" [shape=box];
    "Announce: 'Using [skill] to [purpose]'" [shape=box];
    "Has checklist?" [shape=diamond];
    "Update project-root docs/plans/task.md per checklist item" [shape=box];
    "Follow skill exactly" [shape=box];
    "Respond (including clarifications)" [shape=doublecircle];

    "About to EnterPlanMode?" -> "Already brainstormed?";
    "Already brainstormed?" -> "Invoke brainstorming skill" [label="no"];
    "Already brainstormed?" -> "Might any skill apply?" [label="yes"];
    "Invoke brainstorming skill" -> "Might any skill apply?";

    "User message received" -> "Might any skill apply?";
    "Might any skill apply?" -> "Load skill via view_file" [label="yes, even 1%"];
    "Might any skill apply?" -> "Respond (including clarifications)" [label="definitely not"];
    "Load skill via view_file" -> "Announce: 'Using [skill] to [purpose]'";
    "Announce: 'Using [skill] to [purpose]'" -> "Has checklist?";
    "Has checklist?" -> "Update project-root docs/plans/task.md per checklist item" [label="yes"];
    "Has checklist?" -> "Follow skill exactly" [label="no"];
    "Update project-root docs/plans/task.md per checklist item" -> "Follow skill exactly";
}
```

If the tracker file is missing, create `<project-root>/docs/plans/task.md` as a table-only task list.

## Red Flags

These thoughts mean STOP—you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |

## Skill Priority

When multiple skills could apply, use this order:

1. **Process skills first** (brainstorming, debugging) - these determine HOW to approach the task
2. **Implementation skills second** (frontend-design, mcp-builder) - these guide execution

"Let's build X" → brainstorming first, then implementation skills.
"Fix this bug" → debugging first, then domain-specific skills.

## Skill Types

**Rigid** (TDD, debugging): Follow exactly. Don't adapt away discipline.

**Flexible** (patterns): Adapt principles to context.

The skill itself tells you which.

## User Instructions

Instructions say WHAT, not HOW. "Add X" or "Fix Y" doesn't mean skip workflows.
