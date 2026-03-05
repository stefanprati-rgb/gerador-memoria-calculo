---
name: clean-architecture-enforcer
description: Validates if new features respect the separation of layers (Entities, Use Cases, Adapters) before implementation.
---

# Clean Architecture Enforcer

This skill ensures that all architectural changes and new features adhere to the **Clean Architecture** principles defined in the project context.

## Core Mandate

You MUST validate the layer separation BEFORE writing any implementation code.

## Verification Steps

1.  **Identify the Layer**: Determine which layer the new functionality belongs to.
2.  **Dependency Check**: Ensure that the code does NOT import from outer layers.
    - Entities should have NO dependencies on Use Cases, Adapters, or Infrastructure.
    - Use Cases should have NO dependencies on Adapters or Infrastructure.
    - Adapters should have NO dependencies on Infrastructure.
3.  **Interface usage**: Ensure that communication between layers happens through interfaces or simple data structures (DTOs).

## Enforcement Rules

- **Stop and Validate**: Before creating a new file or modifying an existing one, state which Clean Architecture layer it belongs to.
- **Reject Violations**: If a request would violate the dependency rule (e.g., an Entity importing a Database utility), you MUST point this out and suggest a refactoring (using Dependency Injection or Interfaces).
- **Clean Context**: Use the `architecture.md` file from the project context as the source of truth for specific layer definitions in this repository.

## Workflow Integration

This skill should be triggered during the `/brainstorm` and `/write-plan` phases to ensure the design is sound before execution.
