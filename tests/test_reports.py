import datetime as dt


def _make_ctx(sample_metadata, sample_diagnostics, sample_recommendation):
    from app.reports.report_data import ReportContext

    return ReportContext(
        metadata=sample_metadata, diagnostics=sample_diagnostics, recommendations=[sample_recommendation],
        savings_summary={
            "total_recommendations": 1, "quick_win_count": 1, "strategic_count": 0,
            "total_fte_savings": 0.8, "twelve_month_savings": 28000, "in_year_savings": 14000,
            "blended_efficiency_improvement_pct": 27.5, "target_efficiency_range_pct": "25-30%",
            "annual_fte_cost": 35000, "monthly_fte_cost": 2916.67, "months_remaining_in_year": 6,
        },
        executive_summary="Paragraph one.\n\nParagraph two with findings.",
        generated_at=dt.datetime.utcnow(),
    )


def test_generate_pdf_report(sample_metadata, sample_diagnostics, sample_recommendation):
    from app.reports.pdf import generate_pdf_report

    ctx = _make_ctx(sample_metadata, sample_diagnostics, sample_recommendation)
    data = generate_pdf_report(ctx)
    assert isinstance(data, bytes) and len(data) > 500
    assert data[:4] == b"%PDF"


def test_generate_word_report(sample_metadata, sample_diagnostics, sample_recommendation):
    from app.reports.word import generate_word_report

    ctx = _make_ctx(sample_metadata, sample_diagnostics, sample_recommendation)
    data = generate_word_report(ctx)
    assert isinstance(data, bytes) and len(data) > 500


def test_generate_excel_report(sample_metadata, sample_diagnostics, sample_recommendation):
    from app.reports.excel import generate_excel_report

    ctx = _make_ctx(sample_metadata, sample_diagnostics, sample_recommendation)
    data = generate_excel_report(ctx)
    assert isinstance(data, bytes) and len(data) > 500


def test_generate_ppt_report(sample_metadata, sample_diagnostics, sample_recommendation):
    from app.reports.ppt import generate_ppt_report

    ctx = _make_ctx(sample_metadata, sample_diagnostics, sample_recommendation)
    data = generate_ppt_report(ctx)
    assert isinstance(data, bytes) and len(data) > 500
