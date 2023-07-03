from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

from BroomStick.data_class.APIResponse import APIResponse, CommonAPIResponse
from BroomStick.data_class.RouteFunction import RouteFunction
from fastapi import Request, Response

if TYPE_CHECKING:
    from BroomStick.data_class.Route import Route


class CacheFunction(RouteFunction):

    def __init__(self):
        super().__init__("cache")
        self.route: Route = None

        self.cached_responses_by_user = {}
        self.last_response_time_by_user = {}
        self.last_response_time_global = None
        self.cached_response_global = None

    def interval(self):
        return self.get_config().get("interval")

    def user_cached(self):
        return self.get_config().get("userCached")

    def global_cached(self):
        return self.get_config().get("globalCached")

    def handle_request(self, request: Request, headers: dict, cookies: dict, json: dict):
        if self.interval == 0:
            return CommonAPIResponse.Success

        current_time = datetime.now().timestamp()

        user_object = self.route.main.authenticator.get_user(request.headers.get("Authenticate"))
        if self.user_cached() and user_object is not None:
            user_id = user_object.user_id
            if user_id in self.cached_responses_by_user:
                last_request_time = self.last_response_time_by_user[user_id]
                if current_time - last_request_time < self.interval():
                    return self.cached_responses_by_user[user_id]
            return CommonAPIResponse.Success

        if self.last_response_time_global is not None and self.global_cached():
            if current_time - self.last_response_time_global < self.interval():
                return self.cached_response_global

        return CommonAPIResponse.Success

    def after_handle_request(self, request: Request, planned_response: Response) -> APIResponse:
        if self.interval == 0:
            return CommonAPIResponse.Success

        current_time = datetime.now().timestamp()
        user_object = self.route.main.authenticator.get_user(request.headers.get("Authenticate"))
        if self.user_cached() and user_object is not None:
            user_id = user_object.user_id
            self.last_response_time_by_user[user_id] = current_time
            self.cached_responses_by_user[user_id] = planned_response
            return CommonAPIResponse.Success

        if self.global_cached():
            self.last_response_time_global = current_time
            self.cached_response_global = planned_response
            return CommonAPIResponse.Success

        return CommonAPIResponse.Success