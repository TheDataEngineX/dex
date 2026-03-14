---
applyTo: "src/**/api/**/*.py"
---

# FastAPI — Project Specifics

## Routing & Responses
- Versioned routes: `APIRouter(prefix="/api/v1", tags=["v1"])`
- Declare `response_model=` on every endpoint
- Pydantic models for all request/response shapes
- Custom `custom_openapi()` in main.py for schema customization

## Lifespan & Middleware
- `@asynccontextmanager` lifespan for startup/shutdown
- Middleware stack (order matters): request logging → metrics → auth → rate limit
- Uses `BaseHTTPMiddleware` (not `Depends()`) — keeps cross-cutting logic out of route signatures
- 3 global exception handlers: `RequestValidationError`, `StarletteHTTPException`, catch-all `Exception`
- Lazy imports inside route handlers (e.g., `PipelineConfig`) to avoid circular deps

## Project Map
- Entry: `examples/02_api_quickstart.py` (minimal working example)
- Auth: `src/dataenginex/api/auth.py` — pure-Python HS256 JWT (no pyjwt dependency)
- Health: `src/dataenginex/api/health.py` — TCP checks for DB, cache, external API
- Pagination: `src/dataenginex/api/pagination.py` (cursor-based, base64 opaque cursors)
- Rate limiting: `src/dataenginex/api/rate_limit.py` (token-bucket) | Errors: `src/dataenginex/api/errors.py`
- Metrics: `src/dataenginex/middleware/metrics.py` (`http_requests_total`, `http_request_duration_seconds`)

## Local Dev
- `poe dev` → runs `examples/02_api_quickstart.py` on port 8000
- Docs: `http://localhost:8000/docs`
