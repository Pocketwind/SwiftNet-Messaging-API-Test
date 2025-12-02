from dataclasses import dataclass
@dataclass
class ConsumerCredentials:
    consumerKey: str
    consumerSecret: str
@dataclass
class TokenResponse:
    accessToken: str
    refreshToken: str
    expiresIn: int
    refreshTokenExpiresIn: int
    createdAt: int
@dataclass
class JWTTokenResponse:
    accessToken: str
    refreshToken: str
    expiresIn: int
    refreshTokenExpiresIn: int
    createdAt: int
    jwtToken: str
    jwsToken: str
@dataclass
class JWTConfig:
    issuer: str
    subject: str
    audience: str
    expirationTime: int
    privateKey: str
    certificate: str
    consumerKey: str
    consumerSecret: str