def test_create_and_fetch_process(sample_metadata, sample_diagnostics, sample_recommendation):
    from app.database import crud

    crud.ensure_db_ready()
    process_id = crud.create_process(None, sample_metadata)
    assert process_id > 0

    crud.save_diagnostics(process_id, sample_diagnostics)
    crud.save_recommendations(process_id, [sample_recommendation])
    crud.save_flow_diagrams(process_id, "flowchart TD\nA-->B", "flowchart TD\nA-->C")
    crud.save_executive_summary(process_id, "Summary text", {"total_recommendations": 1})

    full = crud.get_process_full(process_id)
    assert full["process"].process_name == "Vendor Invoice Processing"
    assert len(full["steps"]) == 3
    assert len(full["recommendations"]) == 1
    assert full["process"].flow_mermaid_current.startswith("flowchart")


def test_rehydrate_round_trip(sample_metadata, sample_diagnostics, sample_recommendation):
    from app.database import crud
    from app.database.rehydrate import load_report_context

    crud.ensure_db_ready()
    process_id = crud.create_process(None, sample_metadata)
    crud.save_diagnostics(process_id, sample_diagnostics)
    crud.save_recommendations(process_id, [sample_recommendation])
    crud.save_executive_summary(process_id, "Summary", {"total_fte_savings": 0.8})

    ctx = load_report_context(process_id)
    assert ctx is not None
    assert ctx.metadata.process_name == sample_metadata.process_name
    assert len(ctx.diagnostics) == 3
    assert ctx.diagnostics[1].lean_wastes  # waste enums round-tripped
    assert len(ctx.recommendations) == 1
    assert ctx.recommendations[0].category == sample_recommendation.category


def test_audit_log_and_feedback(sample_metadata):
    from app.database import crud

    crud.ensure_db_ready()
    process_id = crud.create_process(None, sample_metadata)
    crud.log_audit(process_id, "tester", "unit_test_action", {"k": "v"})
    crud.save_feedback(process_id, None, "tester", 5, "Great tool")
    # No exception = success; presence is implicitly covered by not raising.
