from __future__ import annotations

import datetime
import hashlib
import traceback
import uuid
from typing import TYPE_CHECKING, Optional, Dict, Any

import requests
from expiring_dict import ExpiringDict
from pydantic import BaseModel
from fastapi import Request, HTTPException
from fastapi.responses import PlainTextResponse
import jwt

from BroomStick.Authenticator.AuthenticatedUser import AuthenticatedUser
from BroomStick.data_class.APIResponse import CommonAPIResponse

if TYPE_CHECKING:
    from BroomStick import BroomStick


class RegisterRequest(BaseModel):
    username: str
    password: str
    userId: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AuthenticationRequest(BaseModel):
    username: str
    password: str


class Authenticator:

    def __init__(self, main: BroomStick):
        self.main: BroomStick = main
        self.cached_users = ExpiringDict(self.main.config["userCacheTime"])

        self.token_user_id_cache = ExpiringDict(self.main.config["userCacheTime"])
        self.api_key_user_id_cache = ExpiringDict(self.main.config["userCacheTime"])

        self.register_routes()

    def register_routes(self):

        @self.main.app.post("/register")
        async def create_user(request: Request, register: RegisterRequest):
            if 'Authorization' not in request.headers or self.main.config['AuthorizationAPIKey'] != request.headers['Authorization']:
                return CommonAPIResponse.UnAuthorized.get_response_object()
            try:
                self.create_user(register.userId, register.username, register.password, register.metadata)
            except Exception as ex:
                return CommonAPIResponse.InternalError.get_response_object()
            return CommonAPIResponse.Success.get_response_object()

        @self.main.app.post("/authenticate")
        async def authenticate(request: Request, auth: AuthenticationRequest):
            # if 'Authorization' not in request.headers or self.main.config['AuthorizationAPIKey'] != request.headers['Authorization']:
            #     return CommonAPIResponse.UnAuthorized.get_response_object()
            token = self.authenticate(auth.username, auth.password)
            if not token:
                return CommonAPIResponse.UnAuthorized.get_response_object()
            # return PlainTextResponse(token)
            user = self.get_user(token)
            response = CommonAPIResponse.Success
            response.data = self.create_api_key_for_user(user.user_id)
            return response.get_response_object()

    def create_user(self, user_id, username, password, metadata=None):
        # Hash the password using SHA256
        hashedPassword = self.hash_password(password)
        if metadata is None:
            metadata = {}
            metadata.update(self.main.config["authenticator"]["defaultMetadata"])
        # Create a new document with the user data
        user = {
            "userId": user_id,
            "username": username,
            "password": hashedPassword,
            "metadata": metadata
        }
        # if user already exists, update only the password
        if self.main.mongo["BroomStick"]["users"].find_one({"userId": user_id}):
            user = {
                "password": hashedPassword
            }
        self.main.mongo["BroomStick"]["users"].update_one({"userId": user_id}, {"$set": user}, upsert=True)
        if user_id in self.cached_users:
            del self.cached_users[user_id]

    def authenticate(self, username, password):
        # Hash the password using SHA256
        hashedPassword = self.hash_password(password)

        # Find the user with the given username and password
        result = self.main.mongo["BroomStick"]["users"].find_one({
            "username": username,
            "password": hashedPassword
        })

        if result is not None:
            # Generate a JWT token for the authenticated user
            tokenDescriptor = {
                "sub": {"userId": result["userId"]},
                "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=self.main.config["jwtActiveTime"])
            }
            jwt_assertion = jwt.encode(
                tokenDescriptor,
                self.main.config["tokenSecret"]
            )
            return jwt_assertion
        else:
            # Return None if the authentication failed
            return None

    def create_api_key_for_user(self, user_id):
        api_key = str(uuid.uuid4())
        self.main.mongo["BroomStick"]["users"].update_one({"userId": user_id}, {"$set": {"apiKey": api_key}})
        if user_id in self.api_key_user_id_cache:
            del self.api_key_user_id_cache[user_id]
        return api_key

    def get_user(self, token: str = None, api_key: str = None, user_id: str = None, authorization_token: str = None) -> Optional[AuthenticatedUser]:
        if authorization_token is not None:
            scheme, _, authorization_token = authorization_token.partition(" ")
            if scheme.lower() != "bearer":
                return None

            if len(authorization_token) == 36:
                return self.get_user(api_key=authorization_token)
            else:
                return self.get_user(token=authorization_token)
        if user_id is not None:
            if user_id in self.cached_users:
                return self.cached_users[user_id]
            user = self.main.mongo["BroomStick"]["users"].find_one({"userId": user_id})
            if user is not None:
                user = AuthenticatedUser(user_id, user["username"], user.get("metadata", {}))
                self.cached_users[user_id] = user
                return user
            return None

        if token is not None:
            return self.get_user(user_id=self.get_user_id_from_jwt(token))

        if api_key is not None:
            return self.get_user(user_id=self.get_user_id_from_api_key(api_key))

    def get_user_id_from_jwt(self, token: str) -> Optional[AuthenticatedUser]:
        try:
            data = jwt.decode(token, self.main.config["tokenSecret"], algorithms=["HS256"])
            # check if user is already in the cache
            if token in self.token_user_id_cache:
                return self.token_user_id_cache[token]

            userId = data["sub"]["userId"]
            return userId
        except Exception as e:
            pass
        return None

    def get_user_id_from_api_key(self, api_key: str) -> Optional[str]:
        if api_key in self.api_key_user_id_cache:
            return self.api_key_user_id_cache[api_key]
        user = self.main.mongo["BroomStick"]["users"].find_one({"apiKey": api_key})
        if user is not None:
            self.api_key_user_id_cache[api_key] = user["userId"]
            return user["userId"]
        return None

    def hash_password(self, password):
        sha256 = hashlib.sha256()
        sha256.update(password.encode('utf-8'))
        return sha256.hexdigest()
