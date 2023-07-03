from __future__ import annotations
from typing import TYPE_CHECKING
from fastapi import Request, Response
from BroomStick.data_class.APIResponse import CommonAPIResponse, APIResponse

if TYPE_CHECKING:
    from BroomStick.data_class.Route import Route


class RouteFunction:

    def __init__(self, function_name: str):
        self.route: Route = None
        self.function_name = function_name

    def init(self):
        pass

    def get_config(self):
        res = self.route.route_info.get(self.function_name)
        if res is None:
            return {}
        return res

    def is_allowed_to_use(self, request: Request) -> APIResponse:
        return CommonAPIResponse.Success

    def handle_request(self, request: Request, headers: dict, cookies: dict, json: dict) -> APIResponse:
        return CommonAPIResponse.Success

    def after_handle_request(self, request: Request, planned_response: Response) -> APIResponse:
        return CommonAPIResponse.Success