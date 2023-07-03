from __future__ import annotations

import datetime
import hashlib
import traceback
from typing import TYPE_CHECKING, Optional, Dict, Any

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

        self.register_routes()

    def register_routes(self):

        @self.main.app.post("/register")
        async def create_user(request: Request, register: RegisterRequest):
            if 'Authenticate' not in request.headers or \
                    not self.main.config['AuthenticationAPIKey'] == request.headers['Authenticate']:
                raise CommonAPIResponse.UnAuthorized.get_response_object()
            try:
                self.create_user(register.userId, register.username, register.password, register.metadata)
            except Exception as ex:
                return CommonAPIResponse.InternalError.get_response_object()
            return "User created successfully."

        @self.main.app.post("/authenticate")
        async def authenticate(request: Request, auth: AuthenticationRequest):
            if 'Authenticate' not in request.headers or \
                    not self.main.config['AuthenticationAPIKey'] == request.headers['Authenticate']:
                return CommonAPIResponse.UnAuthorized.get_response_object()
            token = self.authenticate(auth.username, auth.password)
            if not token:
                return CommonAPIResponse.UnAuthorized.get_response_object()
            return PlainTextResponse(token)

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
        self.main.mongo["BroomStick"]["users"].update_one({"userId": user_id}, {"$set": user}, upsert=True)

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
                "sub": {"username": username},
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

    def authenticate_token(self, token):
        try:
            jwt.decode(token, self.main.config["tokenSecret"], algorithms=["HS256"])
            return True
        except:
            return False

    cachedUsers = {}

    def get_user(self, token) -> Optional[AuthenticatedUser]:
        if token is None:
            return None

        try:
            data = jwt.decode(token, self.main.config["tokenSecret"], algorithms=["HS256"])
            # check if user is already in the cache
            if token in self.cached_users:
                return self.cached_users[token]

            username = data["sub"]["username"]
            user = self.main.mongo["BroomStick"]["users"].find_one({"username": username})
            if user is not None:
                user_id = user["userId"]
                metadata = user["metadata"]

                # add user to cache
                self.cached_users[token] = AuthenticatedUser(user_id, username, metadata)

                return self.cached_users[token]
        except Exception as e:
            traceback.print_exc()
            # Invalid token
            pass
        return None

    def hash_password(self, password):
        sha256 = hashlib.sha256()
        sha256.update(password.encode('utf-8'))
        return sha256.hexdigest()
