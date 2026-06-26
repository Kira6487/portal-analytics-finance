from __future__ import annotations

from datetime import date, timedelta


def estimate_payment_date(
    *,
    due_date: date,
    as_of_date: date,
    vendor_median_payment_delay_days: int,
    has_history: bool,
    scenario: str,
) -> date:
    delay = vendor_median_payment_delay_days if has_history else 0
    base = due_date + timedelta(days=delay)
    if due_date <= as_of_date:
        return as_of_date
    if scenario == "optimistic":
        return max(as_of_date, due_date)
    if scenario == "pessimistic":
        return max(as_of_date, base)
    return max(as_of_date, base)


def recommend_payment_date(
    *,
    due_date: date,
    as_of_date: date,
    estimated_payment_date: date,
    days_overdue: int,
    days_until_due: int,
    priority_level: str,
    in_deficit_week: bool,
) -> tuple[date, str]:
    if days_overdue > 0:
        return as_of_date, "Documento vencido; recomendar gestion inmediata con Tesoreria."
    if priority_level == "urgent":
        return min(due_date, estimated_payment_date), "Prioridad urgente; revisar pago inmediato."
    if days_until_due <= 7:
        return due_date, "Documento vence en los proximos 7 dias; recomendar pago al vencimiento."
    if in_deficit_week:
        return due_date, "Pago cae en semana de presion de caja; revisar posible negociacion."
    return estimated_payment_date, "Fecha sugerida segun vencimiento e historial del proveedor."
