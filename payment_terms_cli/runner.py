"""High-level orchestration for the payment term CLI.

This module coordinates the end-to-end process of reading payment terms from
Excel, retrieving existing terms from QuickBooks, comparing both datasets,
creating any missing terms in QuickBooks, and writing a comprehensive JSON
report summarising the outcome.
"""

from __future__ import annotations

from pathlib import Path  # Filesystem path handling
from typing import Dict, List  # Type annotations for clarity

from . import comparer, excel_reader, qb_gateway  # Local modules used in orchestration
from .models import Conflict, PaymentTerm  # Domain types
from .reporting import iso_timestamp, write_report  # JSON and timestamps

DEFAULT_REPORT_NAME = "payment_terms_report.json"  # Default output filename


def _term_to_dict(term: PaymentTerm) -> Dict[str, object]:
    """Convert a PaymentTerm object into a serialisable dict.

    This shape is used in the JSON report's "added_terms" collection.
    """
    return {
        "record_id": term.record_id,
        "name": term.name,
        "source": term.source,
        "due_days": term.due_days,
    }


def _conflict_to_dict(conflict: Conflict) -> Dict[str, object]:
    """Convert a Conflict object into a serialisable dict for the report."""
    return {
        "record_id": conflict.record_id,
        "reason": conflict.reason,
        "excel_name": conflict.excel_name,
        "qb_name": conflict.qb_name,
        "excel_due_days": conflict.excel_due_days,
        "qb_due_days": conflict.qb_due_days,
    }


def _missing_in_excel_conflict(term: PaymentTerm) -> Dict[str, object]:
    """Create a synthetic conflict for terms present only in QuickBooks.

    In the report, terms that exist in QuickBooks but not Excel are represented
    as conflicts with reason "missing_in_excel".
    """
    return {
        "record_id": term.record_id,
        "reason": "missing_in_excel",
        "excel_name": None,
        "qb_name": term.name,
        "excel_due_days": None,
        "qb_due_days": term.due_days,
    }


def _count_matching_terms(
    excel_terms: List[PaymentTerm], qb_terms: List[PaymentTerm]
) -> int:
    """Return the number of terms that exist in both sources with identical data."""

    excel_by_id = {term.record_id: term for term in excel_terms}
    qb_by_id = {term.record_id: term for term in qb_terms}

    matches = 0
    for record_id in excel_by_id.keys() & qb_by_id.keys():
        excel_term = excel_by_id[record_id]
        qb_term = qb_by_id[record_id]
        if excel_term.name == qb_term.name and excel_term.due_days == qb_term.due_days:
            matches += 1
    return matches


def run_payment_terms(
    company_file_path: str,
    workbook_path: str,
    *,
    output_path: str | None = None,
) -> Path:
    """Contract entry point for synchronising payment terms.

    Args:
        company_file_path: Path to the QuickBooks company file. Use an empty
            string to reuse the currently open company file.
        workbook_path: Path to the Excel workbook containing the
            payment_terms worksheet.
        output_path: Optional JSON output path. Defaults to
            payment_terms_report.json in the current working directory.

    Returns:
        Path to the generated JSON report.
    """
    # Choose report path: user-provided or default filename in CWD
    report_path = Path(output_path) if output_path else Path(DEFAULT_REPORT_NAME)
    # Initialise the report payload with default success shape
    report_payload: Dict[str, object] = {
        "status": "success",
        "generated_at": iso_timestamp(),
        "added_terms": [],
        "conflicts": [],
        "same_terms": 0,
        "error": None,
    }

    try:
        # Extract terms from the Excel workbook
        excel_terms = excel_reader.extract_payment_terms(Path(workbook_path))
        # Fetch existing terms from QuickBooks
        qb_terms = qb_gateway.fetch_payment_terms(company_file_path)
        # Compare the two sources to find discrepancies
        comparison = comparer.compare_payment_terms(excel_terms, qb_terms)

        # Add any terms that exist only in Excel to QuickBooks in a batch
        added_terms = qb_gateway.add_payment_terms_batch(
            company_file_path, comparison.excel_only
        )

        # Build conflicts list: data mismatches + items missing from Excel
        conflicts: List[Dict[str, object]] = []
        conflicts.extend(
            _conflict_to_dict(conflict) for conflict in comparison.conflicts
        )
        conflicts.extend(
            _missing_in_excel_conflict(term) for term in comparison.qb_only
        )

        # Populate the report payload with results
        report_payload["added_terms"] = [_term_to_dict(term) for term in added_terms]
        report_payload["conflicts"] = conflicts
        report_payload["same_terms"] = _count_matching_terms(excel_terms, qb_terms)

    except Exception as exc:  # pragma: no cover - behaviour verified via tests
        # On any error, capture the message and mark the report as failure
        report_payload["status"] = "error"
        report_payload["error"] = str(exc)

    # Persist the report to disk and return its path
    write_report(report_payload, report_path)
    return report_path


__all__ = ["run_payment_terms", "DEFAULT_REPORT_NAME"]
