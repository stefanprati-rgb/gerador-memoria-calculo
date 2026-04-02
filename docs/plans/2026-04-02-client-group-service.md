# Client Group Service Implementation Plan

> **For Antigravity:** REQUIRED WORKFLOW: Use `.agent/workflows/execute-plan.md` to execute this plan in single-flow mode.

**Goal:** Implement `logic/services/client_group_service.py` for saving and retrieving client groups in Firestore.

**Architecture:** A service in the Logic layer that depends on `FirebaseAdapter` for Firestore communication. Adheres to Clean Architecture and LGPD compliance.

**Tech Stack:** Python, Firestore (Firebase Admin SDK).

---

### Task 1: Create Client Group Service
**Files:**
- Create: `logic/services/client_group_service.py`
- Test: `tests/test_client_group_service.py`

**Step 1: Write the failing test for `save_client_group`**
Create a test that mocks `FirebaseAdapter` and verifies that `save_client_group` calls the Firestore client with the correct arguments (collection, document ID, and data).

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_client_group_service.py`

**Step 3: Implement `save_client_group`**
Define the `CLIENT_GROUPS_COLLECTION` constant and implement the function using lazy loading for the adapter. Ensure no sensitive data is logged.

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_client_group_service.py`

**Step 5: Implement `list_client_groups` and `get_clients_from_group` with tests**
Implement the remaining functions and their corresponding tests.

**Step 6: Final verification**
Run all tests and verify LGPD compliance.

**Step 7: Commit**
```bash
git add logic/services/client_group_service.py tests/test_client_group_service.py
git commit -m "feat(service): add client_group_service with Firestore persistence"
```
