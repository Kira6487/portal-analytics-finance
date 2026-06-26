from __future__ import annotations


SCENARIOS = ("base", "optimistic", "pessimistic")
HORIZON_WEEKS = (4, 8, 13, 26)

REPORTING_CURRENCY_NAME = "Soles"

MANAGERIAL_LIMITATIONS = [
    "Es una vista gerencial y no reemplaza el Balance oficial de SAP.",
    "No crea asientos contables.",
    "No modifica SAP.",
    "Depende de supuestos de cobranza, pagos y forecast.",
    "Debe validarse con Contabilidad y Tesoreria.",
    "Otros activos, otros pasivos y patrimonio se mantienen constantes en esta demo.",
    "Documentos en moneda fuente distinta de SOL requieren politica FX productiva.",
]
