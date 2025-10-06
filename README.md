Payment Terms CLI Template
===========================

This project orchestrates payment term synchronisation between an Excel workbook and QuickBooks Desktop. Students implement the Excel reader, QBXML gateway, and comparison logic.

The public contract is payment_terms_cli.runner.run_payment_terms(company_file_path, workbook_path, output_path=None).

JSON reports contain keys: status, generated_at, added_terms, conflicts, error. A success report lists each added term and conflict; a failure report sets status to "error" and populates the error string.

Command-line usage: python -m payment_terms_cli --workbook company_terms.xlsx [--output report.json].

Stub functions to implement: excel_reader.extract_payment_terms, qb_gateway.fetch_payment_terms, qb_gateway.add_payment_term, comparer.compare_payment_terms.

Run tests with: python -m pytest.
