from dataclasses import dataclass
from typing import List, Any, Optional
from ui.utils.format_utils import sanitize_filename

@dataclass
class WizardReviewMetrics:
    total_invoices: int = 0
    incomplete_count: int = 0
    complete_count: int = 0
    incomplete_details: Optional[Any] = None

@dataclass
class GenerationPayload:
    clients: List[str]
    periods: List[str]
    incomplete_filter: str
    group_by_distributor: bool
    enrichment_df: Optional[Any]
    somente_pendencias: bool
    tipo_apresentacao: str
    incluir_resumo: bool
    separar_auditoria: bool
    is_multiplexed: bool
    filename: str
    mime_type: str

class WizardViewModel:
    def __init__(self, orchestrator: Any):
        self.orch = orchestrator

    def get_review_metrics(self, clients: List[str], periods: List[str]) -> WizardReviewMetrics:
        metrics = WizardReviewMetrics()
        
        if not clients or not periods:
            return metrics

        metrics.total_invoices = self.orch.count_filtered(clients, periods)
        
        incomplete_info = self.orch.check_incomplete_rows(clients, periods)
        metrics.incomplete_count = incomplete_info.get("registros_incompletos", 0)
        metrics.complete_count = incomplete_info.get("total_registros", 0) - metrics.incomplete_count
        metrics.incomplete_details = incomplete_info.get("ucs_afetadas")
        
        return metrics

    def prepare_generation_payload(
        self, 
        group: Any, 
        incomplete_filter: str, 
        enrichment_df: Optional[Any] = None
    ) -> GenerationPayload:
        
        is_multiplexed = len(group.periods) > 1
        safe_name = sanitize_filename(group.name)
        
        if is_multiplexed:
            filename = f"{safe_name}.zip"
            mime_type = "application/zip"
        else:
            filename = f"{safe_name}.xlsx"
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        return GenerationPayload(
            clients=group.clients,
            periods=group.periods,
            incomplete_filter=incomplete_filter,
            group_by_distributor=group.group_by_distributor,
            enrichment_df=enrichment_df,
            somente_pendencias=group.somente_pendencias,
            tipo_apresentacao=group.tipo_apresentacao,
            incluir_resumo=group.incluir_resumo,
            separar_auditoria=group.separar_auditoria,
            is_multiplexed=is_multiplexed,
            filename=filename,
            mime_type=mime_type
        )
