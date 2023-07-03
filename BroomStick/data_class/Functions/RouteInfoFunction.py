from __future__ import annotations

import re
from typing import TYPE_CHECKING

from BroomStick.data_class.RouteFunction import RouteFunction

if TYPE_CHECKING:
    from BroomStick.data_class.Route import Route


class RouteInfoFunction(RouteFunction):

    def __init__(self):
        super().__init__("routeInfo")
        self.cached_pattern = None
        self.route: Route = None
    
    def init(self):
        self.cached_pattern = self.get_path_pattern()

    def get_path(self):
        return self.get_config()["path"]

    def get_backends(self):
        return self.get_config()["backends"]

    def should_remove_prefix(self):
        return self.get_config()["removePrefix"]

    def get_path_pattern(self):
        if self.get_path() is None:
            return None
        pattern = re.sub(r"<.*?>", ".*", re.escape(self.get_path()))
        return pattern

    def matches_path(self, request_path):
        if self.get_path() is None:
            return False
        route = self.clean_path(request_path)
        match = re.match(r"^" + self.cached_pattern + ".*$", route)
        if match is not None:
            return True
        return False

    def clean_path(self, path, remove_path_params=True):
        # Remove path parameters if they exist
        if remove_path_params:
            path_param_index = path.find('?')
            if path_param_index != -1:
                path = path[:path_param_index]

        # Remove trailing slashes
        while path.endswith('/'):
            path = path[:-1]

        return path
