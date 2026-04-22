from logic.services.orchestrator import Orchestrator

def test_generate():
    base_file = "gd_gestao_cobranca-1771957245_2026-02-24.xlsx"
    template_file = "mc.xlsx"
    
    orch = Orchestrator(base_file, template_file)
    
    # Check periods and clients
    clients = orch.get_available_clients()
    periods = orch.get_available_periods()
    
    print(f"Loaded {len(clients)} unique clients.")
    print(f"Available periods: {periods}")
    
    # Select first client and first period for testing
    if not clients or not periods:
        print("No clients or periods found to test.")
        return
        
    client_name = "LTA PARTICIPACOES LTDA"
    period = periods[-1] if periods else None
    
    print(f"Generating for client: {client_name}, period: {period}")
    
    excel_bytes = orch.generate([client_name], period)
    
    if excel_bytes:
        out_path = f"MC_Test_{client_name[:10].replace(' ', '')}.xlsx"
        with open(out_path, "wb") as f:
            f.write(excel_bytes)
        print(f"Generated successfully: {out_path} ({len(excel_bytes)} bytes)")
    else:
        print("Generation returned None.")

if __name__ == "__main__":
    test_generate()
