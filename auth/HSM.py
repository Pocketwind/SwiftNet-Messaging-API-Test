import pkcs11, time, base64, json
from cryptography import x509
from cryptography.hazmat.primitives import serialization
import data.globalData as Data


def sign(data, id):
    lib = pkcs11.lib(r'C:\Windows\System32\eTPKCS11.dll')

    slots = lib.get_slots(token_present=False)
    slot = slots[0]  # 첫 슬롯 (pkcs11-tool --list-slots로 확인)
    token = slot.get_token()  # 또는 lib.get_tokens(token_present=False)[0]

    user_pin=Data.GetSettings()["hsmSecret"]
    with token.open(user_pin=user_pin) as session:
        key_id_bytes = bytes.fromhex(id)
        
        # ✅ ID로 정확히 Private Key 찾기
        priv_keys = list(session.get_objects({
            pkcs11.Attribute.CLASS: pkcs11.ObjectClass.PRIVATE_KEY,
            pkcs11.Attribute.ID: key_id_bytes   # 핵심!
        }))
        
        if priv_keys:
            priv_obj = priv_keys[0]
            mechanism = pkcs11.Mechanism.SHA256_RSA_PKCS
            signature = priv_obj.sign(data, mechanism=mechanism)
            return signature
    return None

def get_cert_pem(id):
    lib = pkcs11.lib(r'C:\Windows\System32\eTPKCS11.dll')

    slots = lib.get_slots(token_present=False)
    slot = slots[0]  # 첫 슬롯 (pkcs11-tool --list-slots로 확인)
    token = slot.get_token()  # 또는 lib.get_tokens(token_present=False)[0]

    user_pin=Data.GetSettings()["hsmSecret"]
    with token.open(user_pin=user_pin) as session:
        key_id_bytes = bytes.fromhex(id)
            
        
        certs = list(session.get_objects({
            pkcs11.Attribute.CLASS: pkcs11.ObjectClass.CERTIFICATE,
            pkcs11.Attribute.ID: key_id_bytes
        }))
        if certs:
            cert_pem = certs[0][pkcs11.Attribute.VALUE] 
            cert_pem = x509.load_der_x509_certificate(certs[0][pkcs11.Attribute.VALUE]).public_bytes(serialization.Encoding.PEM).decode()
            return cert_pem
    return None

def create_jwt(payload, id):
    cert_pem=get_cert_pem(id)

    lib = pkcs11.lib(r'C:\Windows\System32\eTPKCS11.dll')

    slots = lib.get_slots(token_present=False)
    slot = slots[0]  # 첫 슬롯 (pkcs11-tool --list-slots로 확인)
    token = slot.get_token()  # 또는 lib.get_tokens(token_present=False)[0]

    user_pin=Data.GetSettings()["hsmSecret"]
    with token.open(user_pin=user_pin) as session:
        key_id_bytes = bytes.fromhex(id)
        
        # ✅ ID로 정확히 Private Key 찾기
        priv_keys = list(session.get_objects({
            pkcs11.Attribute.CLASS: pkcs11.ObjectClass.PRIVATE_KEY,
            pkcs11.Attribute.ID: key_id_bytes   # 핵심!
        }))
        priv_obj = priv_keys[0]
        
        if priv_keys:
                header={
                    "typ": "JWT",
                    "alg": "RS256",
                    "x5c": [cert_pem
                            .replace("-----BEGIN CERTIFICATE-----", "")
                            .replace("-----END CERTIFICATE-----", "")
                            .replace("\n", "")
                            .replace("\r", "")
                            .replace(" ", "")]
                }
                header_b64 = base64url_encode(json.dumps(header))
                payload_b64 = base64url_encode(json.dumps(payload))
                signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
                try:
                    signature = priv_obj.sign(
                        signing_input, 
                        mechanism=pkcs11.Mechanism.SHA256_RSA_PKCS
                    )
                    signature_b64 = base64url_encode(signature)
                    jwt_token = f"{header_b64}.{payload_b64}.{signature_b64}"
                    #print(jwt_token)
                    return jwt_token
                except:
                    print("HSM JWT 생성 실패")
    return None



def base64url_encode(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    encoded = base64.urlsafe_b64encode(data)
    return encoded.rstrip(b'=').decode('utf-8')