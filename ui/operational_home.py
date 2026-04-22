import os
import streamlit as st

from logic.services.sync_service import PARQUET_FILE, get_cache_update_time, get_pendencias
from ui.viewmodels.admin_viewmodel import AdminViewModel


def _render_status_card(title: str, value: str, state: str, help_text: str | None = None) -> None:
    st.markdown(
        f"""
        <div class="ops-card" data-state="{state}">
            <div class="ops-label">{title}</div>
            <div class="ops-value">{value}</div>
            <div class="ops-help">{help_text or ""}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_operational_home() -> None:
    """Renderiza a home operacional com status do sistema e atalhos de uso diário."""
    vm = AdminViewModel(mode="development")
    admin_state = vm.get_state()
    pendencias = get_pendencias() or {}

    cache_exists = os.path.exists(PARQUET_FILE)
    cache_status = "Disponível" if cache_exists else "Indisponível"
    local_sync_status = "Disponível" if admin_state.can_sync_local else "Indisponível"
    cloud_status = "Disponível" if admin_state.firebase_adapter else "Modo local"
    pending_count = pendencias.get("total_ucs_sem_vencimento", 0)
    base_state = "ready" if cache_exists else "warn"
    pending_state = "warn" if pending_count > 0 else "ready"
    cloud_state = "ready" if admin_state.firebase_adapter else "idle"
    local_state = "ready" if admin_state.can_sync_local else "idle"

    st.write("OPERATIONAL_HOME_MARKER")
    st.markdown(
        """
        <div class="ops-hero">
            <h2>Mesa de Operação</h2>
            <p>Confira o estado da base, identifique pendências e siga direto para a geração do arquivo. A ideia aqui é reduzir decisão operacional desnecessária.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ops-section-title">Leitura rápida do sistema</div>', unsafe_allow_html=True)
    st.markdown('<div class="ops-strip">', unsafe_allow_html=True)
    _render_status_card("Base local", cache_status, base_state, f"Atualizada em: {get_cache_update_time()}")
    _render_status_card("Pendências", str(pending_count), pending_state, "Faturas com vencimento ausente no último processamento.")
    _render_status_card("Backup online", cloud_status, cloud_state, "Disponibilidade da cópia de segurança em nuvem.")
    _render_status_card("Rede local", local_sync_status, local_state, "Atalho para sincronização automática quando disponível.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="ops-section-title">Próximas ações</div>', unsafe_allow_html=True)
    action_col_1, action_col_2 = st.columns(2)
    with action_col_1:
        if st.button("Ir para Geração", use_container_width=True, type="primary"):
            st.session_state.app_mode = "Gerador de Memória"
            st.rerun()
    with action_col_2:
        if st.button("Ir para Enriquecimento", use_container_width=True):
            st.session_state.app_mode = "Enriquecimento de Dados"
            st.rerun()

    if admin_state.fatal_error:
        st.error(admin_state.fatal_error)
    elif admin_state.firebase_warning:
        st.info(admin_state.firebase_warning)

    st.markdown('<div class="ops-section-title">Situação da operação</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="ops-panel">', unsafe_allow_html=True)
        st.markdown('<div class="ops-kicker">Diagnóstico</div>', unsafe_allow_html=True)
        if not cache_exists:
            st.markdown(
                '<div class="ops-summary">A base consolidada ainda não está pronta. O próximo passo correto é sincronizar as planilhas no painel administrativo.</div>',
                unsafe_allow_html=True,
            )
            st.warning("A base consolidada ainda não está disponível. Faça uma sincronização no painel admin.")
        elif pending_count > 0:
            st.markdown(
                f'<div class="ops-summary">A operação pode seguir, mas existem <strong>{pending_count}</strong> pendências abertas. O ideal é revisar antes de emitir arquivos finais sensíveis.</div>',
                unsafe_allow_html=True,
            )
            st.warning(f"Há {pending_count} pendências abertas. A geração continua disponível, mas a revisão é recomendada.")
        else:
            st.markdown(
                '<div class="ops-summary">A base está pronta para uso. Você pode seguir para a geração do arquivo com baixo risco operacional no estado atual.</div>',
                unsafe_allow_html=True,
            )
            st.success("A base está pronta para operação e não há pendências abertas no último processamento.")
        st.markdown("</div>", unsafe_allow_html=True)

    if pending_count > 0 and pendencias.get("pendencias"):
        st.markdown('<div class="ops-section-title">Amostra de pendências</div>', unsafe_allow_html=True)
        st.dataframe(pendencias["pendencias"][:10], use_container_width=True, hide_index=True)
