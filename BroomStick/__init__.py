import glob
import json
import random
import uvicorn
import re

import requests
from fastapi import FastAPI, Request, Response, status
from pymongo import MongoClient

from BroomStick.Authenticator.Authenticator import Authenticator
from BroomStick.data_class.APIResponse import CommonAPIResponse, APIResponse
from BroomStick.data_class.Route import Route
from BroomStick.utils.JsonTools import flatten_dict, unflatten_dict


class BroomStick:

    def __init__(self):
        self.app = FastAPI()
        self.config = {}
        file = open("config/config.json")
        self.config = json.loads(file.read())
        file.close()

        self.mongo = MongoClient(self.config["mongodb"])
        self.authenticator = Authenticator(self)

        self.routes = []
        self.load_routes()

        self.register_routes()

        dynamic_settings = {}
        if self.config["ssl"]["key"] != "" and self.config["ssl"]["cert"] != "":
            dynamic_settings = {
                "ssl_keyfile": self.config["ssl"]["key"],
                "ssl_certfile": self.config["ssl"]["cert"]
            }

        # start server
        uvicorn.run(
            self.app,
            port=self.config["listeningPort"],
            host="0.0.0.0",

            **dynamic_settings
        )

    def load_routes(self):
        for route in glob.glob("routes/*.json"):
            file = open(route)

            data = json.loads(file.read())
            file.close()

            default = data.get("default")
            if default is None:
                continue

            default = flatten_dict(default)

            for datum in data.get("routes"):
                datum = flatten_dict(datum)
                base = default.copy()
                base.update(datum)
                datum = unflatten_dict(base)
                route = Route(self, datum)
                self.routes.append(route)

        # sort routes by route.length
        self.routes.sort(key=lambda x: len(x.route_info_function.get_path()), reverse=True)

    async def process_request(self, request: Request, method: str):

        # only search for routes that have the correct hostname
        available_routes_for_hostname = []
        for route in self.routes:
            if route.hostname_function.is_allowed_to_use(request) == CommonAPIResponse.Success:
                available_routes_for_hostname.append(route)

        route = None
        for route in available_routes_for_hostname:
            route: Route = route
            if route.route_info_function.matches_path(request.url.path):
                break
        if route is None:
            return CommonAPIResponse.RouteNotFound

        if len(route.route_info_function.get_backends()) == 0:
            return CommonAPIResponse.NoBackendsFound

        for function in route.functions:
            result = function.is_allowed_to_use(request)
            if result is not CommonAPIResponse.Success:
                return result

        path = request.url.path
        if route.route_info_function.should_remove_prefix():
            pattern = route.route_info_function.get_path_pattern()
            path = re.sub(pattern, "", path)

        backend = random.choice(route.route_info_function.get_backends()) + path
        backend = route.route_info_function.clean_path(backend, remove_path_params=False)

        headers = dict(request.headers)
        if "host" in headers: del headers["host"]
        if "connection" in headers: del headers["connection"]

        cookies = dict(request.cookies)

        json_object = None
        if method == "POST" or method == "PUT" or method == "PATCH":
            try:
                json_object = await request.json()
            except Exception:
                pass

        for function in route.functions:
            result = function.handle_request(request, headers, cookies, json_object)
            if result is not CommonAPIResponse.Success:
                return result

        params = {}
        if json_object is not None:
            params["json"] = json_object
        else:
            params["data"] = await request.body()

        params["headers"] = headers
        params["cookies"] = cookies

        if method == "GET":
            req = requests.get(backend, **params)
        elif method == "POST":
            req = requests.post(backend, **params)
        elif method == "PUT":
            req = requests.put(backend, **params)
        elif method == "DELETE":
            req = requests.delete(backend, **params)
        elif method == "PATCH":
            req = requests.patch(backend, **params)
        elif method == "HEAD":
            req = requests.head(backend, **params)
        elif method == "OPTIONS":
            req = requests.options(backend, **params)
        else:
            return None

        req_headers = dict(req.headers)
        if "Content-Length" in req_headers:
            del req_headers["Content-Length"]
        if "Content-Encoding" in req_headers:
            del req_headers["Content-Encoding"]

        res = Response(
            content=req.content,
            status_code=req.status_code,
            headers=req_headers,
            media_type=req.headers.get("Content-Type")
        )
        for function in route.functions:
            function.after_handle_request(request, res)

        return res

    def register_routes(self):
        @self.app.get("/{full_path:path}")
        @self.app.put("/{full_path:path}")
        @self.app.post("/{full_path:path}")
        @self.app.delete("/{full_path:path}")
        @self.app.patch("/{full_path:path}")
        @self.app.head("/{full_path:path}")
        @self.app.options("/{full_path:path}")
        async def get(request: Request, full_path: str, response: Response):
            # print request domain
            res = await self.process_request(request, request.method)
            if isinstance(res, APIResponse):
                response.status_code = res.code
                return res.get_response_object()
            return res
