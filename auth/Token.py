import json, base64, requests, time, jwt, random, re, hashlib
from urllib.parse import urlparse
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import threading
import auth.Authorization as Auth
import data.globalData as Data
import auth.HSM as HSM


class TokenRefreshService:
    def __init__(self, settings):
        self.settings = settings
        self.stop_event = threading.Event()
        self.thread = None
        self.service_name = "Refresh Token"

    def run_loop(self):
        while not self.stop_event.is_set():
            if self.stop_event.wait(self.settings["expirationTime"]):
                break
            try:
                access_token = Auth.Auth(True, self.settings)
                Data.SetAccessToken(access_token)
            except Exception as e:
                print(f"{self.service_name} Error:", type(e).__name__, e)

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self.run_loop)
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def join(self, timeout=5):
        if self.thread:
            self.thread.join(timeout=timeout)

#토큰 폐기
#API 예제 Postman에만 있음
#입력:
#   - Header: Password방식 토큰 (Basic Key)
#   - Body: 사용하던 Access Token
#반환:
#   - 값X
#   - 200이나 401, 400같은 Status Code만 옴
def RevokeToken(settings):
    url=settings["revokeUrl"]
    basicKey=MakeRequestKey(settings["consumerKey"],settings["consumerSecret"])
    header={
        "Authorization": f"Basic {basicKey}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    body={
        "token":Data.GetAccessToken()
    }
    response=requests.post(url,headers=header,data=body,proxies=settings["proxies"],verify=False, timeout=5)
    return response

#토큰 Refresh
#API 예제 Postman에만 있음
#입력:
#   - Header: Password방식 토큰 (Basic Key)
#   - Body: 사용했던 Access Token의 Refresh Token, <grant_type> 값
#반환:
#   - access_token: 새로 발급받은 Access Token
#   - refresh_token: 위의 새로 받은 토큰의 Refresh용 토큰
def RefreshToken(settings):
    requestKey=MakeRequestKey(settings["consumerKey"],settings["consumerSecret"])
    headers={
        "Authorization":f"Basic {requestKey}"
    }
    body={
        "grant_type":"refresh_token",
        "refresh_token":f"{Data.GetRefreshToken()}"
    }
    
    response=requests.post(settings["url"], 
                           headers=headers, 
                           data=body, 
                           proxies=settings["proxies"], 
                           verify=False,
                           timeout=5)

    responseJson=response.json()
    refreshToken=responseJson.get("refresh_token")
    accessToken=responseJson.get("access_token")

    return accessToken, refreshToken

#Password Grant방식의 토큰 만들기 -> 가장 기본적인 초기 요청 때 사용
#Developer Portal - API Providers - Authentication 참조
#Basic 방식 Auth - <Consumer Key>:<Consumer Secret> 로 붙인 후 Base64 인코딩한 값
#입력: Consumer 값 2개
#출력: 처리 후 Base64 인코딩한 값
def MakeRequestKey(key, secret):
    requestKey=f"{key}:{secret}"
    requestKeyBase64=base64.b64encode(requestKey.encode('utf-8')).decode('utf-8')
    return requestKeyBase64

#Messaging API에서는 사용하지 않는 부분
#Password Grant 인증에서 사용하는 파트
#거의 SwiftRef 같은 조회성 정보 Query에서만 사용함
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
    response=requests.post(url, headers=headers, data=body, timeout=5)
    return response.json()

#-------------------------------JWT-------------------------------------

#실제 Messaging에서 사용할 토큰 발급받는 부분
#GetBearerTokenWithJWT 참조
def GenerateNewTokensWithJWT(settings):
    accessTokenResponse=GetBearerTokenWithJWT(settings)
    refreshToken=accessTokenResponse.get("refresh_token")
    accessToken=accessTokenResponse.get("access_token")
    return accessToken, refreshToken

def CreateJWT(settings):
    currentTime=int(time.time())
    payload={
        "iss": settings["consumerKey"],
        "aud": settings["audience"],
        "sub": settings["subject"],
        "jti": simpleJTI(),
        #Postman 예제 js는 ms단위
        #파이썬은 s 단위
        "exp": currentTime + settings["expirationTime"],
        "iat": currentTime
    }
    header={
        "typ": "JWT",
        "alg": "RS256",
        "x5c": [Data.GetCertificate()
                .replace("-----BEGIN CERTIFICATE-----", "")
                .replace("-----END CERTIFICATE-----", "")
                .replace("\n", "")
                .replace("\r", "")
                .replace(" ", "")]
    }
    if settings["useHSM"]:
        jwtToken=HSM.create_jwt(payload, settings["hsmID"])
    else:
        jwtToken=jwt.encode(payload, Data.GetPrivateKey(), algorithm="RS256", headers=header)
    return jwtToken

