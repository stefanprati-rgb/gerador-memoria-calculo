---
name: handling-personal-data
description: Use whenever handling, routing, storing, or logging user data (CPF, email, phone, passwords, addresses, health data). Triggers strict LGPD compliance protocols.
---

# Handling Personal Data (LGPD Guardrail)

## Overview
Handling personal data requires absolute paranoia. A single bad log line violates compliance.
**Core principle:** Never log, expose, or mock real personal data.

## The Iron Law

NEVER EXPOSE PERSONAL DATA IN LOGS, EXCEPTIONS, OR DEV ENVIRONMENTS.

## Mandatory Verification Checklist

Before committing ANY code that touches user data, you MUST verify:

- [ ] **Data Minimization:** Are we collecting ONLY what is absolutely necessary?
- [ ] **No Leakage in Logs:** Check all `logger.info`, `logger.error`, and `print` statements. Replace real identifiers with pseudonymized hashes or UUIDs.
- [ ] **Safe Exceptions:** Ensure `raise Exception(...)` does NOT include user emails, CPFs, or tokens in the string.
- [ ] **Environment Check:** Does the dev/staging environment use ONLY synthetic/fake data? (Never use production data locally).

## Handling Deletion (Direito ao Esquecimento)
If implementing a deletion feature, NEVER use a simple `DELETE` without an audit log. You must overwrite personal fields (e.g., `user.cpf = None`) and record the deletion action with an operator ID.