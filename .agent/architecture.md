# Architecture Patterns

This project follows **Clean Architecture** principles to ensure maintainability, testability, and independence from external frameworks.

## Layers

1.  **Entities (Domain)**: Business objects (e.g., calculation logic in `logic/core`).
2.  **Use Cases (Logic/Services)**: Application-specific business rules (e.g., `logic/services`).
3.  **Interface Adapters**: Converters between Use Cases and external agencies (e.g., `logic/adapters`).
4.  **Frameworks & Drivers (Infrastructure)**: Tools like Streamlit (UI), Firestore SDK, and Excel files.

## Dependency Rule
Dependencies must only point **inwards**:
- `Services` (Use Cases) use `Adapters`.
- `Adapters` use `Infrastructure`.
- `Core` (Entities) has NO dependencies on outer layers.

## Implementation Notes
- **FirebaseAdapter**: Centralizes interaction with Google Cloud services.
- **Services**: Should utilize the `FirebaseAdapter` to persist and retrieve data, abstracting the underlying DB details when possible.
