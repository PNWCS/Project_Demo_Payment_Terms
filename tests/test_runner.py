"""Tests for the payment terms runner module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from payment_terms_cli.models import ComparisonReport, Conflict, PaymentTerm
from payment_terms_cli.runner import run_payment_terms


@pytest.fixture
def mock_excel_terms():
    """Mock Excel payment terms."""
    return [
        PaymentTerm(record_id="15", name="Net 15", source="excel"),
        PaymentTerm(record_id="30", name="Net 30", source="excel"),
        PaymentTerm(record_id="45", name="Net 45", source="excel"),
    ]


@pytest.fixture
def mock_qb_terms():
    """Mock QuickBooks payment terms."""
    return [
        PaymentTerm(record_id="30", name="Net 30", source="quickbooks"),
        PaymentTerm(record_id="60", name="Net 60", source="quickbooks"),
    ]


@pytest.fixture
def mock_comparison_no_conflicts():
    """Mock comparison with no conflicts - only new terms to add."""
    comparison = ComparisonReport()
    comparison.excel_only = [
        PaymentTerm(record_id="15", name="Net 15", source="excel"),
        PaymentTerm(record_id="45", name="Net 45", source="excel"),
    ]
    comparison.qb_only = [
        PaymentTerm(record_id="60", name="Net 60", source="quickbooks"),
    ]
    comparison.conflicts = []
    return comparison


@pytest.fixture
def mock_comparison_with_conflicts():
    """Mock comparison with name mismatch conflicts."""
    comparison = ComparisonReport()
    comparison.excel_only = [
        PaymentTerm(record_id="15", name="Net 15", source="excel"),
    ]
    comparison.qb_only = []
    comparison.conflicts = [
        Conflict(
            record_id="30",
            excel_name="Net 30",
            qb_name="Payment in 30 days",
            reason="name_mismatch",
        )
    ]
    return comparison


class TestRunPaymentTerms:
    """Test suite for run_payment_terms function."""

    @patch("payment_terms_cli.runner.excel_reader.extract_payment_terms")
    @patch("payment_terms_cli.runner.qb_gateway.fetch_payment_terms")
    @patch("payment_terms_cli.runner.comparer.compare_payment_terms")
    @patch("payment_terms_cli.runner.qb_gateway.add_payment_terms_batch")
    @patch("payment_terms_cli.runner.write_report")
    def test_successful_sync_no_conflicts(
        self,
        mock_write_report,
        mock_add_batch,
        mock_compare,
        mock_fetch_qb,
        mock_extract_excel,
        mock_excel_terms,
        mock_qb_terms,
        mock_comparison_no_conflicts,
        tmp_path,
    ):
        """Test successful synchronization with no conflicts."""
        # Arrange
        workbook_path = "test_workbook.xlsx"
        output_path = tmp_path / "report.json"

        mock_extract_excel.return_value = mock_excel_terms
        mock_fetch_qb.return_value = mock_qb_terms
        mock_compare.return_value = mock_comparison_no_conflicts

        added_terms = [
            PaymentTerm(record_id="15", name="Net 15", source="quickbooks"),
            PaymentTerm(record_id="45", name="Net 45", source="quickbooks"),
        ]
        mock_add_batch.return_value = added_terms

        # Act
        result_path = run_payment_terms("", workbook_path, output_path=str(output_path))

        # Assert
        assert result_path == output_path
        mock_extract_excel.assert_called_once_with(Path(workbook_path))
        mock_fetch_qb.assert_called_once_with("")
        mock_compare.assert_called_once_with(mock_excel_terms, mock_qb_terms)
        mock_add_batch.assert_called_once_with(
            "", mock_comparison_no_conflicts.excel_only
        )

        # Verify report payload
        report_call = mock_write_report.call_args[0]
        report_payload = report_call[0]

        assert report_payload["status"] == "success"
        assert len(report_payload["added_terms"]) == 2
        assert report_payload["added_terms"][0]["record_id"] == "15"
        assert report_payload["added_terms"][1]["record_id"] == "45"
        assert len(report_payload["conflicts"]) == 1  # One missing_in_excel conflict
        assert report_payload["conflicts"][0]["reason"] == "missing_in_excel"
        assert report_payload["error"] is None

    @patch("payment_terms_cli.runner.excel_reader.extract_payment_terms")
    @patch("payment_terms_cli.runner.qb_gateway.fetch_payment_terms")
    @patch("payment_terms_cli.runner.comparer.compare_payment_terms")
    @patch("payment_terms_cli.runner.qb_gateway.add_payment_terms_batch")
    @patch("payment_terms_cli.runner.write_report")
    def test_sync_with_name_conflicts(
        self,
        mock_write_report,
        mock_add_batch,
        mock_compare,
        mock_fetch_qb,
        mock_extract_excel,
        mock_excel_terms,
        mock_qb_terms,
        mock_comparison_with_conflicts,
        tmp_path,
    ):
        """Test synchronization with name mismatch conflicts."""
        # Arrange
        workbook_path = "test_workbook.xlsx"
        output_path = tmp_path / "report.json"

        mock_extract_excel.return_value = mock_excel_terms
        mock_fetch_qb.return_value = mock_qb_terms
        mock_compare.return_value = mock_comparison_with_conflicts

        added_terms = [
            PaymentTerm(record_id="15", name="Net 15", source="quickbooks"),
        ]
        mock_add_batch.return_value = added_terms

        # Act
        result_path = run_payment_terms("", workbook_path, output_path=str(output_path))

        # Assert
        assert result_path == output_path

        # Verify report payload
        report_call = mock_write_report.call_args[0]
        report_payload = report_call[0]

        assert report_payload["status"] == "success"
        assert len(report_payload["added_terms"]) == 1
        assert len(report_payload["conflicts"]) == 1
        assert report_payload["conflicts"][0]["reason"] == "name_mismatch"
        assert report_payload["conflicts"][0]["excel_name"] == "Net 30"
        assert report_payload["conflicts"][0]["qb_name"] == "Payment in 30 days"

    @patch("payment_terms_cli.runner.excel_reader.extract_payment_terms")
    @patch("payment_terms_cli.runner.qb_gateway.fetch_payment_terms")
    @patch("payment_terms_cli.runner.comparer.compare_payment_terms")
    @patch("payment_terms_cli.runner.qb_gateway.add_payment_terms_batch")
    @patch("payment_terms_cli.runner.write_report")
    def test_sync_with_no_new_terms(
        self,
        mock_write_report,
        mock_add_batch,
        mock_compare,
        mock_fetch_qb,
        mock_extract_excel,
        tmp_path,
    ):
        """Test synchronization when all terms already exist."""
        # Arrange
        workbook_path = "test_workbook.xlsx"
        output_path = tmp_path / "report.json"

        excel_terms = [PaymentTerm(record_id="30", name="Net 30", source="excel")]
        qb_terms = [PaymentTerm(record_id="30", name="Net 30", source="quickbooks")]

        comparison = ComparisonReport()
        comparison.excel_only = []
        comparison.qb_only = []
        comparison.conflicts = []

        mock_extract_excel.return_value = excel_terms
        mock_fetch_qb.return_value = qb_terms
        mock_compare.return_value = comparison
        mock_add_batch.return_value = []

        # Act
        result_path = run_payment_terms("", workbook_path, output_path=str(output_path))

        # Assert
        assert result_path == output_path
        mock_add_batch.assert_called_once_with("", [])

        # Verify report payload
        report_call = mock_write_report.call_args[0]
        report_payload = report_call[0]

        assert report_payload["status"] == "success"
        assert len(report_payload["added_terms"]) == 0
        assert len(report_payload["conflicts"]) == 0

    @patch("payment_terms_cli.runner.excel_reader.extract_payment_terms")
    @patch("payment_terms_cli.runner.qb_gateway.fetch_payment_terms")
    @patch("payment_terms_cli.runner.write_report")
    def test_error_handling(
        self,
        mock_write_report,
        mock_fetch_qb,
        mock_extract_excel,
        tmp_path,
    ):
        """Test error handling when QB connection fails."""
        # Arrange
        workbook_path = "test_workbook.xlsx"
        output_path = tmp_path / "report.json"

        mock_extract_excel.return_value = []
        mock_fetch_qb.side_effect = RuntimeError("QuickBooks connection failed")

        # Act
        result_path = run_payment_terms("", workbook_path, output_path=str(output_path))

        # Assert
        assert result_path == output_path

        # Verify error report payload
        report_call = mock_write_report.call_args[0]
        report_payload = report_call[0]

        assert report_payload["status"] == "error"
        assert "QuickBooks connection failed" in report_payload["error"]
        assert len(report_payload["added_terms"]) == 0
        assert len(report_payload["conflicts"]) == 0

    @patch("payment_terms_cli.runner.excel_reader.extract_payment_terms")
    @patch("payment_terms_cli.runner.write_report")
    def test_excel_read_error(
        self,
        mock_write_report,
        mock_extract_excel,
        tmp_path,
    ):
        """Test error handling when Excel file cannot be read."""
        # Arrange
        workbook_path = "nonexistent.xlsx"
        output_path = tmp_path / "report.json"

        mock_extract_excel.side_effect = FileNotFoundError("Excel file not found")

        # Act
        result_path = run_payment_terms("", workbook_path, output_path=str(output_path))

        # Assert
        assert result_path == output_path

        # Verify error report payload
        report_call = mock_write_report.call_args[0]
        report_payload = report_call[0]

        assert report_payload["status"] == "error"
        assert "Excel file not found" in report_payload["error"]

    @patch("payment_terms_cli.runner.excel_reader.extract_payment_terms")
    @patch("payment_terms_cli.runner.qb_gateway.fetch_payment_terms")
    @patch("payment_terms_cli.runner.comparer.compare_payment_terms")
    @patch("payment_terms_cli.runner.qb_gateway.add_payment_terms_batch")
    @patch("payment_terms_cli.runner.write_report")
    def test_default_output_path(
        self,
        mock_write_report,
        mock_add_batch,
        mock_compare,
        mock_fetch_qb,
        mock_extract_excel,
    ):
        """Test that default output path is used when not specified."""
        # Arrange
        workbook_path = "test_workbook.xlsx"

        comparison = ComparisonReport()
        comparison.excel_only = []
        comparison.qb_only = []
        comparison.conflicts = []

        mock_extract_excel.return_value = []
        mock_fetch_qb.return_value = []
        mock_compare.return_value = comparison
        mock_add_batch.return_value = []

        # Act
        result_path = run_payment_terms("", workbook_path)

        # Assert
        assert result_path == Path("payment_terms_report.json")
        mock_write_report.assert_called_once()
