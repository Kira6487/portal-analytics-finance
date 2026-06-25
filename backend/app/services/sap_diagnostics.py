from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import math
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import DatabaseConnectionError, get_connection
from app.queries import diagnostic_queries as queries


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _row_dict(row: Any) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in dict(row).items()}


def _query_one(
    connection: Connection, sql: str, params: dict | None = None
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        row = connection.execute(text(sql), params or {}).mappings().first()
        return (_row_dict(row) if row else None), None
    except SQLAlchemyError as exc:
        return None, str(exc.orig if getattr(exc, "orig", None) else exc)


def _query_all(
    connection: Connection, sql: str, params: dict | None = None
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        rows = connection.execute(text(sql), params or {}).mappings().all()
        return [_row_dict(row) for row in rows], None
    except SQLAlchemyError as exc:
        return [], str(exc.orig if getattr(exc, "orig", None) else exc)


def _table_map(connection: Connection) -> tuple[dict[str, bool], list[str]]:
    statement = text(queries.TABLES_SQL).bindparams(
        bindparam("table_names", expanding=True)
    )
    try:
        rows = connection.execute(
            statement, {"table_names": list(queries.REQUIRED_TABLES)}
        ).mappings()
        found = {row["table_name"].upper() for row in rows}
        return {
            table: table in found for table in queries.REQUIRED_TABLES
        }, []
    except SQLAlchemyError as exc:
        return (
            {table: False for table in queries.REQUIRED_TABLES},
            [f"No se pudo consultar INFORMATION_SCHEMA.TABLES: {exc}"],
        )


def _columns(connection: Connection, table_name: str) -> set[str]:
    rows, _ = _query_all(
        connection, queries.COLUMNS_SQL, {"table_name": table_name.upper()}
    )
    return {row["COLUMN_NAME"] for row in rows}


def _accounting(connection: Connection, tables: dict[str, bool]) -> dict:
    result = {
        "min_date": None,
        "max_date": None,
        "total_journal_entries": 0,
        "total_journal_lines": 0,
        "total_accounts": 0,
        "available_months": 0,
        "available_years": 0,
        "months_with_movements": 0,
        "total_debit": 0.0,
        "total_credit": 0.0,
        "debit_credit_difference": 0.0,
        "warnings": [],
    }
    missing = [table for table in ("OJDT", "JDT1", "OACT") if not tables[table]]
    if missing:
        result["warnings"].append(
            f"No se puede completar el diagnóstico contable; faltan: {', '.join(missing)}."
        )
        return result

    row, error = _query_one(connection, queries.ACCOUNTING_SQL)
    if error or not row:
        result["warnings"].append(f"Falló la consulta contable: {error}")
        return result

    result.update(row)
    if row["min_date"] and row["max_date"]:
        start = date.fromisoformat(row["min_date"])
        end = date.fromisoformat(row["max_date"])
        result["available_months"] = (
            (end.year - start.year) * 12 + end.month - start.month + 1
        )
        result["available_years"] = len(
            range(start.year, end.year + 1)
        )
    difference = float(result["total_debit"] or 0) - float(result["total_credit"] or 0)
    result["debit_credit_difference"] = round(difference, 6)
    tolerance = max(0.01, max(abs(float(result["total_debit"] or 0)), 1) * 1e-8)
    if abs(difference) > tolerance:
        result["warnings"].append(
            "Los débitos y créditos no cuadran dentro de la tolerancia del diagnóstico."
        )
    if result["months_with_movements"] < result["available_months"]:
        result["warnings"].append(
            "Existen meses calendario sin movimientos contables."
        )
    return result


def _income_statement(
    connection: Connection, tables: dict[str, bool], accounting: dict
) -> dict:
    result = {
        "can_build": False,
        "revenue_accounts_detected": 0,
        "cost_accounts_detected": 0,
        "expense_accounts_detected": 0,
        "months_with_movements": accounting["months_with_movements"],
        "classification_method": None,
        "warnings": [],
    }
    if not tables["OACT"] or not tables["JDT1"]:
        result["warnings"].append("Faltan OACT o JDT1.")
        return result

    columns = _columns(connection, "OACT")
    required = {"AcctCode", "AcctName", "GroupMask", "ActType"}
    if not required.issubset(columns):
        result["warnings"].append(
            "OACT no contiene todos los campos esperados para clasificación."
        )
        return result

    rows, error = _query_all(connection, queries.INCOME_ACCOUNTS_SQL)
    if error:
        result["warnings"].append(f"No se pudieron clasificar cuentas: {error}")
        return result

    def populated(row: dict) -> bool:
        return int(row.get("movements") or 0) > 0

    # SAP B1 commonly marks P&L accounts with ActType='I'/'E'.
    revenue = [
        row for row in rows
        if populated(row) and (
            str(row.get("ActType") or "").upper() == "I"
            or any(word in str(row.get("AcctName") or "").lower()
                   for word in ("ingreso", "venta", "revenue"))
        )
    ]
    expenses = [
        row for row in rows
        if populated(row) and (
            str(row.get("ActType") or "").upper() == "E"
            or any(word in str(row.get("AcctName") or "").lower()
                   for word in ("gasto", "expense"))
        )
    ]
    costs = [
        row for row in rows
        if populated(row) and any(
            word in str(row.get("AcctName") or "").lower()
            for word in ("costo", "coste", "cost of")
        )
    ]
    expense_codes = {row["AcctCode"] for row in expenses}
    result.update(
        {
            "can_build": bool(revenue) and bool(expenses or costs),
            "revenue_accounts_detected": len({r["AcctCode"] for r in revenue}),
            "cost_accounts_detected": len({r["AcctCode"] for r in costs}),
            "expense_accounts_detected": len(
                expense_codes - {r["AcctCode"] for r in costs}
            ),
            "classification_method": "ActType + palabras clave en AcctName",
        }
    )
    if not result["can_build"]:
        result["warnings"].append(
            "La clasificación automática no es concluyente; se requiere mapear el plan de cuentas."
        )
    else:
        result["warnings"].append(
            "La clasificación es preliminar y debe validarse con Contabilidad antes de Fase 2."
        )
    return result


def _receivables(connection: Connection, tables: dict[str, bool]) -> dict:
    result = {
        "total_invoices": 0,
        "open_invoices": 0,
        "open_amount": 0.0,
        "customers": 0,
        "min_invoice_date": None,
        "max_invoice_date": None,
        "has_due_dates": False,
        "has_payment_history": False,
        "can_estimate_collection_risk": False,
        "warnings": [],
    }
    if not tables["OINV"]:
        result["warnings"].append("No existe OINV.")
        return result
    row, error = _query_one(connection, queries.RECEIVABLES_SQL)
    if error or not row:
        result["warnings"].append(f"Falló el diagnóstico CxC: {error}")
        return result
    due_dates = int(row.pop("due_date_records") or 0)
    result.update(row)
    result["has_due_dates"] = due_dates > 0
    if tables["RCT2"]:
        payment, payment_error = _query_one(
            connection, queries.PAYMENT_COUNT_SQL["RCT2"]
        )
        result["has_payment_history"] = bool(
            payment and int(payment["records"] or 0) > 0
        )
        if payment_error:
            result["warnings"].append(f"No se pudo revisar RCT2: {payment_error}")
    else:
        result["warnings"].append("No existe RCT2 para vincular pagos recibidos.")
    result["can_estimate_collection_risk"] = (
        result["total_invoices"] > 0
        and result["has_due_dates"]
        and result["has_payment_history"]
    )
    if not result["can_estimate_collection_risk"]:
        result["warnings"].append(
            "El riesgo de cobranza se limitaría a reglas hasta completar historial."
        )
    return result


def _payables(connection: Connection, tables: dict[str, bool]) -> dict:
    result = {
        "total_vendor_bills": 0,
        "open_vendor_bills": 0,
        "open_amount": 0.0,
        "vendors": 0,
        "min_bill_date": None,
        "max_bill_date": None,
        "has_due_dates": False,
        "has_payment_history": False,
        "can_project_payments": False,
        "warnings": [],
    }
    if not tables["OPCH"]:
        result["warnings"].append("No existe OPCH.")
        return result
    row, error = _query_one(connection, queries.PAYABLES_SQL)
    if error or not row:
        result["warnings"].append(f"Falló el diagnóstico CxP: {error}")
        return result
    due_dates = int(row.pop("due_date_records") or 0)
    result.update(row)
    result["has_due_dates"] = due_dates > 0
    if tables["VPM2"]:
        payment, payment_error = _query_one(
            connection, queries.PAYMENT_COUNT_SQL["VPM2"]
        )
        result["has_payment_history"] = bool(
            payment and int(payment["records"] or 0) > 0
        )
        if payment_error:
            result["warnings"].append(f"No se pudo revisar VPM2: {payment_error}")
    else:
        result["warnings"].append("No existe VPM2 para vincular pagos efectuados.")
    result["can_project_payments"] = (
        result["total_vendor_bills"] > 0 and result["has_due_dates"]
    )
    if not result["has_payment_history"]:
        result["warnings"].append(
            "La proyección de pagos deberá comenzar con vencimientos y reglas."
        )
    return result


def _dimensions(connection: Connection, tables: dict[str, bool]) -> dict:
    result = {
        "has_cost_centers": False,
        "ocr_code_fields_detected": [],
        "cost_centers_count": 0,
        "dimensions_with_movements": [],
        "can_build_profitability_by_dimension": False,
        "warnings": [],
    }
    if not tables["JDT1"]:
        result["warnings"].append("No existe JDT1.")
        return result
    columns = _columns(connection, "JDT1")
    fields = [
        field for field in ("OcrCode", "OcrCode2", "OcrCode3", "OcrCode4", "OcrCode5")
        if field in columns
    ]
    result["ocr_code_fields_detected"] = fields
    if tables["OPRC"]:
        row, error = _query_one(connection, queries.COST_CENTERS_SQL)
        if row:
            result["cost_centers_count"] = int(row["records"] or 0)
        if error:
            result["warnings"].append(f"No se pudo contar OPRC: {error}")
    for field in fields:
        row, error = _query_one(
            connection,
            f"SELECT COUNT_BIG(*) AS records FROM JDT1 "
            f"WHERE NULLIF(LTRIM(RTRIM([{field}])), '') IS NOT NULL",
        )
        if row and int(row["records"] or 0) > 0:
            result["dimensions_with_movements"].append(field)
        if error:
            result["warnings"].append(f"No se pudo revisar {field}: {error}")
    result["has_cost_centers"] = result["cost_centers_count"] > 0
    result["can_build_profitability_by_dimension"] = bool(
        result["dimensions_with_movements"]
    )
    if not result["can_build_profitability_by_dimension"]:
        result["warnings"].append(
            "No se detectaron dimensiones con movimientos para rentabilidad."
        )
    return result


def _budget(connection: Connection, tables: dict[str, bool]) -> dict:
    result = {
        "has_budget": False,
        "budget_tables_detected": [],
        "budget_records": 0,
        "can_compare_real_vs_budget": False,
        "recommendation": (
            "Crear presupuesto simulado para la demo basado en promedio histórico "
            "+ ajuste porcentual."
        ),
        "warnings": [],
    }
    for table in ("OBGT", "BGT1"):
        if not tables[table]:
            continue
        result["budget_tables_detected"].append(table)
        row, error = _query_one(connection, queries.BUDGET_COUNT_SQL[table])
        if row:
            result["budget_records"] += int(row["records"] or 0)
        if error:
            result["warnings"].append(f"No se pudo contar {table}: {error}")
    result["has_budget"] = result["budget_records"] > 0
    result["can_compare_real_vs_budget"] = result["has_budget"]
    if result["has_budget"]:
        result["recommendation"] = (
            "Validar versiones, escenarios y distribución mensual del presupuesto "
            "antes de construir la comparación."
        )
    else:
        result["warnings"].append(
            "No se encontraron registros presupuestales utilizables."
        )
    return result


def _forecast(
    connection: Connection,
    tables: dict[str, bool],
    accounting: dict,
    budget: dict,
    dimensions: dict,
) -> dict:
    months = int(accounting["available_months"] or 0)
    active = int(accounting["months_with_movements"] or 0)
    if months < 12:
        level = "low"
        models = ["Media móvil", "Seasonal naive", "Reglas simples"]
    elif months <= 24:
        level = "medium"
        models = ["Exponential Smoothing", "Medias móviles", "Forecast simple"]
    else:
        level = "high"
        models = [
            "Holt-Winters",
            "SARIMA simple",
            "Gradient Boosting con variables de calendario",
        ]
    warnings: list[str] = []
    if months and active / months < 0.85:
        warnings.append("La serie presenta intermitencia: hay numerosos meses sin movimiento.")

    if tables["OJDT"] and tables["JDT1"]:
        movements, error = _query_all(connection, queries.MONTHLY_MOVEMENTS_SQL)
        values = [float(row["movement"] or 0) for row in movements]
        if len(values) >= 6:
            mean = sum(values) / len(values)
            variance = sum((value - mean) ** 2 for value in values) / len(values)
            cv = math.sqrt(variance) / mean if mean else 0
            if cv > 1:
                warnings.append(
                    "Los movimientos mensuales tienen alta volatilidad; la confianza inicial será baja."
                )
        if error:
            warnings.append(f"No se pudo evaluar volatilidad: {error}")
    if not budget["has_budget"]:
        warnings.append("Real vs Presupuesto requerirá presupuesto simulado en la demo.")
    if not dimensions["can_build_profitability_by_dimension"]:
        warnings.append("Rentabilidad por dimensión no está lista con los datos detectados.")

    conclusion = {
        "low": "Datos insuficientes para modelos estacionales robustos; iniciar con reglas y baselines.",
        "medium": "Viabilidad intermedia; usar modelos simples y backtesting conservador.",
        "high": "Cobertura histórica adecuada para comparar modelos explicables mediante backtesting.",
    }[level]
    return {
        "available_months": months,
        "readiness_level": level,
        "recommended_models": models,
        "receivables_models": [
            "Reglas de atraso por cliente",
            "Promedio histórico",
            "Regresión de días de atraso si el historial es suficiente",
        ],
        "payables_models": [
            "Reglas por vencimiento",
            "Recurrencia",
            "Historial de pagos",
        ],
        "warnings": warnings,
        "general_conclusion": conclusion,
    }


def run_sap_diagnostics() -> dict[str, Any]:
    try:
        with get_connection() as connection:
            tables, table_warnings = _table_map(connection)
            accounting = _accounting(connection, tables)
            income = _income_statement(connection, tables, accounting)
            receivables = _receivables(connection, tables)
            payables = _payables(connection, tables)
            dimensions = _dimensions(connection, tables)
            budget = _budget(connection, tables)
            forecast = _forecast(
                connection, tables, accounting, budget, dimensions
            )
    except DatabaseConnectionError as exc:
        return {
            "status": "error",
            "database_connection": False,
            "message": str(exc),
            "limitations": ["No se pudo ejecutar el diagnóstico sin conexión."],
            "summary": {
                "status": "insufficient",
                "main_strengths": [],
                "main_limitations": ["Conexión SQL Server no disponible."],
                "next_recommended_phase": "Resolver conexión y repetir Fase 1",
            },
        }

    all_warnings = (
        table_warnings
        + accounting["warnings"]
        + income["warnings"]
        + receivables["warnings"]
        + payables["warnings"]
        + dimensions["warnings"]
        + budget["warnings"]
        + forecast["warnings"]
    )
    strengths = []
    if accounting["months_with_movements"]:
        strengths.append(
            f"Historial contable con {accounting['months_with_movements']} meses con movimientos."
        )
    if receivables["can_estimate_collection_risk"]:
        strengths.append("CxC contiene vencimientos e historial de pagos.")
    if payables["can_project_payments"]:
        strengths.append("CxP contiene documentos y vencimientos proyectables.")
    if dimensions["can_build_profitability_by_dimension"]:
        strengths.append("Existen dimensiones contables con movimientos.")
    if budget["has_budget"]:
        strengths.append("Se detectaron datos de presupuesto.")

    core_ready = income["can_build"] and accounting["months_with_movements"] > 0
    status = "ready" if core_ready and len(all_warnings) <= 3 else "partial"
    if not accounting["months_with_movements"]:
        status = "insufficient"

    return {
        "status": "ok",
        "database_connection": True,
        "tables": tables,
        "accounting_data": accounting,
        "income_statement_readiness": income,
        "receivables_data": receivables,
        "payables_data": payables,
        "dimensions_data": dimensions,
        "budget_data": budget,
        "forecast_readiness": forecast,
        "limitations": list(dict.fromkeys(all_warnings)),
        "recommendation": (
            "Continuar con Fase 2 únicamente después de validar el mapeo del plan "
            "de cuentas y las limitaciones documentadas."
        ),
        "summary": {
            "status": status,
            "main_strengths": strengths,
            "main_limitations": list(dict.fromkeys(all_warnings))[:10],
            "next_recommended_phase": "Fase 2 - Construcción del motor financiero base",
        },
    }

