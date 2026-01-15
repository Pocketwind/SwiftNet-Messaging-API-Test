import base64, hashlib, hmac

def validation(data, secret):
    if isinstance(secret, str):
        secret=secret.encode("utf-8")

    if len(data) < 32:
        return False
    
    receivedHMAC=data[:32]
    receivedData=data[32:]
    expectedHMAC=hmac.new(secret,receivedData,hashlib.sha256).digest()

    #print(receivedHMAC)
    #print(expectedHMAC)

    if not hmac.compare_digest(receivedHMAC,expectedHMAC):
        return False
    else:
        return True
    
def encode(text, secret):
    if isinstance(secret, str):
        secret=secret.encode("utf-8")
    if isinstance(text, str):
        text=text.encode("utf-8")

    hashed=hmac.new(secret,text,hashlib.sha256).digest()
    return hashed + text

def decode(text, secret):
    if isinstance(secret, str):
        secret=secret.encode("utf-8")

    payload=text[32:]
    text=payload.decode("utf-8")
    
    return text