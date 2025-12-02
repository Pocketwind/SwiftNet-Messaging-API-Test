from importlib import simple
import json, base64, requests, time, math, jwt, random, re
from os import access
from data import *
from urllib.parse import urlparse
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import hashlib
from urllib.parse import urlparse
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import threading


proxies={
    "http":"http://10.10.3.101:48600",
    "https":"http://10.10.3.101:48600"
}

def ReadTokens(path="tokens.json"):
    try:
        with open(path, "r") as f:
            tokenStr=f.read()
            tokenJson=json.loads(tokenStr.replace("'", "\""))
            refreshToken=tokenJson.get("refresh_token")
            accessToken=tokenJson.get("access_token")
            refreshTokenExpiresIn=tokenJson.get("refresh_token_expires_in")
            expiresIn=tokenJson.get("expires_in")
            createdAt=tokenJson.get("created_at")
            token=TokenResponse(
                refreshToken=refreshToken,
                accessToken=accessToken,
                refreshTokenExpiresIn=refreshTokenExpiresIn,
                expiresIn=expiresIn,
                createdAt=createdAt
            )
            return token, True
            
    except FileNotFoundError:
        return None, False
    
def SaveTokens(token, path="tokens.json"):
    tokens={
        "refresh_token":token.refreshToken,
        "access_token":token.accessToken,
        "refresh_token_expires_in":token.refreshTokenExpiresIn,
        "expires_in":token.expiresIn,
        "created_at":token.createdAt
    }
    with open(path, "w") as f:
        f.write(str(tokens))
    

def GenerateNewTokens(url, consumerCred):
    accessTokenResponse=GetBearerToken(url, consumerCred)
    refreshToken=accessTokenResponse.get("refresh_token")
    accessToken=accessTokenResponse.get("access_token")
    refreshTokenExpiresIn=accessTokenResponse.get("refresh_token_expires_in")
    expiresIn=accessTokenResponse.get("expires_in")
    createdAt=int(time.time())
    token=TokenResponse(
        refreshToken=refreshToken,
        accessToken=accessToken,
        refreshTokenExpiresIn=refreshTokenExpiresIn,
        expiresIn=expiresIn,
        createdAt=createdAt
    )
    return token

def RefreshBasicToken(url, refreshToken, consumerCred, isJWT=False):
    requestKey=MakeRequestKey(consumerCred)
    headers={
        "Authorization":f"Basic {requestKey}"
    }
    body={
        "grant_type":"refresh_token",
        "refresh_token":f"{refreshToken}"
    }
    if isJWT:
        response=requests.post(url, headers=headers, data=body, proxies=proxies, verify=False)
    else:
        response=requests.post(url, headers=headers, data=body)
    responseJson=response.json()
    refreshToken=responseJson.get("refresh_token")
    accessToken=responseJson.get("access_token")
    refreshTokenExpiresIn=responseJson.get("refresh_token_expires_in")
    expiresIn=responseJson.get("expires_in")
    createdAt=int(time.time())
    token=TokenResponse(
        refreshToken=refreshToken,
        accessToken=accessToken,
        refreshTokenExpiresIn=refreshTokenExpiresIn,
        expiresIn=expiresIn,
        createdAt=createdAt
    )
    return token

def MakeRequestKey(consumerCred):
    requestKey=f"{consumerCred.consumerKey}:{consumerCred.consumerSecret}"
    requestKeyBase64=base64.b64encode(requestKey.encode('utf-8')).decode('utf-8')
    return requestKeyBase64

def GetBearerToken(url, consumerCred):
    requestKeyBase64=MakeRequestKey(consumerCred)
    headers={
        "Authorization":f"Basic {requestKeyBase64}"
    }
    body={
        "grant_type":"password",
        "username":"sandbox-id",
        "password":"sandbox-key"
    }
    response=requests.post(url, headers=headers, data=body)
    return response.json()

#-------------------------------JWT-------------------------------------

def GenerateNewTokensWithJWT(URL, jwtConfig):
    accessTokenResponse=GetBearerTokenWithJWT(URL, jwtConfig)
    refreshToken=accessTokenResponse.get("refresh_token")
    accessToken=accessTokenResponse.get("access_token")
    refreshTokenExpiresIn=accessTokenResponse.get("refresh_token_expires_in")
    expiresIn=accessTokenResponse.get("expires_in")
    createdAt=int(time.time())
    token=TokenResponse(
        refreshToken=refreshToken,
        accessToken=accessToken,
        refreshTokenExpiresIn=refreshTokenExpiresIn,
        expiresIn=expiresIn,
        createdAt=createdAt
    )
    return token

def CreateJWT(jwtConfig):
    currentTime=int(time.time())
    payload={
        "iss": jwtConfig.consumerKey,
        "aud": jwtConfig.audience,
        "sub": jwtConfig.subject,
        "jti": simpleJTI(),
        #Postman 예제 js는 ms단위
        #파이썬은 s 단위
        "exp": currentTime + jwtConfig.expirationTime,
        "iat": currentTime
    }
    header={
        "typ": "JWT",
        "alg": "RS256",
        "x5c": [jwtConfig.certificate
                .replace("-----BEGIN CERTIFICATE-----", "")
                .replace("-----END CERTIFICATE-----", "")
                .replace("\n", "")
                .replace("\r", "")
                .replace(" ", "")]
    }
    jwtToken=jwt.encode(payload, jwtConfig.privateKey, algorithm="RS256", headers=header)
    #with open("jwtToken.txt", "w") as f:
    #    f.write(jwtToken)
    return jwtToken

