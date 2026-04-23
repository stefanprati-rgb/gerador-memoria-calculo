from dataclasses import dataclass
from typing import List, Any, Optional
from ui.utils.format_utils import sanitize_filename, build_runtime_filename

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
    grouping_mode: str
    include_child_rows: bool
    enrichment_df: Optional[Any]
    somente_pendencias: bool
    tipo_apresentacao: str
    incluir_resumo: bool
    separar_auditoria: bool
    sort_by: str
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
            filename = build_runtime_filename(safe_name, ".zip")
            mime_type = "application/zip"
        else:
            filename = build_runtime_filename(safe_name, ".xlsx")
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        return GenerationPayload(
            clients=group.clients,
            periods=group.periods,
            incomplete_filter=incomplete_filter,
            grouping_mode=group.grouping_mode,
            include_child_rows=group.include_child_rows,
            enrichment_df=enrichment_df,
            somente_pendencias=group.somente_pendencias,
            tipo_apresentacao=group.tipo_apresentacao,
            incluir_resumo=group.incluir_resumo,
            separar_auditoria=group.separar_auditoria,
            sort_by=getattr(group, "sort_by", "Economia Gerada (Desc)"),
            is_multiplexed=is_multiplexed,
            filename=filename,
            mime_type=mime_type
        )

    @staticmethod
    def load_shortcut(group_id: int, shortcut_name: str) -> bool:
        """Carrega clientes e configurações de um grupo salvo e sincroniza com o GroupState."""
        from logic.services.client_group_service import get_clients_from_group
        from ui.state.group_state import select_clients, update_group_name, set_grouping_mode, get_group
        from logic.services import enrichment_service
        from logic.core.mapping import GROUPING_MODE_DEFAULT, GROUPING_MODE_DISTRIBUTOR
        import pandas as pd
        import logging

        clients = get_clients_from_group(shortcut_name)
        if not clients:
            return False

        select_clients(group_id, clients)
        # Atalho deve manter nome dinâmico no passo 2 (base + períodos).
        update_group_name(group_id, shortcut_name)
        group = get_group(group_id)
        if group:
            group.is_auto_name = True

        try:
            # Evita efeitos colaterais no Firestore quando não existe perfil de mapeamento
            # para o grupo salvo (atalho de clientes).
            if shortcut_name in enrichment_service.list_profiles():
                profile = enrichment_service.load_mapping(shortcut_name)
                if profile is not None:
                    val = False
                    if isinstance(profile, dict):
                        val = profile.get("group_by_distributor", False)
                    elif hasattr(profile, "get"):
                        res = profile.get("group_by_distributor", False)
                        if not isinstance(res, (pd.Series, pd.DataFrame)):
                            val = res
                    set_grouping_mode(group_id, GROUPING_MODE_DISTRIBUTOR if bool(val) else GROUPING_MODE_DEFAULT)
        except Exception as e:
            logging.getLogger(__name__).error("Erro ao sincronizar regras de perfil: %s", e)

        return True
