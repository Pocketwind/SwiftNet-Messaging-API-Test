import requests, json, base64, os, shutil
from Auth.Token import *
from messaging.MessageMaker import *
from lxml import etree
from Data.globalData import *

#fin - Send a FIN message to Alliance Cloud.
#MT 메시지 한번에 하나만 보내기 -> 여러개도 보내기 가능하지만 아직 구현하지 않음
#1초에 1~2개 전송 가능한 속도
#Block4 내용만 전송 가능
def SingleSend(messageData, settings):
    #1. 토큰, 키 가져오기
    accessToken=GetAccessToken()
    """
    with open(settings["privatePath"], "r") as f:
        private=f.read()
    with open(settings["certificatePath"], "r") as f:
        certificate=f.read()
    """
    
    #2. Block4 내용 Base64로 인코딩
    messagePayload=messageData['payload']
    #messagePayload=messagePayload.replace('\r\n', '\n')
    messagePayloadBase64=base64.b64encode(messagePayload.encode('utf-8')).decode('utf-8')

    #3. Body 제작 후 공백 제거
    body={
        "sender_reference":messageData['trn'],
        "message_type":f"fin.{messageData['finType']}",
        "sender":messageData['sender'],
        "receiver":messageData['receiver'],
        "payload": messagePayloadBase64
    }
    bodyString=json.dumps(body, separators=(',', ':'))
    url=settings["messageUrl"]

    #4. !!!중요한부분!!!
    #Access를 통한 전송이 아니기 때문에 NR Signature로 무결성, 암호화 검증함
    #쿼리 보낼 Body, 공개키, 개인키, url을 사용해 실제 사용자가 맞는지 확인
    #아마 가장 많이 오류 날 부분으로 예상됨
    signature=create_nr_signature(settings["subject"], GetPrivateKey(), GetCertificate(), body, url)

    #5. 만든 Signature 헤더에 포함시켜서 제작
    headers={
        "Authorization":f"Bearer {accessToken}",
        "X-SWIFT-Signature":signature,
        "Content-Type":"application/json",
        "Accept":"application/json"
    }

    #6. 실제 메시지 전송
    response=requests.post(url, headers=headers, data=bodyString, proxies=settings["proxies"], verify=True)
    if response.status_code == 201:
        return response.json()
    else:
        response=response.json()
        shutil.move()
        print("---------------------------------------------------------------")
        print(f"Error: {response["code"]}\n{response["text"]}")
        print("---------------------------------------------------------------")
        return response

#interact - Send an InterAct message to Alliance Cloud.
#fin 전송과 같은 방식이지만 XML 파싱 필요해서 상대적으로 느림
#한번에 여러개 보낼수 있지만 아직 구현하지 않음
#2~3초에 1개정도 전송 가능
def SingleSendInterAct(path, settings):
    url=settings["interActMessageUrl"]
    #1. 메시지 파일(XML) 읽어오기
    with open(path, "r") as f:
        tree=etree.parse(path)
    root=tree.getroot()

    #2. 전송에 필요한 값 추출
    namespaces = {
    'Saa': 'urn:swift:saa:xsd:saa.2.0'
    }
    senderRef=root.xpath('//Saa:Header/Saa:Message/Saa:SenderReference/text()', namespaces=namespaces)[0]
    serviceCode=root.xpath('//Saa:Header/Saa:Message/Saa:NetworkInfo/Saa:Service/text()', namespaces=namespaces)[0]
    messageType=root.xpath('//Saa:Header/Saa:Message/Saa:MessageIdentifier/text()', namespaces=namespaces)[0]
    requestor=root.xpath('//Saa:Header/Saa:Message/Saa:Sender/Saa:DN/text()', namespaces=namespaces)[0]
    responder=root.xpath('//Saa:Header/Saa:Message/Saa:Receiver/Saa:DN/text()', namespaces=namespaces)[0]

    #3. 메시지 비즈니스 헤더 추출
    headerns={
        "head":"urn:iso:std:iso:20022:tech:xsd:head.001.001.02"
    }
    header=root.xpath(f"//head:AppHdr",namespaces=headerns)[0]
    headerStr=etree.tostring(header, encoding="unicode")

    #4. 실제 전문 본문인 Document 부분 추출
    docns={
        messageType[:4]:f"urn:iso:std:iso:20022:tech:xsd:{messageType}"
    }
    doc=root.xpath(f"//{messageType[:4]}:Document",namespaces=docns)[0]
    docStr=etree.tostring(doc, encoding="unicode")

    #5. 메시지 전송 시 Payload에는 아래와 같은 <envelope></envelope> 태그로 감싸야함
    #메시지 Document는 필수 데이터
    #비즈니스 헤더는 있을때만 포함 -> 근데 없을 수가 없음
    payload="<envelope:Envelope xmlns:envelope=\"urn:swift:xsd:envelope\">"
    payload+=headerStr
    payload+=docStr
    payload+="</envelope:Envelope>"

    #6. FIN과 동일하게 NR Signature 만든 후 전송하는 API 콜 전송
    accessToken=GetAccessToken()
    """
    with open(settings["privatePath"], "r") as f:
        private=f.read()
    with open(settings["certificatePath"], "r") as f:
        certificate=f.read()
    """
    payloadBase64=base64.b64encode(payload.encode('utf-8')).decode('utf-8')
    body={
        "sender_reference":senderRef,
        "service_code":serviceCode,
        "message_type":messageType,
        "requestor":requestor,
        "responder":responder,
        "format":"MX",
        "payload":payloadBase64
    }
    bodyString=json.dumps(body, separators=(',', ':'))
    signature=create_nr_signature(settings["subject"], GetPrivateKey(), GetCertificate(), body, url)
    headers={
        "Authorization":f"Bearer {accessToken}",
        "X-SWIFT-Signature":signature,
        "Content-Type":"application/json",
        "Accept":"application/json"
    }
    
    response=requests.post(url, headers=headers, data=bodyString, proxies=settings["proxies"], verify=True)
    if response.status_code == 201:
        return response.json()
    else:
        response=response.json()
        shutil.move(path, settings["inputPath"] + "/failed/" + os.path.basename(path))
        print("---------------------------------------------------------------")
        print(f"Error: {response["code"]}\n{response["text"]}")
        print("---------------------------------------------------------------")
        return response

