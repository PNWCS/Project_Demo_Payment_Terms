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
poetry run python -m payment_terms_cli --workbook company_terms.xlsx [--output report.json]
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
