from __future__ import annotations

import random
import re
from typing import TYPE_CHECKING

import requests
from fastapi import FastAPI, Request

from BroomStick.data_class.Functions.AccountFunction import AccountFunction
from BroomStick.data_class.Functions.CacheFunction import CacheFunction
from BroomStick.data_class.Functions.HostNameFunction import HostNameFunction
from BroomStick.data_class.Functions.RouteInfoFunction import RouteInfoFunction

if TYPE_CHECKING:
    from BroomStick import BroomStick
    from BroomStick.data_class.RouteFunction import RouteFunction


class Route:

    def __init__(self, main: BroomStick, route_info: dict):
        self.main: BroomStick = main
        self.route_info: dict = route_info
        self.functions: list[RouteFunction] = []

        self.route_info_function: RouteInfoFunction = self.register_function(RouteInfoFunction())
        self.account_function: AccountFunction = self.register_function(AccountFunction())
        self.cache_function: CacheFunction = self.register_function(CacheFunction())
        self.hostname_function: RouteInfoFunction = self.register_function(HostNameFunction())

    def register_function(self, func: RouteFunction):
        func.route = self
        func.init()
        self.functions.append(func)
        return func

