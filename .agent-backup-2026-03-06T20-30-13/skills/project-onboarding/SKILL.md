---
name: project-onboarding
description: Use when starting work on a new repository, or when the .agent/project.md file is missing. Establishes the foundational context before any code is written.
---

# Project Onboarding & Context

## Overview
Never assume project details. Code written without context is technical debt.
This skill establishes the `.agent/` documentation structure before any implementation begins.

## The Iron Law

NO CODE GENERATION UNTIL PROJECT CONTEXT IS DOCUMENTED

## The Process

### Step 1: Check Context Existence
Run `ls -la .agent/` or equivalent to check if `project.md`, `architecture.md`, and `integrations.md` exist.
- **If they exist:** Read them immediately to understand the stack and rules. Do not proceed to Step 2.
- **If they are missing:** Proceed to Step 2.

### Step 2: The Interview
Ask the human partner EXACTLY these questions, one by one or in a brief list:
1. What is the main goal of this project?
2. What is the tech stack (languages, frameworks, DBs)?
3. Are there critical external integrations (APIs, browsers, queues)?
4. Will this project process Personal Data (LGPD compliance needed)?

### Step 3: Scaffold the .agent/ Directory
Based on the answers, create the following files using the project's standard templates:

**Use the boilerplate templates as starting points:**
- Copy `.agent/boilerplate/architecture.md` → `.agent/architecture.md` and customize for the project
- Copy `.agent/boilerplate/conventions.md` → `.agent/conventions.md` and customize for the project

Then create the remaining files:
- `.agent/project.md`
- `.agent/integrations.md`
- `.agent/tasks.md`

### Step 4: Verification
Confirm to the user that the structure is created and ask if we can move to the `brainstorming` or `writing-plans` skills.