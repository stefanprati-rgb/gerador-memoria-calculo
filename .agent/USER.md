# Developer Guide: Agent Memory & Privacy

This project is enabled with the **Antigravity Persistent Memory System**.

## How It Works
The AI agent maintains its context across separate conversations or crashes using two mechanisms:
1. **Active Memory (`.agent/memory.md`):** A small file tracking the current phase, blockers, and next steps.
2. **Session Logs (`.agent/sessions/YYYY-MM-DD.md`):** Append-only daily logs of actions taken by the agent.

The agent automatically reads these files at the start of a session (via the `using-superpowers` skill) to re-establish context without needing you to repeatedly explain the current state of the project.

## Privacy & LGPD Compliance
Session logs could theoretically capture sensitive data (PII) if the agent handles user data. To comply with LGPD:
- The agent runs a **Post-Action LGPD Hook** before writing to the session logs.
- Any detected PII (emails, CPFs, phones, passwords) is replaced with `[REDACTED_LGPD]`.

### Retention Policy
Logs are not kept forever. The active retention policy is defined in `.agent/memory.md` (default is `log_retention_days: 30`).

To automatically delete old session logs and enforce the "Right to be Forgotten", run:
```bash
npx antigravity-lgpd purge-sessions
```
This command checks the retention policy and purges older logs.
