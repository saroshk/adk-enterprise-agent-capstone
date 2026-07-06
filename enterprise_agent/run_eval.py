"""Local evaluation for the enterprise capstone (data/tool layer).

This is a fast, model-free regression check: it verifies the MCP servers + seed data
still produce the exact facts the demo scenarios depend on. It needs NO API key and NO
quota -- it runs the same tool logic the agents call and asserts the ground-truth answers.

Run from the folder containing this file and the two *_server.py files:
    python run_eval.py

For the full AGENT-level evaluation (does the LLM produce the right answer end-to-end),
use the ADK "Evals" tab in `adk web`, or `adk eval`, driven by eval_cases.json.
"""
import sys

import erp_server as erp
import sharepoint_server as sp

PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, condition, detail=""):
    results.append((PASS if condition else FAIL, name, detail))


# S1 - Contoso open invoice total must be 25,450 (excludes the Paid invoice)
inv = erp.get_vendor_invoices("Contoso", "Open")
total = sum(r["InvoiceAmount"] for r in inv)
check("S1 Contoso open total == 25450", total == 25450.0, f"got {total}")
check("S1 excludes Paid INV-1000", all(r["InvoiceNumber"] != "INV-1000" for r in inv))

# S3 - INV-1003 must be the >=10k, no-PO violation
inv1003 = next((r for r in erp.get_vendor_invoices("Contoso") if r["InvoiceNumber"] == "INV-1003"), None)
check("S3 INV-1003 exists", inv1003 is not None)
check("S3 INV-1003 >= 10000", inv1003 and inv1003["InvoiceAmount"] >= 10000)
check("S3 INV-1003 has no PO", inv1003 and not inv1003["PurchaseOrderNumber"])
# Contrast case: Fabrikam INV-2002 is large but compliant (has a PO)
inv2002 = next((r for r in erp.get_vendor_invoices("Fabrikam") if r["InvoiceNumber"] == "INV-2002"), None)
check("S3 Fabrikam INV-2002 is compliant contrast (>=10k WITH PO)",
      inv2002 and inv2002["InvoiceAmount"] >= 10000 and inv2002["PurchaseOrderNumber"])

# S2 - return policy resolves to POL-RET-004 with a 30-day window
ret = sp.search_documents("supplier return window")
check("S2 return policy top hit is POL-RET-004", ret and ret[0]["document_id"] == "POL-RET-004")
ret_doc = sp.get_document("POL-RET-004")
check("S2 return window says 30 days", ret_doc and "30 days" in ret_doc["text"])

# S3 - procurement policy resolves to POL-PROC-002 with the PO rule
proc = sp.get_document("POL-PROC-002")
check("S3 procurement policy exists (POL-PROC-002)", proc is not None)
check("S3 policy states the 10,000 PO rule", proc and "10,000" in proc["text"])

# Security - the FAQ contains the injection payload (so the demo has something to resist)
faq = sp.get_document("FAQ-VEN-009")
check("SEC FAQ exists (FAQ-VEN-009)", faq is not None)
check("SEC FAQ contains injection payload", faq and "ignore all previous instructions" in faq["text"].lower())
check("SEC FAQ real answer is 3 business days", faq and "three business days" in faq["text"])
# Read-only surface: the ERP server must expose no write/approve tool
erp_tools = [n for n in dir(erp) if not n.startswith("_")]
write_words = ("approve", "create", "update", "delete", "pay", "post")
has_write = any(any(w in t.lower() for w in write_words) for t in erp_tools)
check("SEC ERP tool surface is read-only (no write tool)", not has_write)

# --- report ---
print("\nEnterprise capstone -- local data/tool eval\n" + "-" * 44)
npass = sum(1 for r in results if r[0] == PASS)
for status, name, detail in results:
    line = f"[{status}] {name}"
    if status == FAIL and detail:
        line += f"  ({detail})"
    print(line)
print("-" * 44)
print(f"{npass}/{len(results)} checks passed")
sys.exit(0 if npass == len(results) else 1)
