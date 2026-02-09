import requests, json, base64, os, hashlib, time
import auth.Token as Token
import data.globalData as Data
from lxml import etree

#사내 ETPXKRSS는 FileAct 미가입으로 Upload, Ack까지만 가능 -> 파일 Send는 가능하지만 Nack 떨어짐
#FileAct는 3개 파트로 분리되어있음
#Initiate -> Upload -> Complete
#Initiate: 파일의 대략적인 정보와 Requestor, Responder 정보 
#Upload: 실제 파일 Cloud(AWS?)로 업로드하는 파트(S3 Bucket PUT 참조 - 인터넷 검색하면 나옴)
#Complete: 파일 업로드 종료 알림 -> 실제 FileAct 메시지 생성
def SingleSendFileAct(path, settings):
    #1. 토큰, 인증서 값 읽어오기
    accessToken=Data.GetAccessToken()
    """
    with open(settings["privatePath"], "r") as f:
        private=f.read()
    with open(settings["certificatePath"], "r") as f:
        certificate=f.read()
    """
    
    #2. 파일 이름 읽어오기
    filename = path.split("\\")[-1]

    #3. 파일 크기와 MD5(해시) 계산 후 Base64 인코딩
    fileSize = os.path.getsize(path)
    md5_hasher = hashlib.md5()
    with open(path, "rb") as rf:
        for chunk in iter(lambda: rf.read(8192), b""):
            md5_hasher.update(chunk)
    file_digest_raw = md5_hasher.digest()
    fileDigestBase64 = base64.b64encode(file_digest_raw).decode('ascii')  # 24 chars (with ==)

    #4. Initiate시 필요한 값들 정의
    actionType="upload" #or download
    encryptionKey=settings["encryptionKey"] #AES256 암호화 시 사용할 32글자(고정) 키
    if len(encryptionKey) != 32:
        raise ValueError("<encryptionKey> must be 32 characters (AES256)")
    keyValue=base64.b64encode(encryptionKey.encode('utf-8')).decode('utf-8')
    raw_md5 = hashlib.md5(encryptionKey.encode('utf-8')).digest()
    keyDigest = base64.b64encode(raw_md5).decode('utf-8')
    senderReference=str(int(time.time()))+"."+filename
    serviceCode="swift.generic.fast!p"  #사내 서버 미가입으로 사용 불가
    requestor="ou=xxx,o=etpxkrss,o=swift"   
    responder="ou=xxx,o=etpxkrss,o=swift"
    messageType="type.FileAct"  #FileAct라 메시지 타입은 임의로 설정함
    fileLogicalName=filename
    body={
        #파일 정보
        "file_transfer_request":{
            "file_attributes":{
                "file_name":filename,
                "file_digest_alg":"MD5",
                "file_digest":fileDigestBase64,
                "file_size":fileSize
            },
            "file_operation":{
                "type":actionType
            },
            "encryption_attributes":{
                "key_alg":"AES256",
                "key_value":keyValue,
                "key_digest_alg":"MD5",
                "key_digest":keyDigest
            }
        },
        #송수신 정보
        "companion_info":{
            "sender_reference":senderReference,
            "service_code":serviceCode,
            "message_type":messageType,
            "requestor":requestor,
            "responder":responder,
            "file_logical_name":fileLogicalName
        }        
    }
    print("---------------------------------------------------------------")
    #bodyStr=json.dumps(body, indent=4)
    #print(bodyStr)
    bodyString=json.dumps(body, separators=(',', ':'))  #트래픽 줄이기 위해 공백 제거 -> 안하면 API콜 Reject
    url=settings["fileActUrl"]

    #5. !!!중요한부분!!!
    #Access를 통한 전송이 아니기 때문에 NR Signature로 무결성, 암호화 검증함
    #쿼리 보낼 Body, 공개키, 개인키, url을 사용해 실제 사용자가 맞는지 확인
    #아마 가장 많이 오류 날 부분으로 예상됨
    if settings["useHSM"]:
        signature=Token.create_nr_signature_hsm(settings["subject"], body, url)
    else:
        signature=Token.create_nr_signature(settings["subject"], Data.GetPrivateKey(), Data.GetCertificate(), body, url)

    headers={
        "Authorization":f"Bearer {accessToken}",
        "X-SWIFT-Signature":signature,
        "Content-Type":"application/json",
        "Accept":"application/json"
    }

    #6. FileAct Initiate
    response=requests.post(url, headers=headers, data=bodyString, proxies=settings["proxies"], verify=True).json()

    transferID=response["transfer_id"]
    uploadUrl=response["file_transfer_response"]["signed_urls"][0]["url"]

    signed = response["file_transfer_response"]["signed_urls"][0]
    uploadUrl = signed["url"]
    method = signed.get("method", "PUT").upper()
    fields = signed.get("fields")
    expected_ct = signed.get("content_type")

    #7. Upload 
    #Initiate시 URL 반환 -> S3 Bucket 방식으로 파일 업로드용
    #아래 코드는 PUT, POST 방식 구분 후 실제 파일 업로드하는 부분임
    with open(path, "rb") as f:
        if fields:
            # POST form (S3 POST-style): include provided fields and file
            data = fields.copy()
            files = {"file": (filename, f)}
            r = requests.post(uploadUrl, data=data, files=files, proxies=settings.get("proxies"), verify=True)
        elif method == "PUT":
            # PUT raw bytes; avoid adding extra headers unless signature expects them
            headers_put = {
                "Content-MD5": fileDigestBase64,                # base64(md5(file_bytes))
                "Content-Length": str(fileSize),
                "x-amz-server-side-encryption-customer-algorithm": "AES256",
                "x-amz-server-side-encryption-customer-key": keyValue,     # base64(key)
                "x-amz-server-side-encryption-customer-key-md5": keyDigest # base64(md5(key))
            }
            if expected_ct:
                headers_put["Content-Type"] = expected_ct
            r = requests.put(uploadUrl, data=f, headers=headers_put, proxies=settings.get("proxies"), verify=True)
        else:
            r = requests.post(uploadUrl, data=f, proxies=settings.get("proxies"), verify=True)

    #status_code로 예외 처리 추가 필요함

    #8. FileAct 업로드 Complete
    url=settings["fileActAckUrl"]
    url=url.replace("{transfer-id}",transferID)
    path={
        "transfer-id":transferID
    }
    #Complete 요청 시 body값에 빈 딕셔너리 값 넣어줘야 에러가 안남 -> 버그?
    response=requests.post(url, headers=headers, params=path, data="{}",proxies=settings["proxies"], verify=True)
    print(response.json())
    print("---------------------------------------------------------------")

    return None

#파일 감지 파트
#파일 처리 후 삭제하는 부분임 -> 실제 구현한다면 삭제 없이 백업 폴더로 옮기는게 좋을듯
def FileCollector(path, settings):
    print(path)
    print("---------------------------------------------------------------")
    #fileact
    response=SingleSendFileAct(path, settings)
    #fileact end
    os.remove(path)
    print(f'File {path} is processed and removed.')
    print("---------------------------------------------------------------")

#MD5 계산
def getHash(path, blocksize=8192):
    afile = open(path, 'rb')
    hasher = hashlib.md5()
    buf = afile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
    afile.close()
    return hasher.hexdigest()