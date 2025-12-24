import threading

#토큰 값들 여러 스레드에서 돌려쓰기 때문에 Deadlock 방지 위한 Locking, 전역변수화
_lock=threading.Lock()
_accessToken=""
_refreshToken=""
_consumerCred=""
_consumerKey=""
_creationTime=-1
def SetAccessToken(token):
    global _accessToken
    with _lock:
        _accessToken=token
def GetAccessToken():
    with _lock:
        return _accessToken
def SetRefreshToken(token):
    global _refreshToken
    with _lock:
        _refreshToken=token
def GetRefreshToken():
    with _lock:
        return _refreshToken
def SetConsumerCred(cred):
    global _consumerCred
    with _lock:
        _consumerCred=cred
def GetConsumerCred():
    with _lock:
        return _consumerCred
def SetConsumerKey(cred):
    global _consumerKey
    with _lock:
        _consumerKey=cred
def GetConsumerKey():
    with _lock:
        return _consumerKey
def SetCreationTime(t):
    global _creationTime
    with _lock:
        _creationTime=t
def GetCreationTime():
    with _lock:
        return _creationTime