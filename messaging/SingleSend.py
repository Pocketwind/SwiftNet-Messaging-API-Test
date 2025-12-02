from email import message
from urllib import request
import requests, json, base64
from Token import *
SUBJECT="cn=%3,cn=api,o=etpxkrss,o=swift"

proxies={
    "http":"http://10.10.3.101:48600",
    "https":"http://10.10.3.101:48600"
}

with open("private.txt", "r") as f:
    pri=f.read()
with open("certificate.txt", "r") as f:
    cert=f.read()

def SingleSend(GetAccessToken, messageData):
    accessToken=GetAccessToken()
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
    signature=create_nr_signature(SUBJECT, pri, cert, body, url)
    headers={
        "Authorization":f"Bearer {accessToken}",
        "X-SWIFT-Signature":signature,
        "Content-Type":"application/json",
        "Accept":"application/json"
    }
    response=requests.post(url, headers=headers, data=bodyString, proxies=proxies, verify=False)
    return response.json()