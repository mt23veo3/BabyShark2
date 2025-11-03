from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from services.constants import API_KEY

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Cho phép docs, openapi, redoc, root và health check không cần API key
        if request.url.path in ["/docs", "/openapi.json", "/redoc", "/", "/api/health"]:
            return await call_next(request)
        api_key = request.headers.get("x-api-key")
        if api_key != API_KEY:
            print(f"APIKeyMiddleware: 401 Unauthorized for path {request.url.path} with header x-api-key={api_key}")
            raise HTTPException(status_code=401, detail="Invalid or missing API Key")
        return await call_next(request)