def SingleSendFIN(path, settings):
    with open(path, 'r') as f:
        data=f.read()
    #1. 토큰, 키 가져오기
    accessToken=GetAccessToken()
    messageData=MTParser(data)
    #2. Block4 내용 Base64로 인코딩
    messagePayload=messageData['payload']
    #messagePayload=messagePayload.replace('\r\n', '\n')
    messagePayloadBase64=base64.b64encode(messagePayload.encode('utf-8')).decode('utf-8')

    #3. Body 제작 후 공백 제거
    body={
        "sender_reference":messageData['trn'],
        "message_type":f"fin.{messageData['finType']}",
        "sender":messageData['sender'],
        "receiver":messageData['receiver'],
        "payload": messagePayloadBase64
    }
    bodyString=json.dumps(body, separators=(',', ':'))
    url=settings["messageUrl"]

    #4. !!!중요한부분!!!
    #Access를 통한 전송이 아니기 때문에 NR Signature로 무결성, 암호화 검증함
    #쿼리 보낼 Body, 공개키, 개인키, url을 사용해 실제 사용자가 맞는지 확인
    #아마 가장 많이 오류 날 부분으로 예상됨
    signature=create_nr_signature(settings["subject"], GetPrivateKey(), GetCertificate(), body, url)

    #5. 만든 Signature 헤더에 포함시켜서 제작
    headers={
        "Authorization":f"Bearer {accessToken}",
        "X-SWIFT-Signature":signature,
        "Content-Type":"application/json",
        "Accept":"application/json"
    }

    #6. 실제 메시지 전송
    response=requests.post(url, headers=headers, data=bodyString, proxies=settings["proxies"], verify=True)
    if response.status_code == 201:
        return response.json()
    else:
        response=response.json()
        shutil.move(path, settings["inputPath"] + "/failed/" + os.path.basename(path))
        print("---------------------------------------------------------------")
        print(f"Error: {response["code"]}\n{response["text"]}")
        print("---------------------------------------------------------------")
        return response
#메시지 파일 감지 시 MT/MX 구분하는 파트
#'{' 로 시작하면 MT
#'<' 로 시작하면 MX인 형태로 구분
def MessageCollector(path, settings):
    print(path)
    print("---------------------------------------------------------------")
    if path[-2:] == "in":
        with open(path, 'r') as f:
            data=f.read()
        f.close()
        if data[0] == "{":
            #messageData=MTParser(data)
            #SingleSend(messageData, settings)
            SingleSendFIN(path, settings)
        elif data[0] == "<":
            SingleSendInterAct(path, settings)
        os.remove(path)
        print(f'Message {path} is processed and removed.')
    print("---------------------------------------------------------------")