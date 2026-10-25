"""In-memory rate limiter with sliding window lockout and retry-after backoff."""

import time
from collections import defaultdict

from fastapi import HTTPException, status


class InMemoryRateLimiter:
    """Sliding-window rate limiter tracking failed attempts per IP and per email."""

    def __init__(
        self,
        ip_limit: int = 10,
        email_limit: int = 5,
        window_seconds: int = 300,
    ) -> None:
        self.ip_limit = ip_limit
        self.email_limit = email_limit
        self.window_seconds = window_seconds
        # key -> list of float timestamps of failed attempts
        self._ip_attempts: dict[str, list[float]] = defaultdict(list)
        self._email_attempts: dict[str, list[float]] = defaultdict(list)

    def _clean_and_get_count(
        self,
        attempts_dict: dict[str, list[float]],
        key: str,
        now: float,
    ) -> tuple[int, float | None]:
        """Prunes timestamps older than window_seconds and returns (count, oldest_ts)."""
        cutoff = now - self.window_seconds
        timestamps = [ts for ts in attempts_dict.get(key, []) if ts > cutoff]
        attempts_dict[key] = timestamps
        count = len(timestamps)
        oldest_ts = timestamps[0] if timestamps else None
        return count, oldest_ts

    def check_rate_limit(self, ip: str, email: str | None = None) -> None:
        """Checks if IP or email has exceeded the allowable failed attempts.

        Raises:
            HTTPException: 429 Too Many Requests with Retry-After header.
        """
        now = time.time()

        # Check IP limit
        if ip:
            ip_count, oldest_ip_ts = self._clean_and_get_count(
                self._ip_attempts, ip, now
            )
            if ip_count >= self.ip_limit and oldest_ip_ts is not None:
                retry_after = max(1, int(oldest_ip_ts + self.window_seconds - now))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many failed attempts from this IP address. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )

        # Check Email limit
        if email:
            normalized_email = email.lower().strip()
            email_count, oldest_email_ts = self._clean_and_get_count(
                self._email_attempts, normalized_email, now
            )
            if email_count >= self.email_limit and oldest_email_ts is not None:
                retry_after = max(1, int(oldest_email_ts + self.window_seconds - now))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many failed attempts for this account. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )

    def record_failure(self, ip: str, email: str | None = None) -> None:
        """Records a failed attempt for both IP and email."""
        now = time.time()
        if ip:
            self._ip_attempts[ip].append(now)
        if email:
            self._email_attempts[email.lower().strip()].append(now)

    def record_success(self, ip: str, email: str | None = None) -> None:
        """Clears failed attempts on successful authentication."""
        if ip and ip in self._ip_attempts:
            del self._ip_attempts[ip]
        if email:
            norm_email = email.lower().strip()
            if norm_email in self._email_attempts:
                del self._email_attempts[norm_email]

    def reset(self) -> None:
        """Resets all rate limiting state (for testing)."""
        self._ip_attempts.clear()
        self._email_attempts.clear()


# Global rate limiter instance
auth_rate_limiter = InMemoryRateLimiter()
