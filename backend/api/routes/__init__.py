from fastapi import APIRouter

from api.routes.analysis import router as analysis_router
from api.routes.applications import router as applications_router
from api.routes.auth import router as auth_router
from api.routes.bds import router as bds_router
from api.routes.clients import router as clients_router
from api.routes.health import router as health_router
from api.routes.jobs import router as jobs_router
from api.routes.market_research import router as market_research_router
from api.routes.profiles import router as profiles_router
from api.routes.scrape import router as scrape_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(bds_router, tags=["business-developers"])
api_router.include_router(clients_router, tags=["clients"])
api_router.include_router(profiles_router, tags=["profiles"])
api_router.include_router(scrape_router, tags=["scrape"])
api_router.include_router(jobs_router, tags=["jobs"])
api_router.include_router(analysis_router, tags=["analysis"])
api_router.include_router(applications_router, tags=["applications"])
api_router.include_router(market_research_router, tags=["market-research"])
