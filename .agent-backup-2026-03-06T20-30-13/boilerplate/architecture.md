# Architecture Patterns

This project follows **Clean Architecture** principles to ensure maintainability, testability, and independence from external frameworks.

## Layers

1.  **Entities (Domain)**: Business objects and rules that are least likely to change when external things change.
2.  **Use Cases (Application)**: Application-specific business rules. Orchestrates the flow of data to and from entities.
3.  **Interface Adapters**: Converters between the format most convenient for the use cases and entities, to the format most convenient for external agencies like Databases or Web.
4.  **Frameworks & Drivers (Infrastructure)**: Tools like Databases, Web Frameworks, UI, etc.

## Dependency Rule
Dependencies must only point **inwards**. Nothing in an inner circle can know anything at all about something in an outer circle.
