"""
Audit middleware for automatic tracking of API requests and responses.

This middleware captures HTTP requests and responses to create audit trails
for all API interactions, providing comprehensive system activity tracking.
"""

import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.db.models.audit_event import AuditEventType, AuditEventSeverity
from backend.app.db.repositories.audit_event import AuditEventRepository
from backend.app.db.session import get_db


logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic audit logging of API requests.

    This middleware captures:
    - All HTTP requests and responses
    - User authentication information
    - Request/response timing
    - Error conditions
    - Resource access patterns
    """

    def __init__(
        self,
        app,
        excluded_paths: Optional[list] = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
        max_body_size: int = 1024 * 10,  # 10KB
    ):
        """
        Initialize audit middleware.

        Args:
            app: FastAPI application instance
            excluded_paths: List of paths to exclude from auditing
            log_request_body: Whether to log request bodies
            log_response_body: Whether to log response bodies
            max_body_size: Maximum body size to log (in bytes)
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
        ]
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and create audit event.

        Args:
            request: HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Skip excluded paths
        if self._should_exclude_path(request.url.path):
            return await call_next(request)

        # Record start time
        start_time = time.time()

        # Extract request information
        request_info = await self._extract_request_info(request, request_id)

        # Initialize response info
        response_info = {
            "status_code": None,
            "headers": {},
            "body": None,
            "error": None,
        }

        try:
            # Process request
            response = await call_next(request)

            # Extract response information
            response_info = await self._extract_response_info(response)

            # Calculate processing time
            processing_time = time.time() - start_time

            # Create audit event
            await self._create_audit_event(
                request_info=request_info,
                response_info=response_info,
                processing_time=processing_time,
                success=True,
            )

            return response

        except Exception as e:
            # Calculate processing time for failed requests
            processing_time = time.time() - start_time

            # Update response info with error
            response_info["error"] = str(e)
            response_info["status_code"] = 500

            # Create audit event for error
            await self._create_audit_event(
                request_info=request_info,
                response_info=response_info,
                processing_time=processing_time,
                success=False,
                error_message=str(e),
            )

            # Re-raise the exception
            raise

    def _should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from auditing."""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)

    async def _extract_request_info(self, request: Request, request_id: str) -> Dict[str, Any]:
        """
        Extract relevant information from the request.

        Args:
            request: HTTP request
            request_id: Unique request identifier

        Returns:
            Dictionary with request information
        """
        # Get user information if available
        user_info = self._get_user_info(request)

        # Extract client information
        client_host = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")

        # Extract request body if enabled and within size limits
        request_body = None
        if self.log_request_body:
            try:
                body_bytes = await request.body()
                if len(body_bytes) <= self.max_body_size:
                    if body_bytes:
                        content_type = request.headers.get("content-type", "")
                        if "application/json" in content_type:
                            try:
                                request_body = json.loads(body_bytes.decode())
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                request_body = {"raw": body_bytes.decode("utf-8", errors="ignore")}
                        else:
                            request_body = {"content_type": content_type, "size": len(body_bytes)}
            except Exception as e:
                logger.warning(f"Failed to extract request body: {e}")

        return {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_host": client_host,
            "user_agent": user_agent,
            "body": request_body,
            "user_id": user_info.get("user_id"),
            "user_role": user_info.get("user_role"),
            "session_id": user_info.get("session_id"),
        }

    async def _extract_response_info(self, response: Response) -> Dict[str, Any]:
        """
        Extract relevant information from the response.

        Args:
            response: HTTP response

        Returns:
            Dictionary with response information
        """
        response_info = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": None,
        }

        # Extract response body if enabled
        if self.log_response_body and hasattr(response, 'body'):
            try:
                if len(response.body) <= self.max_body_size:
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        try:
                            response_info["body"] = json.loads(response.body.decode())
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            response_info["body"] = {"raw": response.body.decode("utf-8", errors="ignore")}
                    else:
                        response_info["body"] = {"content_type": content_type, "size": len(response.body)}
            except Exception as e:
                logger.warning(f"Failed to extract response body: {e}")

        return response_info

    def _get_user_info(self, request: Request) -> Dict[str, Any]:
        """
        Extract user information from the request.

        Args:
            request: HTTP request

        Returns:
            Dictionary with user information
        """
        user_info = {
            "user_id": None,
            "user_role": None,
            "session_id": None,
        }

        try:
            # Try to get user from request state (set by auth middleware)
            if hasattr(request.state, "current_user"):
                user = request.state.current_user
                if user:
                    user_info["user_id"] = getattr(user, "id", None)
                    user_info["user_role"] = getattr(user, "role", None)

            # Try to get session ID from various sources
            session_id = (
                request.headers.get("x-session-id") or
                request.cookies.get("session_id") or
                request.headers.get("authorization", "").split(" ")[-1] if "Bearer" in request.headers.get("authorization", "") else None
            )
            user_info["session_id"] = session_id

        except Exception as e:
            logger.warning(f"Failed to extract user info: {e}")

        return user_info

    async def _create_audit_event(
        self,
        request_info: Dict[str, Any],
        response_info: Dict[str, Any],
        processing_time: float,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Create an audit event for the request/response.

        Args:
            request_info: Information about the request
            response_info: Information about the response
            processing_time: Time taken to process the request
            success: Whether the request was successful
            error_message: Error message if request failed
        """
        try:
            # Get database session
            async for session in get_db():
                audit_repo = AuditEventRepository(session)

                # Determine event type based on endpoint and method
                event_type = self._determine_event_type(
                    request_info["path"],
                    request_info["method"],
                    response_info["status_code"]
                )

                # Determine severity
                severity = self._determine_severity(
                    response_info["status_code"],
                    success,
                    processing_time
                )

                # Create metadata
                metadata = {
                    "processing_time_ms": round(processing_time * 1000, 2),
                    "request_size": len(str(request_info.get("body", ""))) if request_info.get("body") else 0,
                    "response_size": len(str(response_info.get("body", ""))) if response_info.get("body") else 0,
                    "query_params": request_info.get("query_params", {}),
                }

                # Extract resource information
                resource_type, resource_id = self._extract_resource_info(
                    request_info["path"],
                    request_info["method"]
                )

                # Create audit event
                await audit_repo.create(
                    event_type=event_type,
                    action=f"{request_info['method']} {request_info['path']}",
                    user_id=request_info.get("user_id"),
                    session_id=request_info.get("session_id"),
                    user_role=request_info.get("user_role"),
                    ip_address=request_info.get("client_host"),
                    user_agent=request_info.get("user_agent"),
                    request_id=request_info.get("request_id"),
                    endpoint=request_info["path"],
                    http_method=request_info["method"],
                    resource_type=resource_type,
                    resource_id=resource_id,
                    description=self._generate_description(request_info, response_info, success),
                    metadata=metadata,
                    severity=severity,
                    success="success" if success else "failure",
                    error_message=error_message,
                )

                await session.commit()
                break

        except Exception as e:
            logger.error(f"Failed to create audit event: {e}")

    def _determine_event_type(self, path: str, method: str, status_code: Optional[int]) -> AuditEventType:
        """Determine the appropriate event type based on the request."""
        # Authentication endpoints
        if "/auth/login" in path:
            return AuditEventType.LOGIN if status_code == 200 else AuditEventType.LOGIN_FAILED
        elif "/auth/logout" in path:
            return AuditEventType.LOGOUT
        elif "/auth/reset-password" in path:
            return AuditEventType.PASSWORD_RESET

        # Booking endpoints
        elif "/bookings" in path:
            if method == "POST":
                return AuditEventType.BOOKING_CREATED
            elif method in ["PUT", "PATCH"]:
                return AuditEventType.BOOKING_UPDATED
            elif "cancel" in path:
                return AuditEventType.BOOKING_CANCELLED

        # Payment endpoints
        elif "/payments" in path:
            if method == "POST":
                return AuditEventType.PAYMENT_INITIATED
            elif "refund" in path:
                return AuditEventType.PAYMENT_REFUNDED

        # User management
        elif "/users" in path:
            if method == "POST":
                return AuditEventType.USER_CREATED
            elif method in ["PUT", "PATCH"]:
                return AuditEventType.USER_UPDATED
            elif method == "DELETE":
                return AuditEventType.USER_DELETED

        # System events for errors
        elif status_code and status_code >= 500:
            return AuditEventType.SYSTEM_ERROR

        # Default to a generic system event
        return AuditEventType.SYSTEM_ERROR if status_code and status_code >= 400 else AuditEventType.LOGIN

    def _determine_severity(self, status_code: Optional[int], success: bool, processing_time: float) -> AuditEventSeverity:
        """Determine the severity level for the event."""
        if not success or (status_code and status_code >= 500):
            return AuditEventSeverity.HIGH
        elif status_code and status_code >= 400:
            return AuditEventSeverity.MEDIUM
        elif processing_time > 5.0:  # Slow requests
            return AuditEventSeverity.MEDIUM
        else:
            return AuditEventSeverity.LOW

    def _extract_resource_info(self, path: str, method: str) -> tuple[Optional[str], Optional[str]]:
        """Extract resource type and ID from the path."""
        path_parts = path.strip("/").split("/")

        # Skip API version prefix
        if path_parts and path_parts[0] in ["v1", "api"]:
            path_parts = path_parts[1:]

        if len(path_parts) >= 1:
            resource_type = path_parts[0]

            # Try to find resource ID (usually numeric)
            resource_id = None
            for part in path_parts[1:]:
                if part.isdigit():
                    resource_id = part
                    break

            return resource_type, resource_id

        return None, None

    def _generate_description(self, request_info: Dict, response_info: Dict, success: bool) -> str:
        """Generate a human-readable description for the audit event."""
        method = request_info["method"]
        path = request_info["path"]
        status_code = response_info.get("status_code")

        if success:
            return f"Successful {method} request to {path} (HTTP {status_code})"
        else:
            return f"Failed {method} request to {path} (HTTP {status_code})"


