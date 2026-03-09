# Coding and Git Conventions

## Programming Languages
- **Python**: Follow PEP 8. Use type hints. Prefer `pytest` for testing.
- **JavaScript/TypeScript**: Use ESM. Use Prettier/ESLint.

## Git Commits
We follow **Conventional Commits**:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools and libraries such as documentation generation

Example: `feat(api): add lgpd compliance validation`
