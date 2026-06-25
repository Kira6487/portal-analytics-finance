from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[2]
OVERRIDES_PATH = BACKEND_DIR / "config" / "account_mapping_overrides.json"

FINANCIAL_GROUPS = (
    "Ingresos",
    "Costo de ventas",
    "Gastos operativos",
    "Gastos administrativos",
    "Gastos de ventas",
    "Gastos financieros",
    "Otros ingresos",
    "Otros gastos",
    "Activos",
    "Pasivos",
    "Patrimonio",
    "No clasificado",
)


@lru_cache
def load_overrides() -> dict[str, dict[str, str]]:
    if not OVERRIDES_PATH.exists():
        return {"accounts": {}, "prefixes": {}}
    try:
        data = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
        return {
            "accounts": data.get("accounts") or {},
            "prefixes": data.get("prefixes") or {},
        }
    except (OSError, json.JSONDecodeError):
        return {"accounts": {}, "prefixes": {}}


def classify_account(account: dict[str, Any]) -> dict[str, Any]:
    code = str(account.get("account_code") or "")
    visible = str(account.get("format_code") or code).replace("-", "").strip()
    name = str(account.get("account_name") or "")
    normalized = name.lower()
    mask = account.get("group_mask")
    act_type = str(account.get("act_type") or "").upper()
    overrides = load_overrides()

    if code in overrides["accounts"] or visible in overrides["accounts"]:
        group = overrides["accounts"].get(code, overrides["accounts"].get(visible))
        method, confidence = "manual_override", "high"
    else:
        group = None
        for prefix in sorted(overrides["prefixes"], key=len, reverse=True):
            if visible.startswith(prefix):
                group = overrides["prefixes"][prefix]
                method, confidence = "prefix_override", "high"
                break

    if group is None and mask in (1, 2, 3):
        group = {1: "Activos", 2: "Pasivos", 3: "Patrimonio"}[mask]
        method, confidence = "GroupMask", "high"
    elif group is None and mask == 4 and act_type == "I":
        group, method, confidence = "Ingresos", "GroupMask/ActType", "high"
    elif group is None and mask == 5:
        if visible.startswith("69") or "costo de venta" in normalized:
            group, confidence = "Costo de ventas", "high"
        else:
            group, confidence = "Costo de ventas", "medium"
        method = "GroupMask/FormatCode"
    elif group is None and mask == 6:
        if visible.startswith("67") or any(
            word in normalized for word in ("interes", "financier", "diferencia de cambio")
        ):
            group = "Gastos financieros"
        elif visible.endswith("0094") or any(
            word in normalized for word in ("administracion", "(adm)")
        ):
            group = "Gastos administrativos"
        elif visible.endswith("0095") or any(
            word in normalized for word in ("comercial", "ventas", "(ven)")
        ):
            group = "Gastos de ventas"
        elif visible.startswith(("65", "66")):
            group = "Otros gastos"
        else:
            group = "Gastos operativos"
        method, confidence = "GroupMask/FormatCode/AcctName", "medium"
    elif group is None and mask == 7:
        group = "Otros ingresos" if act_type == "I" else "Otros gastos"
        method, confidence = "GroupMask/ActType", "medium"
    elif group is None:
        group, method, confidence = "No clasificado", "sin_regla", "low"

    return {
        "account_code": code,
        "format_code": visible,
        "account_name": name,
        "financial_group": group if group in FINANCIAL_GROUPS else "No clasificado",
        "classification_method": method,
        "confidence": confidence,
    }


def signed_amount(group: str, debit: float, credit: float) -> float:
    """Present income/liability/equity as credit-positive; others debit-positive."""
    if group in ("Ingresos", "Otros ingresos", "Pasivos", "Patrimonio"):
        return credit - debit
    return debit - credit
