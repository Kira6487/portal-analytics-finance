REQUIRED_TABLES = (
    "OACT", "OJDT", "JDT1", "OCRD", "OINV", "INV1", "ORIN", "RIN1",
    "OPCH", "PCH1", "ORPC", "RPC1", "ORCT", "RCT2", "OVPM", "VPM2",
    "OCTG", "OPRC", "OBGT", "BGT1",
)

TABLES_SQL = """
SELECT UPPER(TABLE_NAME) AS table_name
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
  AND UPPER(TABLE_NAME) IN :table_names
"""

COLUMNS_SQL = """
SELECT COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE UPPER(TABLE_NAME) = :table_name
"""

ACCOUNTING_SQL = """
SELECT
    MIN(O.RefDate) AS min_date,
    MAX(O.RefDate) AS max_date,
    COUNT(DISTINCT O.TransId) AS total_journal_entries,
    COUNT_BIG(*) AS total_journal_lines,
    (SELECT COUNT_BIG(*) FROM OACT) AS total_accounts,
    COUNT(DISTINCT DATEFROMPARTS(YEAR(O.RefDate), MONTH(O.RefDate), 1))
        AS months_with_movements,
    COALESCE(SUM(CAST(J.Debit AS decimal(28, 6))), 0) AS total_debit,
    COALESCE(SUM(CAST(J.Credit AS decimal(28, 6))), 0) AS total_credit
FROM OJDT O
JOIN JDT1 J ON J.TransId = O.TransId
"""

MONTHLY_MOVEMENTS_SQL = """
SELECT
    DATEFROMPARTS(YEAR(O.RefDate), MONTH(O.RefDate), 1) AS month_start,
    SUM(ABS(COALESCE(J.Debit, 0)) + ABS(COALESCE(J.Credit, 0))) AS movement
FROM OJDT O
JOIN JDT1 J ON J.TransId = O.TransId
GROUP BY DATEFROMPARTS(YEAR(O.RefDate), MONTH(O.RefDate), 1)
ORDER BY month_start
"""

INCOME_ACCOUNTS_SQL = """
SELECT
    A.AcctCode,
    A.AcctName,
    A.GroupMask,
    A.ActType,
    COUNT_BIG(J.TransId) AS movements
FROM OACT A
LEFT JOIN JDT1 J ON J.Account = A.AcctCode
GROUP BY A.AcctCode, A.AcctName, A.GroupMask, A.ActType
"""

RECEIVABLES_SQL = """
SELECT
    COUNT_BIG(*) AS total_invoices,
    SUM(CASE WHEN DocStatus = 'O' THEN 1 ELSE 0 END) AS open_invoices,
    COALESCE(SUM(CASE WHEN DocStatus = 'O'
        THEN CAST(DocTotal - PaidToDate AS decimal(28, 6)) ELSE 0 END), 0)
        AS open_amount,
    COUNT(DISTINCT CardCode) AS customers,
    MIN(DocDate) AS min_invoice_date,
    MAX(DocDate) AS max_invoice_date,
    SUM(CASE WHEN DocDueDate IS NOT NULL THEN 1 ELSE 0 END) AS due_date_records
FROM OINV
WHERE CANCELED = 'N'
"""

PAYABLES_SQL = """
SELECT
    COUNT_BIG(*) AS total_vendor_bills,
    SUM(CASE WHEN DocStatus = 'O' THEN 1 ELSE 0 END) AS open_vendor_bills,
    COALESCE(SUM(CASE WHEN DocStatus = 'O'
        THEN CAST(DocTotal - PaidToDate AS decimal(28, 6)) ELSE 0 END), 0)
        AS open_amount,
    COUNT(DISTINCT CardCode) AS vendors,
    MIN(DocDate) AS min_bill_date,
    MAX(DocDate) AS max_bill_date,
    SUM(CASE WHEN DocDueDate IS NOT NULL THEN 1 ELSE 0 END) AS due_date_records
FROM OPCH
WHERE CANCELED = 'N'
"""

PAYMENT_COUNT_SQL = {
    "RCT2": "SELECT COUNT_BIG(*) AS records FROM RCT2",
    "VPM2": "SELECT COUNT_BIG(*) AS records FROM VPM2",
}

COST_CENTERS_SQL = "SELECT COUNT_BIG(*) AS records FROM OPRC"

BUDGET_COUNT_SQL = {
    "OBGT": "SELECT COUNT_BIG(*) AS records FROM OBGT",
    "BGT1": "SELECT COUNT_BIG(*) AS records FROM BGT1",
}

