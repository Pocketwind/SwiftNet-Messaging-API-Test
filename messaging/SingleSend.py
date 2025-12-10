from email import message
from smtplib import SMTPSenderRefused
from urllib import request
import requests, json, base64
from Token import *
from messaging.MessageMaker import *
from lxml import etree

def SingleSend(messageData, settings):
    accessToken=GetAccessToken()
    with open(settings["privatePath"], "r") as f:
        private=f.read()
    with open(settings["certificatePath"], "r") as f:
        certificate=f.read()
    messagePayload=messageData['payload']
    #messagePayload=messagePayload.replace('\r\n', '\n')
    messagePayloadBase64=base64.b64encode(messagePayload.encode('utf-8')).decode('utf-8')
    body={
        "sender_reference":messageData['trn'],
        "message_type":f"fin.{messageData['finType']}",
        "sender":messageData['sender'],
        "receiver":messageData['receiver'],
        "payload": messagePayloadBase64
    }
    bodyString=json.dumps(body, separators=(',', ':'))
    url="https://api-test.swiftnet.sipn.swift.com/alliancecloud-test/v2/fin/messages"
    signature=create_nr_signature(settings["subject"], private, certificate, body, url)
    headers={
        "Authorization":f"Bearer {accessToken}",
        "X-SWIFT-Signature":signature,
        "Content-Type":"application/json",
        "Accept":"application/json"
    }
    response=requests.post(url, headers=headers, data=bodyString, proxies=settings["proxies"], verify=False)
    return response.json()

def SingleSendInterAct(path, settings):
    url="https://api-test.swiftnet.sipn.swift.com/alliancecloud-test/v2/interact/messages"
    with open(path, "r") as f:
        tree=etree.parse(path)
    root=tree.getroot()

    namespaces = {
    'Saa': 'urn:swift:saa:xsd:saa.2.0'
    }
    senderRef=root.xpath('//Saa:Header/Saa:Message/Saa:SenderReference/text()', namespaces=namespaces)[0]
    serviceCode=root.xpath('//Saa:Header/Saa:Message/Saa:NetworkInfo/Saa:Service/text()', namespaces=namespaces)[0]
    messageType=root.xpath('//Saa:Header/Saa:Message/Saa:MessageIdentifier/text()', namespaces=namespaces)[0]
    requestor=root.xpath('//Saa:Header/Saa:Message/Saa:Sender/Saa:DN/text()', namespaces=namespaces)[0]
    responder=root.xpath('//Saa:Header/Saa:Message/Saa:Receiver/Saa:DN/text()', namespaces=namespaces)[0]

    headerns={
        "head":"urn:iso:std:iso:20022:tech:xsd:head.001.001.02"
    }
    header=root.xpath(f"//head:AppHdr",namespaces=headerns)[0]
    headerStr=etree.tostring(header, encoding="unicode")

    docns={
        messageType[:4]:f"urn:iso:std:iso:20022:tech:xsd:{messageType}"
    }
    doc=root.xpath(f"//{messageType[:4]}:Document",namespaces=docns)[0]
    docStr=etree.tostring(doc, encoding="unicode")

    payload="<envelope:Envelope xmlns:envelope=\"urn:swift:xsd:envelope\">"
    payload+=headerStr
    payload+=docStr
    payload+="</envelope:Envelope>"

    print(senderRef)
    print(serviceCode)
    print(messageType)
    print(requestor)
    print(responder)
    #print(payload)

    accessToken=GetAccessToken()
    with open(settings["privatePath"], "r") as f:
        private=f.read()
    with open(settings["certificatePath"], "r") as f:
        certificate=f.read()
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
    signature=create_nr_signature(settings["subject"], private, certificate, body, url)
    headers={
        "Authorization":f"Bearer {accessToken}",
        "X-SWIFT-Signature":signature,
        "Content-Type":"application/json",
        "Accept":"application/json"
    }
    
    response=requests.post(url, headers=headers, data=bodyString, proxies=settings["proxies"], verify=False).json()
    print(response)
    return response

def MessageCollector(path, settings):
    print("---------------------------------------------------------------")
    with open(path, 'r') as f:
        data=f.read()
    f.close()
    if data[0] == "{":
        messageData=MTParser(data)
        SingleSend(messageData, settings)
    elif data[0] == "<":
        messageData=SingleSendInterAct(path, settings)
    os.remove(path)
    print(f'File {path} is processed and removed.')
    print("---------------------------------------------------------------")