#Messaging을 위한 Access Token 발급을 위한 부분
#필요한 값: JWT, setting안의 값, Basic 키
#입력: 
#   - Header: Basic Key
#   - Body: grant_type, assertion(JWT), scope - 자세한 값은 settings 참조
#반환:
#   - Access Token, Refresh Token
def GetBearerTokenWithJWT(settings):
    jwtToken = CreateJWT(settings)
    body={
        "grant_type": settings["grant_type"],
        "assertion": jwtToken,
        "scope": settings["scope"]
    }
    header={
        "Authorization": f"Basic {MakeRequestKey(settings["consumerKey"],settings["consumerSecret"])}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response=requests.post(settings["url"], headers=header, data=body, proxies=settings["proxies"], verify=False, timeout=5)
    responseJson=response.json()
    if responseJson.get("access_token") == None:
        raise Exception(f"Failed to get Access Token\n{responseJson}")
    return responseJson

#JWT 생성 위한 임의 문자열
#예시를 위한 간단한 구현이고, 실무에서는 더 복잡한 방식으로 사용해야함
def simpleJTI():
    jti=""
    jtiCharacters="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-"
    for i in range(21):
        jti+=jtiCharacters[random.randint(0, len(jtiCharacters)-1)]
    return jti

#Base64 문자열에 '=' 넣어서 갯수 맞추기
def base64_add_padding(s):
    return s + '=' * (4 - len(s) % 4) % 4

#Base64 문자열에서 '=' 제거하기
def base64_url_encode(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

#Base64 URL 인코딩시 '=' 안전하게 계산
def base64_url_encode_with_padding(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    b64 = base64.urlsafe_b64encode(data).decode('utf-8')
    # padding 추가
    padding_needed = (4 - len(b64) % 4) % 4
    return b64 + ('=' * padding_needed)

#인증서 포맷 검사
def validate_x5c_header(entry, public_key):
    if not entry.strip().startswith("-----BEGIN CERTIFICATE-----"):
        raise ValueError(f"Your '{public_key}' (Public Certificate) is missing the header '-----BEGIN CERTIFICATE-----'")

#인증서 포맷 검사
def validate_x5c_footer(entry, public_key):
    if not entry.strip().endswith("-----END CERTIFICATE-----"):
        raise ValueError(f"Your '{public_key}' (Public Certificate) is missing the footer '-----END CERTIFICATE-----'")

# 인증서 실제 값만 얻어내기
def normalize_cert_to_x5c(pem_cert: str) -> str:
    # BEGIN/END 제거하고 모든 공백/개행 제거 -> 순수 base64 DER 문자열
    cert = pem_cert.replace("-----BEGIN CERTIFICATE-----", "") \
                   .replace("-----END CERTIFICATE-----", "")
    cert = re.sub(r'\s+', '', cert)
    return cert

#URL 계산 
def b64url_with_padding_from_str(s: str) -> str:
    b = base64.urlsafe_b64encode(s.encode('utf-8')).decode('utf-8')
    pad = (4 - len(b) % 4) % 4
    return b + ("=" * pad)

#Postman 예제에서만 존재
#NR Signature 만드는 부분
#
def create_nr_signature(sub, private_key_pem, certificate_pem, request_body, url):
    # 1) 인증서 값만 추출 후 헤더 만들기
    x5c_cert = normalize_cert_to_x5c(certificate_pem)
    header = {"typ": "JWT", "alg": "RS256", "x5c": [x5c_cert]}

    # 2) audience -> API Call 할 url에서부터 얻어내는 값
    parsed_url = urlparse(url)
    aud_dynamic = parsed_url.hostname + parsed_url.path
    if parsed_url.query:
        aud_dynamic += '?' + parsed_url.query

    # 3) JTI -> 실무에서는 더 복잡한 방식으로 구현 필수
    charset = "abcdefghijklmnopqrstuvwxyz0123456789"
    new_jti = ''.join(random.choice(charset) for _ in range(12))

    # 4) body 미니파이 -> 쿼리 보낼때 트래픽 감소 위해 공백 모두 제거함
    if isinstance(request_body, dict):
        body_string = json.dumps(request_body, separators=(',', ':'))  # minified
    else:
        body_string = request_body

    # 5) digest 계산 (Postman: stob64u -> addPadding -> SHA256 -> Base64)
    b64url_padded = b64url_with_padding_from_str(body_string)   # base64url with padding
    digest_hash = hashlib.sha256(b64url_padded.encode('utf-8')).digest()
    digest = base64.b64encode(digest_hash).decode('utf-8')     # standard Base64

    # 6) JWT에 들어가는 값
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

def create_nr_signature_hsm(sub, request_body, url):
    # 1) 인증서 값만 추출 후 헤더 만들기
    certificate_pem = Data.GetCertificate()
    x5c_cert = normalize_cert_to_x5c(certificate_pem)
    header = {"typ": "JWT", "alg": "RS256", "x5c": [x5c_cert]}

    # 2) audience -> API Call 할 url에서부터 얻어내는 값
    parsed_url = urlparse(url)
    aud_dynamic = parsed_url.hostname + parsed_url.path
    if parsed_url.query:
        aud_dynamic += '?' + parsed_url.query

    # 3) JTI -> 실무에서는 더 복잡한 방식으로 구현 필수
    charset = "abcdefghijklmnopqrstuvwxyz0123456789"
    new_jti = ''.join(random.choice(charset) for _ in range(12))

    # 4) body 미니파이 -> 쿼리 보낼때 트래픽 감소 위해 공백 모두 제거함
    if isinstance(request_body, dict):
        body_string = json.dumps(request_body, separators=(',', ':'))  # minified
    else:
        body_string = request_body

    # 5) digest 계산 (Postman: stob64u -> addPadding -> SHA256 -> Base64)
    b64url_padded = b64url_with_padding_from_str(body_string)   # base64url with padding
    digest_hash = hashlib.sha256(b64url_padded.encode('utf-8')).digest()
    digest = base64.b64encode(digest_hash).decode('utf-8')     # standard Base64

    # 6) JWT에 들어가는 값
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
    id=Data.GetSettings()["hsmID"]
    signature=HSM.sign(signing_input, id)
    signature_enc = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')

    jwt_token = f"{signing_input}.{signature_enc}"
    return jwt_token

def ThreadTokenRefresh(settings, stopEvent):
    service = TokenRefreshService(settings)
    service.stop_event = stopEvent
    service.run_loop()

            