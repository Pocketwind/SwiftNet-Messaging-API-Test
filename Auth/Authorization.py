import base64, time
from Auth.Token import *

#토큰 관리 위한 파트
#Messaging에서 JWT 방식 사용
def Auth(isJWTRequied, settings=None):
    if isJWTRequied:
        accessToken = JWTAuth(settings)
        return accessToken
    else:
        accessToken = BasicAuth(settings)
        return accessToken

#현재시간과 발급시간 비교해 만료시간이면 Refresh
#or 첫 발급이면 신규 발급
#or 할거 없으면 넘어감
def JWTAuth(settings):
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

#Messaging에서는 필요없는 파트
def BasicAuth(settings):
    key=settings["consumerKey"]
    secret=settings["consumerSecret"]
    accessToken=key+":"+secret
    accessToken=base64.b64encode(accessToken.encode('utf-8')).decode('utf-8')
    SetAccessToken(accessToken)
    return accessToken