class AuditEventLogger:
    """Helper class for manual audit event creation."""

    @staticmethod
    async def log_user_action(
        user_id: int,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        description: Optional[str] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        severity: AuditEventSeverity = AuditEventSeverity.LOW,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """
        Manually log a user action as an audit event.

        Args:
            user_id: ID of the user performing the action
            action: Description of the action
            resource_type: Type of resource affected
            resource_id: ID of the resource affected
            description: Human-readable description
            old_values: Previous values (for updates)
            new_values: New values (for updates)
            metadata: Additional context
            severity: Event severity
            session_id: Session ID
            ip_address: User's IP address
        """
        try:
            async for session in get_db():
                audit_repo = AuditEventRepository(session)

                await audit_repo.create(
                    event_type=AuditEventType.USER_UPDATED,  # Generic user action
                    action=action,
                    user_id=user_id,
                    session_id=session_id,
                    ip_address=ip_address,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    description=description or f"User performed action: {action}",
                    old_values=old_values,
                    new_values=new_values,
                    metadata=metadata,
                    severity=severity,
                    success="success",
                )

                await session.commit()
                break

        except Exception as e:
            logger.error(f"Failed to log user action: {e}")

    @staticmethod
    async def log_system_event(
        event_type: AuditEventType,
        description: str,
        metadata: Optional[Dict] = None,
        severity: AuditEventSeverity = AuditEventSeverity.LOW,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log a system event.

        Args:
            event_type: Type of system event
            description: Description of the event
            metadata: Additional context
            severity: Event severity
            success: Whether the event was successful
            error_message: Error message if applicable
        """
        try:
            async for session in get_db():
                audit_repo = AuditEventRepository(session)

                await audit_repo.create(
                    event_type=event_type,
                    action=event_type.value,
                    description=description,
                    metadata=metadata,
                    severity=severity,
                    success="success" if success else "failure",
                    error_message=error_message,
                )

                await session.commit()
                break

        except Exception as e:
            logger.error(f"Failed to log system event: {e}")
