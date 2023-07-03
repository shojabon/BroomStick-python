from fastapi import Response


class APIResponse:
    def __init__(self, status=None, message=None, data=None, code=-1):
        self.status = status
        self.message = message
        self.data = data if data is not None else {}
        self.code = code
        self.http_response_message = None

    def set_http_response(self, response):
        self.http_response_message = response

    def get_http_response(self):
        return self.http_response_message

    def get_response_object(self):
        return {
            "status": self.status,
            "message": self.message,
            "data": self.data,
            "code": self.code
        }


class CommonAPIResponse:
    Success = APIResponse("success", "Success", None, 200)
    UnAuthorized = APIResponse("unauthorized", "Not Authorized", None, 401)
    RouteNotFound = APIResponse("route_not_found", "Route Not Found", None, 404)
    PermissionInsufficient = APIResponse("permission_lacking", "Permission Insufficient", None, 403)
    RateLimited = APIResponse("rate_limited", "Rate limited", None, 429)
    NoBackendsFound = APIResponse("backend_not_found", "No backends found", None, 502)
    BackendDisconnected = APIResponse("backend_disconnected", "Backend Disconnected", None, 503)
    InternalError = APIResponse("error_internal", "Internal Error Occurred", None, 500)
