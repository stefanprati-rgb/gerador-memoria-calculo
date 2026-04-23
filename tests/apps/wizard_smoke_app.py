from ui.groups_wizard_ui import render_groups_section_wizard


class FakeOrchestrator:
    def __init__(self):
        self.generate_calls = 0

    def count_filtered(self, clients, periods):
        return 3

    def check_incomplete_rows(self, clients, periods):
        return {
            "total_registros": 3,
            "registros_incompletos": 1,
            "ucs_afetadas": [
                {"no_uc": "UC001", "referencia": "01/2026", "razao_social": "Cliente A"}
            ],
        }

    def generate(self, clients, periods, **kwargs):
        self.generate_calls += 1
        return b"fake-excel-bytes"


render_groups_section_wizard(["Cliente A"], ["01/2026"], FakeOrchestrator())
