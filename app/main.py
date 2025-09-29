# Health endpoint toggle
ENABLE_HEALTH_ENDPOINT = os.getenv("ENABLE_HEALTH_ENDPOINT", "true").lower() == "true"

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.routing import APIRouter
import logging
import asyncio
import time
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from .routes.chat import router as chat_router
from .routes.token import router as token_router
from .utils.logger import setup_logging
from .services.request_queue import request_queue
from .services.emotion_classifier import emotion_classifier
from .services.llm_service import llm_service
from .services.user_limiter import user_limiter

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()

# Get environment settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
	env_emoji = "🏭" if IS_PRODUCTION else "🔧"
	logging.info(f"{env_emoji} AI Chatbot Platform API starting up in {ENVIRONMENT} mode...")
	logging.info("📊 NO QUEUE MODE: Direct OpenRouter execution for maximum speed!")
	logging.info("🎯 User limits: 3 prompts per user per day")
	yield
	logging.info("🛑 AI Chatbot Platform API shutting down...")

app = FastAPI(
	title="AI Chatbot Platform",
	description="An empathetic AI chatbot that responds based on user emotions with improved load handling",
	version="1.1.0",
	lifespan=lifespan
)

# Add GZip
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configure CORS
laptop_server_mode = os.getenv("LAPTOP_SERVER_MODE", "false").lower() == "true"

if laptop_server_mode:
	allowed_origins = [
		os.getenv("FRONTEND_URL", "https://educhat.smkn21jakarta.sch.id"),
		"https://educhat.smkn21jakarta.sch.id",
		"*"
	]
	logging.info("🖥️ Laptop Server Mode: Permissive CORS")
elif IS_PRODUCTION:
	allowed_origins = [
		os.getenv("FRONTEND_URL", "https://educhat.smkn21jakarta.sch.id"),
		"https://www.educhat.smkn21jakarta.sch.id",
	]
	extra_origins = os.getenv("EXTRA_CORS_ORIGINS", "").split(",")
	allowed_origins.extend([origin.strip() for origin in extra_origins if origin.strip()])
else:
	allowed_origins = [
		"http://localhost:3000",
		"http://127.0.0.1:3000",
		"http://localhost:3001",
		"https://localhost:3000",
		"*"
	]
	logging.info("🔧 Dev mode: Permissive CORS")

logging.info(f"✅ Allowed Origins: {allowed_origins}")

app.add_middleware(
	CORSMiddleware,
	allow_origins=allowed_origins,
	allow_credentials=True,
	allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
	allow_headers=["*", "ngrok-skip-browser-warning"],
)


@app.get("/api/v1/stats")
async def get_api_stats():
	"""Get API and simplified stats for monitoring (for frontend health check)"""
	stats = request_queue.get_stats()
	return {
		"api_status": "active",
		"queue_mode": "minimal_throttling_no_queue",
		"statistics": stats,
		"performance": {
			"mode": stats.get("mode", "unknown"),
			"concurrent_limit": 50,  # Semaphore limit
			"designed_for": "36+ concurrent users",
			"expected_response_time": "2-5 seconds"
		},
		"system_health": {
			"emotion_classifier": "loaded" if emotion_classifier.clf is not None else "error",
			"llm_service": "active",
			"user_limiter": "active"
		},
		"user_limits": {
			"prompts_per_user": 3,
			"reset_period": "24 hours",
			"identification": "token-based"
		}
	}

# Explicit preflight OPTIONS handler
@app.options("/{full_path:path}")
async def preflight_handler(full_path: str, request: Request):
	logging.debug(f"Preflight request to {request.url}")
	return JSONResponse(
		status_code=200,
		content={"message": "Preflight OK"},
		headers={
			"Access-Control-Allow-Origin": request.headers.get("origin", "*"),
			"Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
			"Access-Control-Allow-Headers": "*, ngrok-skip-browser-warning",
		}
	)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
	error_id = int(time.time())
	logging.error(f"Global exception [{error_id}] on {request.url}: {exc}")

	if IS_PRODUCTION:
		return JSONResponse(
			status_code=500,
			content={
				"error": "Internal server error",
				"message": "The server encountered an error while processing your request",
				"type": "server_error",
				"error_id": error_id
			}
		)
	else:
		return JSONResponse(
			status_code=500,
			content={
				"error": "Internal server error",
				"message": str(exc),
				"type": "server_error",
				"error_id": error_id
			}
		)

# Timeout exception handler
@app.exception_handler(asyncio.TimeoutError)
async def timeout_exception_handler(request: Request, exc: asyncio.TimeoutError):
	logging.warning(f"Request timeout on {request.url}")
	return JSONResponse(
		status_code=504,
		content={
			"error": "Request timeout",
			"message": "The request took too long to process",
			"type": "timeout_error"
		}
	)

# Routers
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
app.include_router(token_router, prefix="/api/v1", tags=["token"])

@app.get("/")
async def root():
	return {
		"message": "Welcome to AI Chatbot Platform API",
		"version": "1.0.0",
		"endpoints": {
			"chat": "/api/v1/chat",
			"health": "/api/v1/health",
			"emotions": "/api/v1/emotions"
		}
	}


@app.get("/api/v1/health")
async def health_check():
	if not ENABLE_HEALTH_ENDPOINT:
		return JSONResponse(status_code=404, content={"error": "Health endpoint disabled"})
	stats = request_queue.get_stats()
	return {
		"status": "healthy",
		"timestamp": time.time(),
		"queue_stats": stats,
		"server": "running"
	}

@app.get("/api/v1/queue/stats")
async def get_queue_stats():
	return request_queue.get_stats()
# Copy of backend main.py for Railway
