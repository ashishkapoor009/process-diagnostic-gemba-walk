def test_render_flowchart_contains_all_steps(sample_diagnostics):
    from app.graphs.mermaid import render_flowchart

    diagram = render_flowchart(sample_diagnostics)
    assert "flowchart TD" in diagram
    for d in sample_diagnostics:
        assert f"S{d.step_number}" in diagram


def test_render_flowchart_empty():
    from app.graphs.mermaid import render_flowchart

    diagram = render_flowchart([])
    assert "No steps to display" in diagram


def test_render_swimlane_groups_by_owner(sample_diagnostics):
    from app.graphs.mermaid import render_swimlane

    diagram = render_swimlane(sample_diagnostics)
    assert "subgraph" in diagram
    assert "AP Clerk" in diagram


def test_render_vsm_includes_pce(sample_diagnostics):
    from app.graphs.mermaid import render_vsm

    diagram = render_vsm(sample_diagnostics)
    assert "Process Cycle Efficiency" in diagram


def test_decision_step_renders_as_diamond(sample_diagnostics):
    from app.graphs.mermaid import render_flowchart

    diagram = render_flowchart(sample_diagnostics)
    decision_step = next(d for d in sample_diagnostics if d.is_decision)
    assert "{" in diagram and f"S{decision_step.step_number}" + '{"' in diagram
