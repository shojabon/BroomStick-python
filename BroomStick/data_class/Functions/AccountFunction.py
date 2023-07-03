from __future__ import annotations

import re
from typing import TYPE_CHECKING

from BroomStick.data_class.APIResponse import CommonAPIResponse
from BroomStick.data_class.RouteFunction import RouteFunction
from fastapi import Request

if TYPE_CHECKING:
    from BroomStick.data_class.Route import Route


class AccountFunction(RouteFunction):

    def __init__(self):
        super().__init__("account")
        self.route: Route = None

    def get_allowed_groups(self):
        return self.get_config().get("allowedGroups")

    def get_public_meta_key(self):
        return self.get_config().get("publicMetaKey")

    def is_allowed_to_use(self, request: Request):
        if len(self.get_allowed_groups()) == 0:
            return CommonAPIResponse.Success
        if request.headers.get("authenticate") is None:
            return CommonAPIResponse.UnAuthorized
        user = self.route.main.authenticator.get_user(request.headers.get("authenticate"))
        if user is None:
            return CommonAPIResponse.UnAuthorized
        user_group = user.metadata.get("group")
        if user_group is None:
            return CommonAPIResponse.UnAuthorized
        if user_group not in self.get_config().get("allowedGroups"):
            return CommonAPIResponse.UnAuthorized
        return CommonAPIResponse.Success

    def handle_request(self, request: Request, headers: dict, cookies: dict, json: dict):
        user_object = self.route.main.authenticator.get_user(request.headers.get("authenticate"))
        if user_object is None:
            if len(self.get_allowed_groups()) == 0:
                return CommonAPIResponse.Success
            return CommonAPIResponse.UnAuthorized
        del headers["authenticate"]
        headers["x-User-Id"] = user_object.user_id
        headers["x-User-Name"] = user_object.username
        for metadata in self.get_public_meta_key():
            if metadata not in user_object.metadata:
                continue
            headers["x-User-Metadata-" + metadata] = user_object.metadata[metadata]
        return CommonAPIResponse.Success


