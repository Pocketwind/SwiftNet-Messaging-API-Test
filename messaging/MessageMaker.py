import json, base64, hashlib, hmac, struct, threading
from datetime import datetime
from lxml import etree
import data.globalData as Data
import messaging.SingleSend as SingleSend
import messaging.Watchdog as Watchdog
import data.hmacValidation as hv


class MessageMakerService:
    def __init__(self, settings, send_binary):
        self.settings = settings
        self.stop_event = threading.Event()
        self.send_binary = send_binary
        self.thread = None

    def _message_maker_callback(self, download_path):
        MessageMaker(download_path, self.settings, self.send_binary)

    def run_loop(self):
        Watchdog.ThreadWatchdog(self.settings["downloadPath"], self._message_maker_callback, self.stop_event)

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

#Input MT 메시지 Block4만 추출하기
#보낼때 block4 값만 보낼수있음
def MTParser(message):
    lines=message.split('\n')
    sender=lines[0][6:18]
    finType=lines[0][33:36]
    receiver=lines[0][36:48]
    block4=""
    start=0
    end=0
    #block4 시작 체크
    for i, line in enumerate(lines):
        if line[:-3] == "4:\n":
            start=i
            break
    #block4 끝 체크
    for i, line in enumerate(lines):
        if line == "-}":
            end=i
            break
    #MT전문에서 block4 추출
    payload=lines[start+1:end]
    #lines 배열 crlf로 붙이기
    payload="\r\n".join(payload)
    trn=""
    #trn 체크
    for line in lines:
        if line.startswith(":20:"):
            trn=line[4:].strip()
            break
    data={
        "sender": sender,
        "mtype": f"fin.{finType}",
        "receiver": receiver,
        "payload": payload,
        "trn": trn
    }
    return data

def MXParser(message):
    root=etree.fromstring(message.encode("utf-8"))

    namespaces = {
    'Saa': 'urn:swift:saa:xsd:saa.2.0'
    }
    senderRef=root.xpath('//Saa:Header/Saa:Message/Saa:SenderReference/text()', namespaces=namespaces)[0]
    serviceCode=root.xpath('//Saa:Header/Saa:Message/Saa:NetworkInfo/Saa:Service/text()', namespaces=namespaces)[0]
    mtype=root.xpath('//Saa:Header/Saa:Message/Saa:MessageIdentifier/text()', namespaces=namespaces)[0]
    requestor=root.xpath('//Saa:Header/Saa:Message/Saa:Sender/Saa:DN/text()', namespaces=namespaces)[0]
    responder=root.xpath('//Saa:Header/Saa:Message/Saa:Receiver/Saa:DN/text()', namespaces=namespaces)[0]

    headerns={
        "head":"urn:iso:std:iso:20022:tech:xsd:head.001.001.02"
    }
    header=root.xpath(f"//head:AppHdr",namespaces=headerns)[0]
    headerStr=etree.tostring(header, encoding="unicode")

    docns={
        mtype[:4]:f"urn:iso:std:iso:20022:tech:xsd:{mtype}"
    }
    doc=root.xpath(f"//{mtype[:4]}:Document",namespaces=docns)[0]
    docStr=etree.tostring(doc, encoding="unicode")

    payload=f"{headerStr}{docStr}"

    result={
        "senderRef":senderRef,
        "serviceCode":serviceCode,
        "mtype":mtype,
        "mformat":"MX",
        "requestor":requestor,
        "responder":responder,
        "payload":payload
    }

    return result
           
def SocketJSONReceiver(data):
    data = data.split(".")
    text=data[0]
    digest=data[1]
    #print(repr(text))
    #print(repr(digest))
    textDecoded=base64.b64decode(text.encode("utf-8")).decode("utf-8")

    
    hmacSecret=Data.GetSettings()["hmacSecret"]
    #expectedDigest=hmac.new(hmacSecret,textDecoded.encode("utf-8"),hashlib.sha256).hexdigest()
    expected=hv.Encode(textDecoded, hmacSecret)
    expected=expected.split(".")
    expectedDigest=expected[1]

    #print(f"{digest}\n{expectedDigest}")
    if digest == expectedDigest:
        print("Message is Validated")
    else:
        print("Message Data is Corrupted")
        return
    
    textJson=json.loads(textDecoded)
    #textJson["payload"]=base64.b64decode(textJson["payload"]).decode("utf-8")
    if textJson["mformat"] == "MT":
        SingleSend.SingleSendFIN(textJson, Data.GetSettings())
    elif textJson["mformat"] in ["MX", "AnyXML"]:
        SingleSend.SingleSendInterAct(textJson, Data.GetSettings())
    else:
        print("Unknown Message Format")
        return
    print("Message from Socket is processed")

def SocketBinaryReceiver(data):
    try:
        if len(data) < 32:
            return "Invalid HMAC Binary Data Format".encode("utf-8")
        
        receivedHMAC=data[:32]
        receivedData=data[32:]
        secret=Data.GetSettings()["hmacSecret"]
        expectedHMAC=hmac.new(secret.encode("utf-8"),receivedData,hashlib.sha256).digest()


        if not hmac.compare_digest(receivedHMAC,expectedHMAC):
            return "HMAC Binary Check Failed".encode("utf-8")
        
        payload=receivedData.decode("utf-8",errors="replace")
        payload=json.loads(payload)
        
        if payload["mformat"] == "MT":
            SingleSend.SingleSendFIN(payload, Data.GetSettings())
            trn=payload["trn"]
            return f"ACK {trn}".encode("utf-8")
        elif payload["mformat"] in ["MX", "AnyXML"]:
            SingleSend.SingleSendInterAct(payload, Data.GetSettings())
            senderRef=payload["senderRef"]
            return f"ACK {senderRef}".encode("utf-8")
        else:
            return "Invalid Data Format".encode("utf-8")

    except Exception as e:
        print(f"SocketBinaryReceiver Error:{e}")
        return "SocketBinaryReceiver Error".encode("utf-8")

