# External Integrations

## Google Cloud / Firebase
- **Firestore**: Used for document persistence (profiles, mappings, client groups).
- **Cloud Storage**: Used for backing up uploaded spreadsheets (Balanço and Gestão).
- **Authentication**: Managed via Admin secrets/env (no external auth providers for end-users currently).

## File Systems
- **Excel (.xlsx/.xlsm)**: Primary input and output format.
- **Local Data**: Legacy JSON files in `data/mappings` are supported for migration/fallback.

## Configuration
- **Streamlit Secrets**: Source of truth for Firebase credentials and app settings in production.
- **Environment Variables**: Used for local development fallback.
