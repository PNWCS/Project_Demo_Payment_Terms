from __future__ import annotations

import json
from pathlib import Path

import pytest

from payment_terms_cli import runner
from payment_terms_cli.models import ComparisonReport, Conflict, PaymentTerm


@pytest.fixture
def temp_report(tmp_path: Path) -> Path:
    return tmp_path / "report.json"


def test_run_payment_terms_success(monkeypatch, temp_report, tmp_path: Path):
    excel_terms = [PaymentTerm(record_id="30", name="Net 30", source="excel")]
    qb_terms = [PaymentTerm(record_id="45", name="QB Net 45", source="quickbooks")]

    comparison = ComparisonReport(
        excel_only=[excel_terms[0]],
        qb_only=[qb_terms[0]],
        conflicts=[Conflict(record_id="45", excel_name="Net 45", qb_name="QB Net 45", reason="name_mismatch")],
    )

    monkeypatch.setattr(runner.excel_reader, "extract_payment_terms", lambda path: excel_terms)
    monkeypatch.setattr(runner.qb_gateway, "fetch_payment_terms", lambda company: qb_terms)

    added_terms: list[PaymentTerm] = []

    def fake_add(company_file: str, term: PaymentTerm) -> PaymentTerm:
        created = PaymentTerm(record_id=term.record_id, name=term.name, source="quickbooks")
        added_terms.append(created)
        return created

    monkeypatch.setattr(runner.qb_gateway, "add_payment_term", fake_add)
    monkeypatch.setattr(runner.comparer, "compare_payment_terms", lambda excel, qb: comparison)

    output = runner.run_payment_terms("company.qbw", "workbook.xlsx", output_path=str(temp_report))

    assert output == temp_report
    payload = json.loads(temp_report.read_text())
    assert payload["status"] == "success"
    assert payload["added_terms"] == [{"record_id": "30", "name": "Net 30", "source": "quickbooks"}]
    assert any(conflict["reason"] == "missing_in_excel" for conflict in payload["conflicts"])
    assert any(conflict["reason"] == "name_mismatch" for conflict in payload["conflicts"])
    assert payload["error"] is None


def test_run_payment_terms_failure(monkeypatch, temp_report):
    def explode(path):  # pragma: no cover - behaviour verified in test
        raise RuntimeError("boom")

    monkeypatch.setattr(runner.excel_reader, "extract_payment_terms", explode)

    output = runner.run_payment_terms("company.qbw", "workbook.xlsx", output_path=str(temp_report))
    assert output == temp_report

    payload = json.loads(temp_report.read_text())
    assert payload["status"] == "error"
    assert payload["error"] == "boom"
    assert payload["added_terms"] == []
    assert payload["conflicts"] == []
