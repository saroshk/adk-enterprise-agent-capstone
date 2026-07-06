"""D365 F&O stub MCP server (read-only).

Serves vendor, invoice and purchase-order data from local JSON files shaped like
Dynamics 365 F&O OData responses. To go live later, replace the `_load` helper
with real OData calls; the tool signatures stay the same.

Security note: this server exposes READ tools only. There is no write/approve
path to ERP by design.
"""
import json
import os
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

DATA_DIR = Path(
    os.environ.get("ERP_DATA_DIR", Path(__file__).parent.parent / "seed-data" / "erp")
)

mcp = FastMCP("d365-erp")


def _load(name: str) -> list[dict]:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)["value"]


def _resolve_vendor(vendor: str) -> Optional[dict]:
    q = vendor.strip().lower()
    for row in _load("vendors.json"):
        if row["VendorAccountNumber"].lower() == q or q in row["VendorName"].lower():
            return row
    return None


@mcp.tool()
def find_vendor(name: str) -> list[dict]:
    """Look up vendors by name or account number (case-insensitive, partial match)."""
    q = name.strip().lower()
    return [
        r for r in _load("vendors.json")
        if q in r["VendorName"].lower() or q == r["VendorAccountNumber"].lower()
    ]


@mcp.tool()
def get_vendor_invoices(vendor: str, status: Optional[str] = None) -> list[dict]:
    """Return invoices for a vendor (by name or account number).

    status: optional filter such as "Open" or "Paid". Omit to return all invoices.
    """
    row = _resolve_vendor(vendor)
    if not row:
        return []
    account = row["VendorAccountNumber"]
    invoices = [r for r in _load("vendor_invoices.json") if r["InvoiceAccount"] == account]
    if status:
        s = status.strip().lower()
        invoices = [r for r in invoices if r["InvoiceStatus"].lower() == s]
    return invoices


@mcp.tool()
def get_purchase_order(po_number: str) -> Optional[dict]:
    """Return a single purchase order by number, or null if not found."""
    q = po_number.strip().lower()
    for r in _load("purchase_orders.json"):
        if r["PurchaseOrderNumber"].lower() == q:
            return r
    return None


@mcp.tool()
def get_invoice(invoice_number: str) -> Optional[dict]:
    """Return a single invoice by its invoice number, or null if not found."""
    q = invoice_number.strip().lower()
    for r in _load("vendor_invoices.json"):
        if r["InvoiceNumber"].lower() == q:
            return r
    return None

if __name__ == "__main__":
    mcp.run()
