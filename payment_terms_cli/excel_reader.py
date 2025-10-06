"""Excel extraction stubs for payment terms."""
from __future__ import annotations

from pathlib import Path
from typing import List

from openpyxl import load_workbook

from .models import PaymentTerm


def extract_payment_terms(workbook_path: Path) -> List[PaymentTerm]:
    """Return payment terms parsed from the Excel workbook.

    Students should implement this function using their preferred Excel
    library (e.g., ``openpyxl`` or ``pandas``). It must read the
    ``payment_terms`` worksheet, build :class:`~payment_terms_cli.models.PaymentTerm`
    instances with ``source="excel"``, and raise :class:`FileNotFoundError`
    if the workbook cannot be located.
    """

    workbook_path = Path(workbook_path)
    if not workbook_path.exists():
        raise FileNotFoundError(f"Workbook not found: {workbook_path}")

    workbook = load_workbook(filename=workbook_path, read_only=True, data_only=True)
    try:
        sheet = workbook["payment_terms"]
    except KeyError as exc:
        workbook.close()
        raise ValueError("Worksheet 'payment_terms' not found in workbook") from exc

    rows = sheet.iter_rows(values_only=True)
    headers_row = next(rows, None)
    if headers_row is None:
        workbook.close()
        return []

    headers = [str(header).strip() if header is not None else "" for header in headers_row]
    header_index = {header: idx for idx, header in enumerate(headers)}

    def _value(row, column_name: str):
        idx = header_index.get(column_name)
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    terms: List[PaymentTerm] = []
    try:
        for row in rows:
            raw_id = _value(row, "Days")
            if raw_id in (None, ""):
                raw_id = _value(row, "ID")

            name = _value(row, "Name")
            if name is None:
                continue
            name_str = str(name).strip()
            if not name_str:
                continue

            if raw_id in (None, ""):
                continue

            try:
                record_id = str(int(raw_id))
            except (TypeError, ValueError):
                record_id = str(raw_id).strip()

            if not record_id:
                continue

            terms.append(PaymentTerm(record_id=record_id, name=name_str, source="excel"))
    finally:
        workbook.close()

    return terms


__all__ = ["extract_payment_terms"]
