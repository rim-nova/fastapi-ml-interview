"""
Custom middleware for request logging and rate limiting.
"""
import time
import logging
from collections import defaultdict
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all incoming requests with timing information."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        
        # Generate request ID
        request_id = f"{time.time_ns()}"
        request.state.request_id = request_id
        
        # Log request
        logger.info(
            f"Request started | ID: {request_id} | "
            f"Method: {request.method} | Path: {request.url.path} | "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.perf_counter() - start_time
            
            # Log response
            logger.info(
                f"Request completed | ID: {request_id} | "
                f"Status: {response.status_code} | "
                f"Duration: {duration:.4f}s"
            )
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{duration:.4f}"
            
            return response
            
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(
                f"Request failed | ID: {request_id} | "
                f"Error: {str(e)} | Duration: {duration:.4f}s"
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    For production, use Redis-based rate limiting.
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_window: int | None = None,
        window_seconds: int = 60,
        exclude_paths: list[str] | None = None
    ):
        super().__init__(app)
        # Support both parameter styles
        self.window_seconds = window_seconds
        self.requests_limit = requests_per_window if requests_per_window else requests_per_minute
        self.exclude_paths = exclude_paths or ["/health", "/api/v1/health"]
        self.requests: dict[str, list[float]] = defaultdict(list)
    
    def _clean_old_requests(self, client_id: str, current_time: float) -> None:
        """Remove requests older than the window."""
        cutoff = current_time - self.window_seconds
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff
        ]
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier."""
        # Use X-Forwarded-For for proxied requests, fallback to client IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        # Clean old requests
        self._clean_old_requests(client_id, current_time)
        
        # Check rate limit
        if len(self.requests[client_id]) >= self.requests_limit:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": self.window_seconds
                },
                headers={"Retry-After": str(self.window_seconds)}
            )
        
        # Record this request
        self.requests[client_id].append(current_time)
        
        # Add rate limit headers to response
        response = await call_next(request)
        remaining = self.requests_limit - len(self.requests[client_id])
        response.headers["X-RateLimit-Limit"] = str(self.requests_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
