"""
Policy Compliance Check Script
Part of the policy-compliance-check Skill.

Deterministically evaluates a vendor invoice against the Procurement & Invoice
Approval Policy (POL-PROC-002). Returns a structured verdict as JSON.

Usage:
    python check_invoice.py --amount 12500 --po None --terms Net45
    python check_invoice.py --amount 6000 --po PO-6001 --terms Net30
"""

import argparse
import json


POLICY_ID = "POL-PROC-002"
PO_REQUIRED_THRESHOLD_USD = 10000.0
ALLOWED_TERMS_DEFAULT = "Net30"


def check_compliance(amount: float, po_number: str, payment_terms: str) -> dict:
    """
    Applies the procurement policy rules and returns a structured verdict.
    """
    violations = []

    # Rule 1: Invoices >= 10,000 USD must reference a purchase order.
    if amount >= PO_REQUIRED_THRESHOLD_USD:
        if not po_number or po_number.lower() in ("none", "null", ""):
            violations.append(
                f"Invoices of USD {PO_REQUIRED_THRESHOLD_USD:,.0f} or more must reference "
                f"an approved purchase order (invoice amount was USD {amount:,.2f}, no PO provided)."
            )

    # Rule 2: Payment terms should be Net30 unless approved otherwise.
    terms_note = None
    if payment_terms and payment_terms.lower() != ALLOWED_TERMS_DEFAULT.lower():
        terms_note = (
            f"Payment terms '{payment_terms}' deviate from default '{ALLOWED_TERMS_DEFAULT}'. "
            f"Verify with vendor master for approved exception."
        )

    if violations:
        return {
            "status": "VIOLATION",
            "rule_broken": " | ".join(violations),
            "cited_policy": POLICY_ID,
            "recommended_action": "FLAG FOR HUMAN REVIEW",
            "terms_note": terms_note,
        }
    else:
        return {
            "status": "COMPLIANT",
            "rule_broken": None,
            "cited_policy": POLICY_ID,
            "recommended_action": "AUTO-APPROVE PENDING HUMAN CONFIRMATION",
            "terms_note": terms_note,
        }


def main():
    parser = argparse.ArgumentParser(description="Procurement policy compliance check.")
    parser.add_argument("--amount", type=float, required=True, help="Invoice amount in USD.")
    parser.add_argument("--po", type=str, default="None", help="Purchase order number (or 'None').")
    parser.add_argument("--terms", type=str, default="Net30", help="Payment terms (e.g. Net30).")
    args = parser.parse_args()

    verdict = check_compliance(args.amount, args.po, args.terms)
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()