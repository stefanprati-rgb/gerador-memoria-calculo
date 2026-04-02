# UI Client Group Integration Plan

> **For Antigravity:** REQUIRED WORKFLOW: Use `.agent/workflows/execute-plan.md` to execute this plan in single-flow mode.

**Goal:** Integrate client group selection and saving in Step 1 of the Wizard UI.

**Architecture:** UI Layer enhancement. Modifies `ui/groups_wizard_ui.py` to add selection shortcuts and saving capabilities using the and `logic.services.client_group_service`.

**Tech Stack:** Python, Streamlit.

---

### Task 1: Integrate Client Groups in Wizard UI
**Files:**
- Modify: `ui/groups_wizard_ui.py`
- Backup: `ui/groups_wizard_ui.py.bak_groups`

**Step 1: Create Backup**
Run: `cp ui/groups_wizard_ui.py ui/groups_wizard_ui.py.bak_groups`

**Step 2: Add Imports**
Add the following imports to `ui/groups_wizard_ui.py`:
- `from logic.services.client_group_service import save_client_group, list_client_groups, get_clients_from_group`
- `from ui.utils.notifications import notify_completion`

**Step 3: Implement "Atalhos de Seleção (Grupos Salvos)"**
In `_render_step_1_clients`, before the basket area:
- Fetch groups using `list_client_groups()`.
- Add a `st.selectbox` "Atalhos de Seleção (Grupos Salvos)".
- If a group (not "Nenhum") is selected:
  - Fetch clients via `get_clients_from_group(name)`.
  - Update state via `select_clients(group.id, new_clients)`.
  - Trigger `st.rerun()`.

**Step 4: Implement "Salvar Seleção" Expander**
In `_render_step_1_clients`, after the search area:
- Add `st.expander("💾 Salvar esta seleção como um novo grupo")`.
- Inside: `st.text_input("Nome do grupo")` and `st.button("Confirmar e Salvar")`.
- On click:
  - Call `save_client_group(name, group.clients)`.
  - Call `notify_completion("Grupo salvo com sucesso!")`.
  - Trigger `st.rerun()`.

**Step 5: Final verification**
Manually verify the UI layout and interaction.

**Step 6: Commit**
```bash
git add ui/groups_wizard_ui.py
git commit -m "feat(ui): integrate client groups selection and saving in wizard"
```
