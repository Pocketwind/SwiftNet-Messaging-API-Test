import requests, jwt, base64, time, math, random
from data import *
from Token import *

isJWTRequired = False
FILE_PATH_BASIC = "basic_tokens.json"
FILE_PATH_JWT = "jwt_tokens.json"
BASE_URL="https://api-test.swiftnet.sipn.swift.com"
URL=f"{BASE_URL}/oauth2/v1/token"
CONSUMER_KEY_BASIC="bAKf7CBcOEhaH0z6WLAMMql5s4lC2E2Y"
CONSUMER_SECRET_BASIC="co1nuoseiAZHjy7i"
CONSUMER_KEY_JWT="rXGsrqqsH0PPeb90EKEBAT0HtRmWiE0U"
CONSUMER_SECRET_JWT="9XbAOjziV2GTfZRH"
"""res=requests.get("https://sandbox.swift.com/sandbox-selfsigned-dummy-secret/privatekey2")
dummyPrivateKey=f"-----BEGIN PRIVATE KEY-----\n{res.text}\n-----END PRIVATE KEY-----"
res=requests.get("https://sandbox.swift.com/sandbox-selfsigned-dummy-secret/certificate2")
dummyCertificate=f"-----BEGIN CERTIFICATE-----\n{res.text}\n-----END CERTIFICATE-----"""

with open("private.txt", "r") as f:
    dummyPrivateKey=f.read()
with open("certificate.txt", "r") as f:
    dummyCertificate=f.read()

AUDIENCE="api-test.swiftnet.sipn.swift.com/oauth2/v1/token"
SUBJECT="cn=%3,cn=api,o=etpxkrss,o=swift"
expirationTime=900
jwtConfig = JWTConfig(
    consumerKey=CONSUMER_KEY_JWT,
    consumerSecret=CONSUMER_SECRET_JWT,
    privateKey=dummyPrivateKey,
    certificate=dummyCertificate,
    audience=AUDIENCE,
    subject=SUBJECT,
    expirationTime=expirationTime,
    issuer=CONSUMER_KEY_JWT
)

def Auth(isJWTRequied):
    if isJWTRequied:
        accessToken, cred = JWTAuth(jwtConfig)
        return accessToken, cred
    else:
        accessToken, cred = BasicAuth()
        return accessToken, cred

def BasicAuth():
    token, result = ReadTokens(FILE_PATH_BASIC)
    consumerCred = ConsumerCredentials(CONSUMER_KEY_BASIC, CONSUMER_SECRET_BASIC)
    if result:
        timeElapsed = int(time.time()) - token.createdAt
        if timeElapsed >= 24*60*60:
            print("Refresh Token is expired, generating new tokens...")
            token = GenerateNewTokens(URL, consumerCred)
            SaveTokens(token, FILE_PATH_BASIC)
        elif timeElapsed >= 30*60:
            print("Access Token is expired, refreshing tokens...")
            token = RefreshBasicToken(URL, token.refreshToken, consumerCred)
            SaveTokens(token, FILE_PATH_BASIC)
    else:
        print("Cannot read token file, generating new tokens...")
        token = GenerateNewTokens(URL, consumerCred)
        SaveTokens(token, FILE_PATH_BASIC)

    return token.accessToken, consumerCred

def JWTAuth(jwtConfig):
    token, result = ReadTokens(FILE_PATH_JWT)
    consumerCred = ConsumerCredentials(CONSUMER_KEY_JWT, CONSUMER_SECRET_JWT)

    if result:
        timeElapsed = int(time.time()) - token.createdAt
        if timeElapsed >= 24*60*60:
            print("Refresh Token is expired, generating new tokens...")
            token = GenerateNewTokensWithJWT(URL, jwtConfig)
            SaveTokens(token, FILE_PATH_JWT)
        elif timeElapsed >= 30*60:
            print("Access Token is expired, refreshing tokens...")
            token = RefreshBasicToken(URL, token.refreshToken, consumerCred, isJWT=True)
            SaveTokens(token, FILE_PATH_JWT)
    else:
        print("Cannot read token file, generating new tokens...")
        token = GenerateNewTokensWithJWT(URL, jwtConfig)
        SaveTokens(token, FILE_PATH_JWT)

    return token.accessToken, consumerCred