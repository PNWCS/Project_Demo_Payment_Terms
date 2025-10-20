Payment Terms CLI Template
===========================

This project orchestrates payment term synchronisation between an Excel workbook and QuickBooks Desktop. Students implement the Excel reader, QBXML gateway, and comparison logic.

JSON reports contain keys: status, generated_at, added_terms, conflicts, error. A success report lists each added term and conflict; a failure report sets status to "error" and populates the error string.

## Installation

Install dependencies using Poetry:
```bash
poetry install
```

## Usage

Command-line usage:
```bash
poetry run python -m payment_terms_cli --workbook PaymentTerms.xlsx [--output report.json]
```

Run tests with:
```bash
poetry run pytest
```

## Building as Executable

To build the project as a standalone `.exe`:

1. Install dependencies (including PyInstaller):
   ```bash
   poetry install
   ```

2. Build the executable:
   ```bash
   poetry run pyinstaller --onefile --name payment_terms_cli --hidden-import win32timezone --hidden-import win32com.client build_exe.py
   ```

3. The executable will be created in the `dist` folder.

The `--hidden-import` flags ensure PyInstaller includes the Windows COM dependencies needed for QuickBooks integration.

## Dummy Executables

For GUI development, this repo includes small dummy scripts that generate JSON
reports without connecting to QuickBooks. They live in `dummy_exes/`:

- `dummy_exes/payment_terms_dummy.py` — writes `payment_terms_report.json`-shaped output
- `dummy_exes/customers_dummy.py` — writes a similar report for customers
- `dummy_exes/vendors_dummy.py` — writes a similar report for vendors

Run directly with Python:

```bash
poetry run python -m dummy_exes.payment_terms_dummy --workbook PaymentTerms.xlsx --output payment_terms_report.json
poetry run python -m dummy_exes.customers_dummy --workbook PaymentTerms.xlsx --output customers_report.json
poetry run python -m dummy_exes.vendors_dummy --workbook PaymentTerms.xlsx --output vendors_report.json
```

Or build standalone executables with PyInstaller:

```bash
poetry run pyinstaller --onefile --name payment_terms_dummy dummy_exes/payment_terms_dummy.py
poetry run pyinstaller --onefile --name customers_dummy dummy_exes/customers_dummy.py
poetry run pyinstaller --onefile --name vendors_dummy dummy_exes/vendors_dummy.py
```

These dummy binaries have no external dependencies and do not require
QuickBooks. Each script requires a `--workbook` path for CLI compatibility and
accepts an optional `--output` path to control where the JSON file is written
(defaults shown above).
