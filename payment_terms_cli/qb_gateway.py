"""QuickBooks COM gateway helpers for payment terms.

This module communicates with QuickBooks Desktop via the QBXML Request Processor
COM interface exposed by ``pywin32``. It provides functions to query existing
payment terms and to add new terms in batches.
"""

from __future__ import annotations  # Enable postponed evaluation of annotations

import xml.etree.ElementTree as ET  # XML parsing for QBXML responses
from contextlib import contextmanager  # For clean session management
from typing import Iterator, List  # Type hints for readability

try:
    import win32com.client  # type: ignore  # Imported lazily to allow testing without pywin32
except ImportError:  # pragma: no cover
    win32com = None  # type: ignore  # Fallback used to raise a clear error later

from .models import PaymentTerm  # Core domain model for payment terms


APP_NAME = "Quickbooks Connector"  # do not chanege this (intentional spelling per spec)


def _require_win32com() -> None:
    """Ensure the win32com dependency is available before COM operations."""
    if win32com is None:  # pragma: no cover - exercised via tests
        raise RuntimeError("pywin32 is required to communicate with QuickBooks")


@contextmanager
def _qb_session() -> Iterator[tuple[object, object]]:
    """Context manager that opens and closes a QBXML request processor session.

    Yields a tuple of (session, ticket) that must be used to send requests.
    Ensures sessions are properly closed even if errors occur.
    """
    _require_win32com()
    session = win32com.client.Dispatch(
        "QBXMLRP2.RequestProcessor"
    )  # Acquire COM object
    session.OpenConnection2("", APP_NAME, 1)  # Register connection with an app name
    ticket = session.BeginSession(
        "", 0
    )  # Start a session using the currently open company file
    try:
        yield session, ticket  # Provide the session and ticket to the caller
    finally:
        try:
            session.EndSession(ticket)  # Always end the session
        finally:
            session.CloseConnection()  # And close the connection regardless of errors


def _send_qbxml(qbxml: str) -> ET.Element:
    """Send a QBXML request and return the parsed XML root element."""
    with _qb_session() as (session, ticket):
        print(f"Sending QBXML:\n{qbxml}")  # Debug output to aid diagnostics
        raw_response = session.ProcessRequest(ticket, qbxml)  # type: ignore[attr-defined]
        print(f"Received response:\n{raw_response}")  # Debug output of QB response
    return _parse_response(raw_response)


def _parse_response(raw_xml: str) -> ET.Element:
    """Parse raw QBXML response and raise on error status codes."""
    root = ET.fromstring(raw_xml)  # Parse the XML text into an element tree
    response = root.find(".//*[@statusCode]")  # Locate the first node with a status
    if response is None:
        raise RuntimeError("QuickBooks response missing status information")

    status_code = int(response.get("statusCode", "0"))  # Convert status code to int
    status_message = response.get("statusMessage", "")  # Retrieve status message
    # Status code 1 means "no matching objects found" - this is OK for queries
    if status_code != 0 and status_code != 1:
        print(f"QuickBooks error ({status_code}): {status_message}")  # Log the error
        raise RuntimeError(status_message)  # Propagate as a runtime error
    return root  # Return the parsed XML root


def fetch_payment_terms(company_file: str | None = None) -> List[PaymentTerm]:
    """Return payment terms currently stored in QuickBooks.

    The ``company_file`` parameter is currently unused since sessions default to
    the open company file, but is kept for API symmetry with other functions.
    """

    qbxml = """\
<?xml version="1.0"?>
<?qbxml version="16.0"?>
<QBXML>
  <QBXMLMsgsRq onError="stopOnError">
    <StandardTermsQueryRq/>
  </QBXMLMsgsRq>
</QBXML>"""
    root = _send_qbxml(qbxml)  # Dispatch request and parse response
    terms: List[PaymentTerm] = []  # Accumulate parsed terms here
    for term_ret in root.findall(".//StandardTermsRet"):  # Iterate over each term
        record_id = term_ret.findtext("StdDiscountDays")  # Use days as record_id
        name = (term_ret.findtext("Name") or "").strip()  # Normalise the name

        if not record_id:
            continue  # Skip entries without an ID
        try:
            record_id = str(
                int(record_id)
            )  # Coerce to int then back to str to normalise
        except ValueError:
            record_id = record_id.strip()  # Fallback: trim whitespace
        if not record_id:
            continue  # Skip empty IDs after normalisation

        due_days_text = term_ret.findtext("StdDueDays")
        try:
            due_days = int(due_days_text) if due_days_text is not None else None
        except ValueError:
            due_days = None

        terms.append(
            PaymentTerm(
                record_id=record_id,
                name=name,
                source="quickbooks",
                due_days=due_days,
            )
        )

    return terms  # Return all collected terms


def add_payment_terms_batch(
    company_file: str | None, terms: List[PaymentTerm]
) -> List[PaymentTerm]:
    """Create multiple payment terms in QuickBooks in a single batch request."""

    if not terms:
        return []  # Nothing to add; return early

    # Build the QBXML with multiple StandardTermsAddRq entries
    requests = []  # Collect individual add requests to embed in one batch
    for term in terms:
        try:
            days_value = int(term.record_id)  # QuickBooks expects a numeric days value
        except ValueError as exc:
            raise ValueError(
                f"record_id must be numeric for QuickBooks payment terms: {term.record_id}"
            ) from exc

        if term.due_days is None:
            due_days_value = days_value
        else:
            try:
                due_days_value = int(term.due_days)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"due_days must be numeric for QuickBooks payment terms: {term.due_days}"
                ) from exc

        # Build the QBXML snippet for this term creation
        requests.append(
            f"    <StandardTermsAddRq>\n"
            f"      <StandardTermsAdd>\n"
            f"        <Name>{_escape_xml(term.name)}</Name>\n"
            f"        <StdDiscountDays>{days_value}</StdDiscountDays>\n"
            f"        <StdDueDays>{due_days_value}</StdDueDays>\n"
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
    )  # Batch request enabling partial success on errors

    try:
        root = _send_qbxml(qbxml)  # Submit the batch to QuickBooks
    except RuntimeError as exc:
        # If the entire batch fails, return empty list
        print(f"Batch add failed: {exc}")
        return []

    # Parse all responses
    added_terms: List[PaymentTerm] = []  # Terms confirmed/returned by QuickBooks
    for term_ret in root.findall(".//StandardTermsRet"):
        record_id = term_ret.findtext("StdDiscountDays")  # Extract the ID
        if not record_id:
            continue
        try:
            record_id = str(int(record_id))  # Normalise numeric string
        except ValueError:
            record_id = record_id.strip()
        name = (term_ret.findtext("Name") or "").strip()  # Extract and trim name
        due_days_text = term_ret.findtext("StdDueDays")
        try:
            due_days = int(due_days_text) if due_days_text is not None else None
        except ValueError:
            due_days = None
        added_terms.append(
            PaymentTerm(
                record_id=record_id,
                name=name,
                source="quickbooks",
                due_days=due_days,
            )
        )

    return added_terms  # Return all terms that were added/acknowledged


def _escape_xml(value: str) -> str:
    """Escape XML special characters for safe QBXML construction."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


__all__ = [
    "fetch_payment_terms",
    "add_payment_terms_batch",
]  # Public API
