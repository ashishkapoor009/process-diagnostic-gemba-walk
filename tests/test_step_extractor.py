def test_parse_manual_steps_basic():
    from app.extraction.step_extractor import parse_manual_steps

    text = "Receive request\nLog in system :: Ops Analyst :: CRM :: 5\nApprove :: Manager :: Email :: 10"
    steps = parse_manual_steps(text)
    assert len(steps) == 3
    assert steps[0].step_name == "Receive request"
    assert steps[1].owner == "Ops Analyst"
    assert steps[1].system_used == "CRM"
    assert steps[1].cycle_time_minutes == 5.0
    assert [s.step_number for s in steps] == [1, 2, 3]


def test_parse_manual_steps_ignores_blank_lines_and_bullets():
    from app.extraction.step_extractor import parse_manual_steps

    text = "1. First step\n\n- Second step\n* Third step"
    steps = parse_manual_steps(text)
    assert [s.step_name for s in steps] == ["First step", "Second step", "Third step"]
