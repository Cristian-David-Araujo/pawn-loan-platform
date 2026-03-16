from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.security import decode_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

SERVICE_MAP = {
    "auth": settings.IDENTITY_SERVICE_URL,
    "users": settings.IDENTITY_SERVICE_URL,
    "roles": settings.IDENTITY_SERVICE_URL,
    "customers": settings.CUSTOMER_SERVICE_URL,
    "loan-applications": settings.LOAN_SERVICE_URL,
    "loans": settings.LOAN_SERVICE_URL,
    "collateral-items": settings.COLLATERAL_SERVICE_URL,
    "interest": settings.FINANCE_SERVICE_URL,
    "penalties": settings.FINANCE_SERVICE_URL,
    "payments": settings.PAYMENT_SERVICE_URL,
    "reports": settings.REPORTING_SERVICE_URL,
}


async def proxy_request(request: Request, target_url: str) -> Response:
    headers = dict(request.headers)
    headers.pop("host", None)
    body = await request.body()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            params=dict(request.query_params),
        )
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.headers.get("content-type"),
    )


@router.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def gateway(path: str, request: Request):
    path_parts = path.strip("/").split("/")
    resource = path_parts[0] if path_parts else ""
    target_base = SERVICE_MAP.get(resource)
    if not target_base:
        raise HTTPException(status_code=404, detail=f"No service found for resource: {resource}")
    target_url = f"{target_base}/api/v1/{path}"
    return await proxy_request(request, target_url)
