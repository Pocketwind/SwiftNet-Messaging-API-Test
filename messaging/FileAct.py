import urllib.parse
import urllib.parse
import requests, json, base64
from Token import *
from messaging.MessageMaker import *
from lxml import etree
import hashlib

def SingleSendFileAct(path, settings):
    accessToken=GetAccessToken()
    with open(settings["privatePath"], "r") as f:
        private=f.read()
    with open(settings["certificatePath"], "r") as f:
        certificate=f.read()
    filename = path.split("\\")[-1]
    # compute file size and raw MD5, then base64-encode the raw digest
    fileSize = os.path.getsize(path)
    md5_hasher = hashlib.md5()
    with open(path, "rb") as rf:
        for chunk in iter(lambda: rf.read(8192), b""):
            md5_hasher.update(chunk)
    file_digest_raw = md5_hasher.digest()
    fileDigestBase64 = base64.b64encode(file_digest_raw).decode('ascii')  # 24 chars (with ==)
    actionType="upload" #or download
    encryptionKey="13c2f4184wjmuygjyghfs5fd5xc5xv6s" #32char
    keyValue=base64.b64encode(encryptionKey.encode('utf-8')).decode('utf-8')
    raw_md5 = hashlib.md5(encryptionKey.encode('utf-8')).digest()
    keyDigest = base64.b64encode(raw_md5).decode('utf-8')
    senderReference=str(int(time.time()))+"."+filename
    serviceCode="swift.generic.fast!p"
    requestor="ou=xxx,o=etpxkrss,o=swift"
    responder="ou=xxx,o=etpxkrss,o=swift"
    messageType="type.FileAct"
    fileLogicalName=filename
    body={
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
    bodyString=json.dumps(body, separators=(',', ':'))
    url=settings["fileActUrl"]
    signature=create_nr_signature(settings["subject"], private, certificate, body, url)
    headers={
        "Authorization":f"Bearer {accessToken}",
        "X-SWIFT-Signature":signature,
        "Content-Type":"application/json",
        "Accept":"application/json"
    }

    #Initiate File Upload
    response=requests.post(url, headers=headers, data=bodyString, proxies=settings["proxies"], verify=False).json()
    #print(response)
    transferID=response["transfer_id"]
    uploadUrl=response["file_transfer_response"]["signed_urls"][0]["url"]

    #Payload
    #PUT?
    signed = response["file_transfer_response"]["signed_urls"][0]
    uploadUrl = signed["url"]
    method = signed.get("method", "PUT").upper()
    fields = signed.get("fields")
    expected_ct = signed.get("content_type")

    #print("FileAct - signed object:", json.dumps(signed, indent=2))
    #print("FileAct - uploadUrl:", uploadUrl, "method:", method)

    # Do not add headers not included in the signature.
    with open(path, "rb") as f:
        if fields:
            # POST form (S3 POST-style): include provided fields and file
            data = fields.copy()
            files = {"file": (filename, f)}
            r = requests.post(uploadUrl, data=data, files=files, proxies=settings.get("proxies"), verify=False)
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
            r = requests.put(uploadUrl, data=f, headers=headers_put, proxies=settings.get("proxies"), verify=False)
        else:
            r = requests.post(uploadUrl, data=f, proxies=settings.get("proxies"), verify=False)

    #print("FileAct - upload response status:", r.status_code)
    #print("FileAct - upload response text:", r.text)

    #complete upload
    url=settings["fileActAckUrl"]
    url=url.replace("{transfer-id}",transferID)
    path={
        "transfer-id":transferID
    }
    response=requests.post(url, headers=headers, params=path, data="{}",proxies=settings["proxies"], verify=False)
    print(response.json())
    print("---------------------------------------------------------------")

    return None

def FileCollector(path, settings):
    print(path)
    print("---------------------------------------------------------------")
    #fileact
    response=SingleSendFileAct(path, settings)
    #fileact end
    os.remove(path)
    print(f'File {path} is processed and removed.')
    print("---------------------------------------------------------------")


def getHash(path, blocksize=8192):
    afile = open(path, 'rb')
    hasher = hashlib.md5()
    buf = afile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
    afile.close()
    return hasher.hexdigest()