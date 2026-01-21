from fastapi import Request, HTTPException
from collections import defaultdict
import time
from app.core.config import settings

# In-Memory Storage (Use Redis in production)
# Structure: {ip_address: [timestamp1, timestamp2, ...]}
request_history = defaultdict(list)


async def rate_limiter(request: Request):
    """
    Rate Limit Dependency: 5 requests / 60 seconds per IP.
    Returns 429 if exceeded.
    """
    client_ip = request.client.host
    now = time.time()

    # Get history and clean up old requests (>60s ago)
    history = request_history[client_ip]
    valid_window = [t for t in history if now - t < 60]

    # Check Limit
    if len(valid_window) >= settings.RATE_LIMIT_PER_MINUTE:
        wait_time = int(60 - (now - valid_window[0]))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {wait_time} seconds."
        )

    # Record new request
    valid_window.append(now)
    request_history[client_ip] = valid_window
