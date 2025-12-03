import os, json, base64

def MTParser(message):
    lines=message.split('\n')
    sender=lines[0][6:18]
    finType=lines[0][33:36]
    receiver=lines[0][36:48]
    payload=lines[1:-1]
    payload="\r\n".join(payload)
    trn=""
    for line in lines:
        if line.startswith(":20:"):
            trn=line[4:].strip()
            break
    data={
        "sender": sender,
        "finType": finType,
        "receiver": receiver,
        "payload": payload,
        "trn": trn
    }
    return data

def MTMaker(sender, receiver, block, mtype):
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
    result+="N}{3:{111:001}}{4:"
    result+=block
    result+="\n-}"

    return result

def MessageMaker(downloadPath, outputPath, ackPath):
    with open(downloadPath, "r") as f:
        file=json.load(f)
    for item in file:
        if isinstance(item.get("message"), dict):
            payload=base64.b64decode(item["message"]["payload"]).decode("utf-8")
            payload=payload.replace("\r","")
            sender=item["message"]["sender"]
            receiver=item["message"]["receiver"]
            mtype=item["message"]["message_type"].split(".")[1]
            messageId=item["distribution"]["id"]
            message=MTMaker(sender,receiver,payload,mtype)
            with open(f"{outputPath}/{messageId}.out", "w") as f:
                f.write(message)
        elif isinstance(item.get("transmission_report"), dict):
            #ack maker 만들어야함
            payload=base64.b64decode(item["transmission_report"]["message"]["payload"]).decode("utf-8")
            payload=payload.replace("\r","")
            item["transmission_report"]["message"]["payload"]=payload
            sender=item["transmission_report"]["message"]["sender"]
            receiver=item["transmission_report"]["message"]["receiver"]
            mtype=item["transmission_report"]["message"]["message_type"].split(".")[1]
            messageId=item["distribution"]["id"]
            with open(f"{ackPath}/{messageId}.ack", "w") as f:
                #f.write(payload)

                json.dump(item, f, indent=4)
        