#Output MT 메시지
#download한 데이터에서 실제 MT 전문 만들어내기
#MT 포맷 맞게 했는지 확인 필요함
def MTMaker(sender, receiver, block, mtype, item):
    result="{1:F01"
    if len(sender) == 8:
        sender+="XXXX"
    elif len(sender) == 11:
        sender+="X"
    if len(receiver) == 8:
        receiver+="XXXX"
    elif len(receiver) == 11:
        receiver+="X"
    result+=sender
    result+="1234567890}{2:O"
    result+=mtype
    result+=receiver
    result+=f"{item["message"]["network_info"]["session_number"]:04d}"
    result+=f"{item["message"]["network_info"]["sequence_number"]:06d}"
    result+=str(item["message"]["network_info"]["local_output_time"])[2:-2]
    result+="N}{3:{111:001}}{4:\n"
    result+=block
    result+="\n-}"

    return result

#MT Ack 전문 만들기
#다운로드한 Transmission Report에서 Ack 만들어내기
#Ack 구조를 잘 몰라서 패스
def MTAckMaker(sender,receiver,status,reason,payload, mdate,mtype,reference):
    #Response time 가끔 다르게 반환함
    try:
        dt=datetime.strptime(mdate,"%Y-%m-%dT%H:%M:%S.%fZ")
    except:
        dt=datetime.strptime(mdate,"%Y-%m-%dT%H:%M:%SZ")
    result="{1:F21"
    result+=sender
    result+="0000000000}{4:{177:"
    result+=dt.strftime("%y%m%d%H%M")
    result+="}{451:"
    #Nack
    if status == "Rejected":
        result+="1}{405:nnn}}{"
        result+="1:F01"
        result+=str(sender)
        result+="0000000000}{2:I"
        result+=str(mtype)
        result+=str(receiver)
        result+="N}{4:\n"
        result+=f":20:{reference}\n"
        result+=f":79:{reason}"
        result+="\n-}"
    #Ack
    else:
        result+="0}{108:"
        result+=f"{reference}"
        result+="}}{1:F01"
        result+=str(sender)
        result+="0000000000}{2:I"
        result+=str(mtype)
        result+=str(receiver)
        result+="N}{3:{108:"
        result+=str(reference)
        result+="}}{4:"
        result+=payload
        result+="\n-}"

    return result

#download한 데이터에서 실제 전문 추출
#Payload에 값이 들어있지만 Base64 인코딩 되어있으므로 디코딩 후 파서로 전문 제작
def MessageMaker(path, settings, SendBinary):
    with open(path, "r") as f:
        file=json.load(f)
    text=json.dumps(file,separators=(',', ':'))
    
    digest=hmac.new(settings["hmacSecret"].encode("utf-8"),text.encode("utf-8"),hashlib.sha256).digest()
    data=digest+text.encode("utf-8")
    length=struct.pack('>I', len(data))
    m=length+data

    response=SendBinary("10.10.20.181", 12345, m)
    print(response)
    #전문 Maker
    """
    for item in file:
        if isinstance(item.get("message"), dict):
            if item["distribution"]["service"]=="fin":
                payload=base64.b64decode(item["message"]["payload"]).decode("utf-8")
                payload=payload.replace("\r","")
                sender=item["message"]["sender"]
                receiver=item["message"]["receiver"]
                mtype=item["message"]["message_type"].split(".")[1]
                messageId=item["distribution"]["id"]
                message=MTMaker(sender,receiver,payload,mtype,item)
                with open(f"{outputPath}/{messageId}.out", "w") as f:
                    f.write(message)
            elif item["distribution"]["service"]=="interAct":
                payload=item["message"]["payload"]
                payload=base64.b64decode(payload).decode("utf-8")
                messageId=item["distribution"]["id"]
                with open(f"{outputPath}/{messageId}.mxout", "w") as f:
                    f.write(payload)
        elif isinstance(item.get("transmission_report"), dict):
            #ack maker 만들어야함
            if item["distribution"]["service"]=="fin":
                #Ack에 원본 전문 포함할지 설정 가능함, 지금은 off
                #payload=base64.b64decode(item["transmission_report"]["message"]["payload"]).decode("utf-8")
                #payload=payload.replace("\r","")
                #item["transmission_report"]["message"]["payload"]=payload
                sender=item["transmission_report"]["message"]["sender"]
                receiver=item["transmission_report"]["message"]["receiver"]
                mtype=item["transmission_report"]["message"]["message_type"].split(".")[1]
                messageId=item["distribution"]["id"]
                reference=item["transmission_report"]["sender_reference"]
                status=item["transmission_report"]["delivery_status"]
                if status=="Rejected":
                    reason=item["transmission_report"]["rejection_reason"]
                else:
                    reason=None
                mdate=item["transmission_report"]["response_date"]
                result=MTAckMaker(sender,receiver,status,reason,payload, mdate,mtype,reference)
                with open(f"{ackPath}/{messageId}.ack", "w") as f:
                    f.write(result)
            elif item["distribution"]["service"]=="interAct":
                payload=item["transmission_report"]["transmission_report_payload"]
                payload=base64.b64decode(payload).decode("utf-8")
                messageId=item["distribution"]["id"]
                with open(f"{ackPath}/{messageId}.mxack", "w") as f:
                    f.write(payload)
    """