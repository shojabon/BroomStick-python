from __future__ import annotations

import re
from typing import TYPE_CHECKING

from BroomStick.data_class.APIResponse import APIResponse, CommonAPIResponse
from BroomStick.data_class.RouteFunction import RouteFunction
from fastapi import Request

if TYPE_CHECKING:
    from BroomStick.data_class.Route import Route


class HostNameFunction(RouteFunction):

    def __init__(self):
        super().__init__("hostname")
        self.cached_pattern = None
        self.route: Route = None
    
    def init(self):
        pass

    def get_allowed_hosts(self):
        return self.get_config().get("allowedHosts", [])

    def is_allowed_to_use(self, request: Request) -> APIResponse:
        allowed_hosts = self.get_allowed_hosts()
        if len(allowed_hosts) == 0:
            return CommonAPIResponse.Success
        if request.url.hostname not in allowed_hosts:
            return CommonAPIResponse.RouteNotFound
        return CommonAPIResponse.Success

