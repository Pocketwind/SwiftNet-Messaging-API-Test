import requests, jwt, base64, time, math, random
from Token import *


def Auth(isJWTRequied, settings=None):
    if isJWTRequied:
        accessToken = JWTAuth(settings)
        return accessToken
    else:
        accessToken = BasicAuth(settings)
        return accessToken

def JWTAuth(settings):
    #token, result = ReadTokens(FILE_PATH_JWT)
    currentTime=int(time.time())
    creationTime=GetCreationTime()

    if creationTime==-1:    #Initialize
        print("Initializing New Access Token...")
        accessToken, refreshToken = GenerateNewTokensWithJWT(settings)
        print(f"Access Token: {accessToken}")
        SetAccessToken(accessToken)
        SetRefreshToken(refreshToken)
        SetCreationTime(currentTime)
    elif currentTime-creationTime > settings["expirationTime"]:
        print("Token Expired. Refreshing New Token.")
        accessToken, refreshToken = RefreshToken(settings)
        print(f"Access Token: {accessToken}")
        SetAccessToken(accessToken)
        SetRefreshToken(refreshToken)

    return GetAccessToken()

def BasicAuth(settings):
    key=settings["consumerKey"]
    secret=settings["consumerSecret"]
    accessToken=key+":"+secret
    accessToken=base64.b64encode(accessToken.encode('utf-8')).decode('utf-8')
    SetAccessToken(accessToken)
    return accessToken