from fastapi import APIRouter

from src.modules.authentication.router import router as auth_router
from src.modules.collateral.router import router as collateral_router
from src.modules.customers.router import router as customers_router
from src.modules.finance.router import router as finance_router
from src.modules.loans.router import router as loans_router
from src.modules.payments.router import router as payments_router
from src.modules.reporting.router import router as reporting_router
from src.modules.settings.router import router as settings_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(customers_router)
api_router.include_router(loans_router)
api_router.include_router(collateral_router)
api_router.include_router(payments_router)
api_router.include_router(finance_router)
api_router.include_router(reporting_router)
api_router.include_router(settings_router)
