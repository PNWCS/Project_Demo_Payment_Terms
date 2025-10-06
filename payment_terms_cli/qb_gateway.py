"""QuickBooks COM gateway helpers for payment terms."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from contextlib import contextmanager
from typing import Iterator, List

try:
    import win32com.client  # type: ignore
except ImportError:  # pragma: no cover
    win32com = None  # type: ignore

from .models import PaymentTerm


APP_NAME = "Payment Terms CLI"


def _require_win32com() -> None:
    if win32com is None:  # pragma: no cover - exercised via tests
        raise RuntimeError("pywin32 is required to communicate with QuickBooks")


@contextmanager
def _qb_session() -> Iterator[tuple[object, object]]:
    _require_win32com()
    session = win32com.client.Dispatch("QBXMLRP2.RequestProcessor")
    session.OpenConnection2("", APP_NAME, 1)
    ticket = session.BeginSession("", 0)
    try:
        yield session, ticket
    finally:
        try:
            session.EndSession(ticket)
        finally:
            session.CloseConnection()


def _send_qbxml(qbxml: str) -> ET.Element:
    with _qb_session() as (session, ticket):
        print(f"Sending QBXML:\n{qbxml}")  # Debug output
        raw_response = session.ProcessRequest(ticket, qbxml)  # type: ignore[attr-defined]
        print(f"Received response:\n{raw_response}")  # Debug output
    return _parse_response(raw_response)


def _parse_response(raw_xml: str) -> ET.Element:
    root = ET.fromstring(raw_xml)
    response = root.find(".//*[@statusCode]")
    if response is None:
        raise RuntimeError("QuickBooks response missing status information")

    status_code = int(response.get("statusCode", "0"))
    status_message = response.get("statusMessage", "")
    # Status code 1 means "no matching objects found" - this is OK for queries
    if status_code != 0 and status_code != 1:
        print(f"QuickBooks error ({status_code}): {status_message}")
        raise RuntimeError(status_message)
    return root


def fetch_payment_terms(company_file: str | None = None) -> List[PaymentTerm]:
    """Return payment terms currently stored in QuickBooks."""

    qbxml = (
        '<?xml version="1.0"?>\n'
        '<?qbxml version="16.0"?>\n'
        "<QBXML>\n"
        '  <QBXMLMsgsRq onError="stopOnError">\n'
        "    <StandardTermsQueryRq/>\n"
        "  </QBXMLMsgsRq>\n"
        "</QBXML>"
    )
    root = _send_qbxml(qbxml)
    terms: List[PaymentTerm] = []
    for term_ret in root.findall(".//StandardTermsRet"):
        record_id = term_ret.findtext("StdDiscountDays")
        name = (term_ret.findtext("Name") or "").strip()

        if not record_id:
            continue
        try:
            record_id = str(int(record_id))
        except ValueError:
            record_id = record_id.strip()
        if not record_id:
            continue

        terms.append(PaymentTerm(record_id=record_id, name=name, source="quickbooks"))

    return terms


def add_payment_terms_batch(
    company_file: str | None, terms: List[PaymentTerm]
) -> List[PaymentTerm]:
    """Create multiple payment terms in QuickBooks in a single batch request."""

    if not terms:
        return []

    # Build the QBXML with multiple StandardTermsAddRq entries
    requests = []
    for term in terms:
        try:
            days_value = int(term.record_id)
        except ValueError as exc:
            raise ValueError(
                f"record_id must be numeric for QuickBooks payment terms: {term.record_id}"
            ) from exc

        requests.append(
            f"    <StandardTermsAddRq>\n"
            f"      <StandardTermsAdd>\n"
            f"        <Name>{_escape_xml(term.name)}</Name>\n"
            f"        <StdDiscountDays>{days_value}</StdDiscountDays>\n"
            f"        <DiscountPct>0</DiscountPct>\n"
            f"      </StandardTermsAdd>\n"
            f"    </StandardTermsAddRq>"
        )

    qbxml = (
        '<?xml version="1.0"?>\n'
        '<?qbxml version="13.0"?>\n'
        "<QBXML>\n"
        '  <QBXMLMsgsRq onError="continueOnError">\n' + "\n".join(requests) + "\n"
        "  </QBXMLMsgsRq>\n"
        "</QBXML>"
    )

    try:
        root = _send_qbxml(qbxml)
    except RuntimeError as exc:
        # If the entire batch fails, return empty list
        print(f"Batch add failed: {exc}")
        return []

    # Parse all responses
    added_terms: List[PaymentTerm] = []
    for term_ret in root.findall(".//StandardTermsRet"):
        record_id = term_ret.findtext("StdDiscountDays")
        if not record_id:
            continue
        try:
            record_id = str(int(record_id))
        except ValueError:
            record_id = record_id.strip()
        name = (term_ret.findtext("Name") or "").strip()
        added_terms.append(
            PaymentTerm(record_id=record_id, name=name, source="quickbooks")
        )

    return added_terms


def add_payment_term(company_file: str | None, term: PaymentTerm) -> PaymentTerm:
    """Create a payment term in QuickBooks and return the stored record."""

    try:
        days_value = int(term.record_id)
    except ValueError as exc:
        raise ValueError(
            "record_id must be numeric for QuickBooks payment terms"
        ) from exc

    qbxml = (
        '<?xml version="1.0"?>\n'
        '<?qbxml version="13.0"?>\n'
        "<QBXML>\n"
        '  <QBXMLMsgsRq onError="stopOnError">\n'
        "    <StandardTermsAddRq>\n"
        "      <StandardTermsAdd>\n"
        f"        <Name>{_escape_xml(term.name)}</Name>\n"
        f"        <StdDiscountDays>{days_value}</StdDiscountDays>\n"
        "        <DiscountPct>0</DiscountPct>\n"
        "      </StandardTermsAdd>\n"
        "    </StandardTermsAddRq>\n"
        "  </QBXMLMsgsRq>\n"
        "</QBXML>"
    )

    try:
        root = _send_qbxml(qbxml)
    except RuntimeError as exc:
        # Check if error is "name already in use" (error code 3100)
        if "already in use" in str(exc):
            # Return the term as-is since it already exists
            return PaymentTerm(
                record_id=term.record_id, name=term.name, source="quickbooks"
            )
        raise

    term_ret = root.find(".//StandardTermsRet")
    if term_ret is None:
        return PaymentTerm(
            record_id=term.record_id, name=term.name, source="quickbooks"
        )

    record_id = term_ret.findtext("StdDiscountDays") or term.record_id
    try:
        record_id = str(int(record_id))
    except ValueError:
        record_id = record_id.strip()
    name = (term_ret.findtext("Name") or term.name).strip()

    return PaymentTerm(record_id=record_id, name=name, source="quickbooks")


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


__all__ = ["fetch_payment_terms", "add_payment_term", "add_payment_terms_batch"]
