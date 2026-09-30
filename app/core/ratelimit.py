"""Limitação de pedidos em memória de processo (§37).

Suficiente para uma única instância. Quando o AngoRating correr em mais do que
um processo, trocar a clase `Limiter` por uma com Redis — a interface é a
mesma, `hit()` devolve sempre (permitido, restantes).
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class SlidingWindow:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Regista uma tentativa. Devolve (permitido, restantes)."""
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = int(window_seconds - (now - bucket[0])) + 1
                return False, retry_after
            bucket.append(now)
            return True, max(0, limit - len(bucket))

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


limiter = SlidingWindow()


def client_key(request: Request, scope: str) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    return f"{scope}:{ip}"


def rate_limit(scope: str, limit: int, window_seconds: int, message: str | None = None):
    """Dependência FastAPI. Exemplo:

        @router.post("/login", dependencies=[Depends(rate_limit("login", 8, 60))])
    """

    def _dependency(request: Request):
        allowed, retry_after = limiter.hit(client_key(request, scope), limit, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=message or "Demasiadas tentativas. Tente novamente dentro de instantes.",
                headers={"Retry-After": str(retry_after)},
            )
        return True

    return _dependency
