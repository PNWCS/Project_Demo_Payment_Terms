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

Generate a coverage report with:
```bash
poetry run pytest --cov=payment_terms_cli --cov-report=term-missing
```
Add `--cov-report=html` to emit an HTML report in `htmlcov/`.

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

### Running the Executable

After building, launch the CLI directly from Command Prompt:

1. Change into the `dist` directory (or reference the full path):
   ```cmd
   cd dist
   ```
2. Run the executable with the same arguments the Python entry point expects:
   ```cmd
   payment_terms_cli.exe --workbook C:\path\to\PaymentTerms.xlsx --output C:\path\to\report.json
   ```

If you omit `--output`, the report defaults to `payment_terms_report.json` in the current directory. You can also invoke it without `cd` by using the absolute path, e.g.:

```cmd
C:\Users\VictorG\Project_Demo_Terms\Project_Demo_Payment_Terms\dist\payment_terms_cli.exe --workbook PaymentTerms.xlsx
```