def GetBearerTokenWithJWT(url, jwtConfig):
    jwtToken = CreateJWT(jwtConfig)
    body={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwtToken,
        "scope": "swift.alliancecloud.api!p"
    }
    header={
        "Authorization": f"Basic {MakeRequestKey(ConsumerCredentials(jwtConfig.consumerKey, jwtConfig.consumerSecret))}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response=requests.post(url, headers=header, data=body, proxies=proxies, verify=False)
    responseJson=response.json()
    return responseJson

def simpleJTI():
    jti=""
    jtiCharacters="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-"
    for i in range(21):
        jti+=jtiCharacters[random.randint(0, len(jtiCharacters)-1)]
    return jti

def base64_add_padding(s):
    """base64 문자열에 패딩 추가"""
    return s + '=' * (4 - len(s) % 4) % 4

def base64_url_encode(data):
    """base64url 인코딩 (padding 제거)"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def base64_url_encode_with_padding(data):
    """base64url 인코딩 (padding 포함)"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    b64 = base64.urlsafe_b64encode(data).decode('utf-8')
    # padding 추가
    padding_needed = (4 - len(b64) % 4) % 4
    return b64 + ('=' * padding_needed)

def validate_x5c_header(entry, public_key):
    """인증서 헤더 검증"""
    if not entry.strip().startswith("-----BEGIN CERTIFICATE-----"):
        raise ValueError(f"Your '{public_key}' (Public Certificate) is missing the header '-----BEGIN CERTIFICATE-----'")

def validate_x5c_footer(entry, public_key):
    """인증서 푸터 검증"""
    if not entry.strip().endswith("-----END CERTIFICATE-----"):
        raise ValueError(f"Your '{public_key}' (Public Certificate) is missing the footer '-----END CERTIFICATE-----'")

# ...existing code...
def normalize_cert_to_x5c(pem_cert: str) -> str:
    # BEGIN/END 제거하고 모든 공백/개행 제거 -> 순수 base64 DER 문자열
    cert = pem_cert.replace("-----BEGIN CERTIFICATE-----", "") \
                   .replace("-----END CERTIFICATE-----", "")
    cert = re.sub(r'\s+', '', cert)
    return cert

def b64url_with_padding_from_str(s: str) -> str:
    b = base64.urlsafe_b64encode(s.encode('utf-8')).decode('utf-8')
    pad = (4 - len(b) % 4) % 4
    return b + ("=" * pad)

def create_nr_signature(sub, private_key_pem, certificate_pem, request_body, url):
    # 1) x5c 준비 (안전하게)
    x5c_cert = normalize_cert_to_x5c(certificate_pem)
    header = {"typ": "JWT", "alg": "RS256", "x5c": [x5c_cert]}

    # 2) audience
    parsed_url = urlparse(url)
    aud_dynamic = parsed_url.hostname + parsed_url.path
    if parsed_url.query:
        aud_dynamic += '?' + parsed_url.query

    # 3) JTI
    charset = "abcdefghijklmnopqrstuvwxyz0123456789"
    new_jti = ''.join(random.choice(charset) for _ in range(12))

    # 4) body 미니파이 (Postman과 동일하게)
    if isinstance(request_body, dict):
        body_string = json.dumps(request_body, separators=(',', ':'))  # minified
    else:
        body_string = request_body

    # 5) digest 계산 (Postman: stob64u -> addPadding -> SHA256 -> Base64)
    b64url_padded = b64url_with_padding_from_str(body_string)   # base64url with padding
    digest_hash = hashlib.sha256(b64url_padded.encode('utf-8')).digest()
    digest = base64.b64encode(digest_hash).decode('utf-8')     # standard Base64

    # 6) payload
    current_time = int(time.time())
    payload = {
        "aud": aud_dynamic,
        "sub": sub,
        "jti": new_jti,
        "exp": current_time + 300,
        "iat": current_time,
        "digest": digest
    }

    # 7) signing input (base64url WITHOUT padding)
    header_enc = base64.urlsafe_b64encode(json.dumps(header, separators=(',', ':')).encode('utf-8')).decode('utf-8').rstrip('=')
    payload_enc = base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':')).encode('utf-8')).decode('utf-8').rstrip('=')
    signing_input = f"{header_enc}.{payload_enc}"

    # 8) 서명 (RS256)
    private_key = serialization.load_pem_private_key(private_key_pem.encode('utf-8'), password=None)
    signature = private_key.sign(
        signing_input.encode('utf-8'),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    signature_enc = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')

    jwt_token = f"{signing_input}.{signature_enc}"
    return jwt_token


#Token Manager Thread------------------------------

_lock=threading.RLock()
_accessToken=""
consumerCred=""
expired=60*10
def SetAccessToken(token):
    global _accessToken
    _accessToken=token
def GetAccessToken():
    return _accessToken
