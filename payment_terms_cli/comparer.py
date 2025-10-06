"""Comparison helpers for payment terms."""

from __future__ import annotations

from typing import Dict, Iterable

from .models import ComparisonReport, Conflict, PaymentTerm


def compare_payment_terms(
    excel_terms: Iterable[PaymentTerm],
    qb_terms: Iterable[PaymentTerm],
) -> ComparisonReport:
    """Compare Excel and QuickBooks payment terms and identify discrepancies.

    This function reconciles payment terms from two sources (Excel and QuickBooks)
    by comparing their ``record_id`` and ``name`` fields. Students must implement
    the logic to detect three types of discrepancies:

    1. Terms that exist only in Excel
    2. Terms that exist only in QuickBooks
    3. Terms with matching ``record_id`` but different ``name`` values

    **Input Parameters:**

    :param excel_terms: An iterable of :class:`~payment_terms_cli.models.PaymentTerm`
        objects sourced from Excel. Each PaymentTerm has:

        - ``record_id`` (str): Unique identifier for the payment term
        - ``name`` (str): Display name of the payment term
        - ``source`` (SourceLiteral): Will be "excel" for these terms

        Example: ``PaymentTerm(record_id="NET30", name="Net 30", source="excel")``

    :param qb_terms: An iterable of :class:`~payment_terms_cli.models.PaymentTerm`
        objects sourced from QuickBooks. Structure is identical to ``excel_terms``
        but with ``source="quickbooks"``.

        Example: ``PaymentTerm(record_id="NET30", name="Net 30 Days", source="quickbooks")``

    **Return Value:**

    :return: A :class:`~payment_terms_cli.models.ComparisonReport` object containing
        three lists that categorize all discrepancies found:

        - ``excel_only`` (list[PaymentTerm]): Terms with ``record_id`` values that
          appear in ``excel_terms`` but NOT in ``qb_terms``. These represent payment
          terms that need to be added to QuickBooks.

        - ``qb_only`` (list[PaymentTerm]): Terms with ``record_id`` values that
          appear in ``qb_terms`` but NOT in ``excel_terms``. These represent payment
          terms that may need to be removed from QuickBooks or added to Excel.

        - ``conflicts`` (list[Conflict]): Terms where the same ``record_id`` exists
          in both sources but the ``name`` field differs. Each
          :class:`~payment_terms_cli.models.Conflict` must have:

          - ``record_id`` (str): The shared record ID
          - ``excel_name`` (str | None): The name from Excel
          - ``qb_name`` (str | None): The name from QuickBooks
          - ``reason`` (ConflictReason): Must be ``"name_mismatch"`` for these cases

    **Implementation Requirements:**

    1. Compare terms based on their ``record_id`` field (case-sensitive)
    2. Build dictionaries or sets for efficient lookup of record IDs
    3. Identify terms unique to each source (Excel-only and QB-only)
    4. For matching ``record_id`` values, compare the ``name`` fields
    5. If names differ, create a Conflict with reason ``"name_mismatch"``
    6. Return all findings in a ComparisonReport object

    **Example:**

    Given these inputs::

        excel_terms = [
            PaymentTerm(record_id="NET30", name="Net 30", source="excel"),
            PaymentTerm(record_id="NET60", name="Net 60", source="excel"),
            PaymentTerm(record_id="COD", name="Cash on Delivery", source="excel"),
        ]

        qb_terms = [
            PaymentTerm(record_id="NET30", name="Net 30 Days", source="quickbooks"),
            PaymentTerm(record_id="NET60", name="Net 60", source="quickbooks"),
            PaymentTerm(record_id="DUE", name="Due on Receipt", source="quickbooks"),
        ]

    Expected output::

        ComparisonReport(
            excel_only=[
                PaymentTerm(record_id="COD", name="Cash on Delivery", source="excel")
            ],
            qb_only=[
                PaymentTerm(record_id="DUE", name="Due on Receipt", source="quickbooks")
            ],
            conflicts=[
                Conflict(
                    record_id="NET30",
                    excel_name="Net 30",
                    qb_name="Net 30 Days",
                    reason="name_mismatch"
                )
            ]
        )

    Note: NET60 appears in both sources with the same name, so it does not appear
    in any of the report's collections (no conflict, not Excel-only, not QB-only).
    """

    # Index terms by record_id for quick lookup
    excel_dict: Dict[str, PaymentTerm] = {term.record_id: term for term in excel_terms}
    qb_dict: Dict[str, PaymentTerm] = {term.record_id: term for term in qb_terms}

    # Excel only terms
    excel_only = [term for term in excel_dict.values() if term.record_id not in qb_dict]

    # QB only terms
    qb_only = [term for term in qb_dict.values() if term.record_id not in excel_dict]

    # Conflicts: same record_id but different names
    conflicts = []
    common_ids = set(excel_dict.keys()).intersection(qb_dict.keys())
    for record_id in common_ids:
        excel_name = excel_dict[record_id].name
        qb_name = qb_dict[record_id].name
        if excel_name != qb_name:
            conflicts.append(
                Conflict(
                    record_id=record_id,
                    excel_name=excel_name,
                    qb_name=qb_name,
                    reason="name_mismatch",
                )
            )
    return ComparisonReport(
        excel_only=excel_only,
        qb_only=qb_only,
        conflicts=conflicts,
    )


__all__ = ["compare_payment_terms"]
