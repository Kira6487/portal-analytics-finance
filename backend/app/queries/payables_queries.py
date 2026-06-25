OPEN_PAYABLES_SQL = """
SELECT
    I.DocEntry AS doc_entry,
    I.CardCode AS partner_code,
    I.CardName AS partner_name,
    I.DocNum AS document_number,
    I.DocDate AS document_date,
    I.DocDueDate AS due_date,
    I.DocCur AS currency,
    CAST(I.DocTotal AS decimal(28, 6)) AS document_total,
    CAST(I.PaidToDate AS decimal(28, 6)) AS paid_amount,
    CAST(I.DocTotal - I.PaidToDate AS decimal(28, 6)) AS open_amount
FROM OPCH I
WHERE I.CANCELED = 'N'
  AND I.DocStatus = 'O'
  AND I.DocDate <= :as_of_date
  AND (I.DocTotal - I.PaidToDate) > 0.005
ORDER BY I.DocDueDate, I.CardCode, I.DocNum
"""
