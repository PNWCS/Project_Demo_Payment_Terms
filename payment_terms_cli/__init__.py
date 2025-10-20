"""Payment terms CLI toolkit.

Exposes the high-level ``run_payment_terms`` API for programmatic use.
"""

from .runner import run_payment_terms  # Public API for synchronisation

__all__ = ["run_payment_terms"]  # Re-exported symbol
