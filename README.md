# SOC-Lite · Triaje automático de alertas SOC

Implementación de referencia del caso **SOC-Lite** (triaje automático de alertas con
orquestación low-code + razonamiento LLM) para PYME, mediana empresa y organismo público.

## Componentes

| Componente | Ruta | Tecnología |
|---|---|---|
| Esquema y datos semilla | `db/` | PostgreSQL 16, pgcrypto, pg_trgm |
| API + RBAC + reportes | `backend/` | FastAPI, SQLAlchemy 2 async, ReportLab, python-docx, XlsxWriter |
| Triaje LLM | `ai-service/` | LangChain, Ollama (llama3.1:8b), FastAPI |
| Interfaz | `frontend/` | React 18, TypeScript, Vite, TanStack Query, Recharts, Tailwind |
| Orquestación | `workflows/soc_lite_triage.json` | n8n (importable) |
| Stack completo | `docker-compose.yml` | Docker Compose |

## Arranque rápido

```bash
cp .env.example .env          # cambie JWT_SECRET y las claves de API
docker compose up -d --build
docker compose exec ollama ollama pull llama3.1:8b-instruct-q4_K_M
```

- Interfaz: <http://localhost:8080>
- API y Swagger: <http://localhost:8000/docs>
- n8n: <http://localhost:5678>
- Servicio de triaje: <http://localhost:8081/health>

Importe `workflows/soc_lite_triage.json` en n8n y configure las credenciales
`SOC-Lite PostgreSQL`, `SOC-Lite AI Service Token`, `SOC-Lite Slack` y `osTicket API`.

## Usuarios de demostración

| Correo | Rol | Contraseña |
|---|---|---|
| admin@soclite.local | Administrador | `SocLite#2026!` |
| gerente.soc@soclite.local | Jefe de SOC | `SocLite#2026!` |
| analista1@soclite.local | Analista | `SocLite#2026!` |
| analista2@soclite.local | Analista | `SocLite#2026!` |
| auditor@soclite.local | Auditor (solo lectura) | `SocLite#2026!` |
| directivo@soclite.local | Consulta | `SocLite#2026!` |

Los hashes se generan en PostgreSQL con `crypt(..., gen_salt('bf', 12))`; no hay
contraseñas en claro persistidas.

## Estructura de la API

```
POST /api/v1/auth/login              → tokens (access 15 min + refresh rotatorio)
GET  /api/v1/auth/me                 → perfil y permisos efectivos
GET  /api/v1/alerts                  → bandeja con filtros y paginación
GET  /api/v1/alerts/{id}             → detalle + triaje + enriquecimiento
POST /api/v1/alerts/{id}/triage      → triaje IA (idempotente con ?force=true)
POST /api/v1/alerts/{id}/review      → validación humana del veredicto
POST /api/v1/alerts/{id}/escalate    → apertura de incidente con SLA
GET  /api/v1/dashboard               → KPIs y series del panel
POST /api/v1/reports                 → genera PDF / DOCX / XLSX
GET  /api/v1/reports/{id}/download   → descarga auditada
GET  /api/v1/audit                   → bitácora paginada
GET  /api/v1/audit/verify            → verificación de la cadena SHA-256
```

## Pruebas

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

## Notas de seguridad

- RBAC verificado en cada request contra la base de datos (no se confía en el rol del JWT).
- Bitácora append-only con trigger de inmutabilidad y encadenamiento SHA-256.
- Bloqueo de cuenta tras 5 intentos fallidos y rotación de refresh tokens.
- Inferencia local con Ollama por defecto: las alertas no salen de la infraestructura.
- Reportes con checksum SHA-256 registrado en la tabla `reports`.

## Licencia

Uso académico · VIII Ciclo · Ingeniería de Software II.
