import base64, hashlib, hmac

def Validation(data):
    datasplit = data.split(".")
    text=datasplit[0]
    digest=datasplit[1]
    textDecoded=base64.b64decode(text.encode("utf-8")).decode("utf-8")
    
    hmacSecret=b"Abcd1234Abcd1234"
    expectedDigest=hmac.new(hmacSecret,textDecoded.encode("utf-8"),hashlib.sha256).hexdigest()

    if digest == expectedDigest:
        return True
    else:
        return False
def Decode(data):
    datasplit = data.split(".")
    text=datasplit[0]
    textDecoded=base64.b64decode(text.encode("utf-8")).decode("utf-8")
    return textDecoded

def Encode(data, secret):
    textB64=base64.b64encode(data.encode("utf-8")).decode("utf-8")
    digest=hmac.new(secret.encode("utf-8"),data.encode("utf-8"),hashlib.sha256).hexdigest()
    return f"{textB64}.{digest}"