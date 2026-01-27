from email import message
import requests, json, base64, os, shutil
from auth import HSM
import auth.Token as Token
import data.globalData as Data
import messaging.MessageMaker as MessageMaker
from lxml import etree


def SingleSendFIN(messageData, settings):
    accessToken = Data.GetAccessToken()
    payload=messageData["payload"]
    trn=messageData["trn"]
    mtype=messageData["mtype"]
    sender=messageData["sender"]
    receiver=messageData["receiver"]
    
    payloadB64=base64.b64encode(payload.encode("utf-8")).decode("utf-8")

    body={
        "sender_reference":trn,
        "message_type":mtype,
        "sender":sender,
        "receiver":receiver,
        "payload": payloadB64
    }
    bodyString=json.dumps(body, separators=(',', ':'))

    url=settings["messageUrl"]

    
    if settings["useHSM"]:
        signature=Token.create_nr_signature_hsm(settings["subject"], body, url)
    else:
        signature=Token.create_nr_signature(settings["subject"], Data.GetPrivateKey(), Data.GetCertificate(), body, url)

    header={
        "Authorization":f"Bearer {accessToken}",
        "X-SWIFT-Signature":signature,
        "Content-Type":"application/json",
        "Accept":"application/json"
    }

    response=requests.post(url, headers=header, data=bodyString, proxies=settings["proxies"], verify=True)
    if response.status_code == 201:
        return True
    else:
        response=response.json()
        raise Exception(f"{response["code"]}\n{response["text"]}")
    
def SingleSendInterAct(messageData, settings):
    accessToken = Data.GetAccessToken()
    senderRef=messageData["senderRef"]
    mtype=messageData["mtype"]
    requestor=messageData["requestor"]
    responder=messageData["responder"]
    serviceCode=messageData["serviceCode"]
    mformat=messageData["mformat"]
    payload=messageData["payload"]
    url=settings["interActMessageUrl"]

    payload=f"<envelope:Envelope xmlns:envelope=\"urn:swift:xsd:envelope\">{payload}</envelope:Envelope>"
    payloadB64=base64.b64encode(payload.encode("utf-8")).decode("utf-8")

    body={
        "sender_reference":senderRef,
        "service_code":serviceCode,
        "message_type":mtype,
        "requestor":requestor,
        "responder":responder,
        "format":mformat,
        "payload":payloadB64
    }

    bodyString=json.dumps(body, separators=(',', ':'))

    if settings["useHSM"]:
        signature=Token.create_nr_signature_hsm(settings["subject"], body, url)
    else:
        signature=Token.create_nr_signature(settings["subject"], Data.GetPrivateKey(), Data.GetCertificate(), body, url)
    
    header={
        "Authorization":f"Bearer {accessToken}",
        "X-SWIFT-Signature":signature,
        "Content-Type":"application/json",
        "Accept":"application/json"
    }

    response=requests.post(url, headers=header, data=bodyString, proxies=settings["proxies"], verify=True)
    if response.status_code == 201:
        return True
    else:
        response=response.json()
        raise Exception(f"{response["code"]}\n{response["text"]}")

def MessageCollector(path, settings):
    print(path)
    print("---------------------------------------------------------------")
    if path[-2:] == "in":
        with open(path, 'r') as f:
            data=f.read()
        f.close()
        try:
            if data[0] == "{":
                messageData=MessageMaker.MTParser(data)
                SingleSendFIN(messageData, settings)
            elif data[0] == "<":
                messageData=MessageMaker.MXParser(data)
                SingleSendInterAct(messageData, settings)
            os.remove(path)
            print(f'Message {path} is processed and removed.')
        except Exception as e:
            print(f"Message Input Error: {type(e).__name__}: {e}")
    print("---------------------------------------------------------------")