import logging
import time


logger = logging.getLogger("app.request")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = time.perf_counter()
        user_id = request.user.id if request.user.is_authenticated else None
        logger.debug(
            "request.start method=%s path=%s user_id=%s htmx=%s",
            request.method,
            request.path,
            user_id,
            request.headers.get("HX-Request") == "true",
        )
        try:
            response = self.get_response(request)
        except Exception:
            logger.exception(
                "request.error method=%s path=%s user_id=%s elapsed_ms=%.1f",
                request.method,
                request.path,
                user_id,
                (time.perf_counter() - started_at) * 1000,
            )
            raise
        logger.info(
            "request.complete method=%s path=%s status=%s user_id=%s elapsed_ms=%.1f",
            request.method,
            request.path,
            response.status_code,
            user_id,
            (time.perf_counter() - started_at) * 1000,
        )
        return response
