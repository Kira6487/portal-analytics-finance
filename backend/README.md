# Backend

API FastAPI de solo lectura para la Fase 1 de Analytics Finance SAP B1.

Desde esta carpeta:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

El script de diagnóstico se ejecuta desde la raíz del repositorio:

```powershell
python backend/scripts/test_connection.py
```

