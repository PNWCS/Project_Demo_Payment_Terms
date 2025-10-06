"""Comparison helpers for payment terms."""
from __future__ import annotations

from typing import Dict, Iterable

from .models import ComparisonReport, Conflict, PaymentTerm


def compare_payment_terms(
    excel_terms: Iterable[PaymentTerm],
    qb_terms: Iterable[PaymentTerm],
) -> ComparisonReport:
    """Compare Excel and QuickBooks payment terms.

    Students must implement reconciliation logic that returns a
    :class:`~payment_terms_cli.models.ComparisonReport`. The
    ``excel_only`` collection should contain terms present in Excel but absent
    from QuickBooks. The ``qb_only`` collection should contain terms absent
    from Excel but present in QuickBooks. Any field-level mismatches should
    be captured as :class:`~payment_terms_cli.models.Conflict` entries with
    the reason ``"name_mismatch"``.
    """

    excel_index: Dict[str, PaymentTerm] = {term.record_id: term for term in excel_terms}
    qb_index: Dict[str, PaymentTerm] = {term.record_id: term for term in qb_terms}

    report = ComparisonReport()

    all_ids = sorted(set(excel_index) | set(qb_index), key=lambda value: (len(value), value))

    for record_id in all_ids:
        excel_term = excel_index.get(record_id)
        qb_term = qb_index.get(record_id)

        if excel_term and not qb_term:
            report.excel_only.append(excel_term)
            continue

        if qb_term and not excel_term:
            report.qb_only.append(qb_term)
            continue

        if excel_term and qb_term and excel_term.name != qb_term.name:
            report.conflicts.append(
                Conflict(
                    record_id=record_id,
                    excel_name=excel_term.name,
                    qb_name=qb_term.name,
                    reason="name_mismatch",
                )
            )

    return report


__all__ = ["compare_payment_terms"]
