from email import message
from urllib import request
import requests, json, base64
from Token import *
from messaging.MessageMaker import *


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

def SingleSendInterAct(messageData, settings):
    

def MessageCollector(path, settings):
    print("---------------------------------------------------------------")
    with open(path, 'r') as f:
        data=f.read()
    if data[0] == "{":
        messageData=MTParser(data)
        SingleSend(messageData, settings)
    elif data[0] == "<":
        messageData=MXParser(data)
        SingleSendInterAct(messageData, settings)
    os.remove(path)
    print(f'File {path} is processed and removed.')
    print("---------------------------------------------------------------")