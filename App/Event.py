# -*- coding: utf-8 -*-
# @Time: 2024/7/28 19:55
# @FileName: Event.py
# @Software: PyCharm
# @GitHub: KimmyXYC
import aiohttp
import json
import tempfile
import xml.etree.ElementTree as ET
from loguru import logger
from datetime import datetime
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, ec


async def load_from_url():
    url = "https://android.googleapis.com/attestation/status"

    headers = {
        "Cache-Control": "max-age=0, no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"Error fetching data: {response.status}")
            return await response.json()


def parse_number_of_certificates(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    number_of_certificates = root.find('.//NumberOfCertificates')

    if number_of_certificates is not None:
        count = int(number_of_certificates.text.strip())
        return count
    else:
        raise Exception('No NumberOfCertificates found.')


def parse_certificates(xml_file, pem_number):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    pem_certificates = root.findall('.//Certificate[@format="pem"]')

    if pem_certificates is not None:
        pem_contents = [cert.text.strip() for cert in pem_certificates[:pem_number]]
        return pem_contents
    else:
        raise Exception("No Certificate found.")


def load_public_key_from_file(file_path):
    with open(file_path, 'rb') as key_file:
        public_key = serialization.load_pem_public_key(
            key_file.read(),
            backend=default_backend()
        )
    return public_key


def compare_keys(public_key1, public_key2):
    return public_key1.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ) == public_key2.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )


async def keybox_check(bot, message, document):
    file_info = await bot.get_file(document.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    with tempfile.NamedTemporaryFile(delete=True) as temp_file:
        temp_file.write(downloaded_file)
        temp_file.flush()
        try:
            pem_number = parse_number_of_certificates(temp_file.name)
            pem_certificates = parse_certificates(temp_file.name, pem_number)
        except Exception as e:
            logger.error(f"[Keybox Check][message.chat.id]: {e}")
            await bot.reply_to(message, e)
            return
    try:
        certificate = x509.load_pem_x509_certificate(
            pem_certificates[0].encode(),
            default_backend()
        )
    except Exception as e:
        logger.error(f"[Keybox Check][message.chat.id]: {e}")
        await bot.reply_to(message, e)
        return

    # Certificate Validity Verification
    serial_number = certificate.serial_number
    serial_number_string = hex(serial_number)[2:].lower()
    reply = f"🔐 *Serial number:* `{serial_number_string}`"
    subject = certificate.subject
    reply += f"\nℹ️ *Subject:* `"
    for rdn in subject:
        reply += f"{rdn.oid._name}={rdn.value}, "
    reply = reply[:-2]
    reply += "`"
    not_valid_before = certificate.not_valid_before
    not_valid_after = certificate.not_valid_after
    current_time = datetime.utcnow()
    is_valid = not_valid_before <= current_time <= not_valid_after
    if is_valid:
        reply += "\n✅ Certificate within validity period"
    elif current_time > not_valid_after:
        reply += "\n❌ Expired certificate"
    else:
        reply += "\n❌ Invalid certificate"

    # Keychain Authentication
    flag = True
    for i in range(pem_number - 1):
        son_certificate = x509.load_pem_x509_certificate(pem_certificates[i].encode(), default_backend())
        father_certificate = x509.load_pem_x509_certificate(pem_certificates[i + 1].encode(), default_backend())

        if son_certificate.issuer != father_certificate.subject:
            flag = False
            break
        signature = son_certificate.signature
        signature_algorithm = son_certificate.signature_algorithm_oid._name
        tbs_certificate = son_certificate.tbs_certificate_bytes
        public_key = father_certificate.public_key()
        try:
            if signature_algorithm in ['sha256WithRSAEncryption', 'sha1WithRSAEncryption', 'sha384WithRSAEncryption',
                                       'sha512WithRSAEncryption']:
                hash_algorithm = {
                    'sha256WithRSAEncryption': hashes.SHA256(),
                    'sha1WithRSAEncryption': hashes.SHA1(),
                    'sha384WithRSAEncryption': hashes.SHA384(),
                    'sha512WithRSAEncryption': hashes.SHA512()
                }[signature_algorithm]
                padding_algorithm = padding.PKCS1v15()
                public_key.verify(signature, tbs_certificate, padding_algorithm, hash_algorithm)
            elif signature_algorithm in ['ecdsa-with-SHA256', 'ecdsa-with-SHA1', 'ecdsa-with-SHA384',
                                         'ecdsa-with-SHA512']:
                hash_algorithm = {
                    'ecdsa-with-SHA256': hashes.SHA256(),
                    'ecdsa-with-SHA1': hashes.SHA1(),
                    'ecdsa-with-SHA384': hashes.SHA384(),
                    'ecdsa-with-SHA512': hashes.SHA512()
                }[signature_algorithm]
                padding_algorithm = ec.ECDSA(hash_algorithm)
                public_key.verify(signature, tbs_certificate, padding_algorithm)
            else:
                raise ValueError("Unsupported signature algorithms")
        except Exception as e:
            flag = False
            break
    if flag:
        reply += f"\n✅ Valid keychain"
    else:
        reply += f"\n❌ Invalid keychain"

    # Root Certificate Validation
    root_certificate = x509.load_pem_x509_certificate(pem_certificates[-1].encode(), default_backend())
    root_public_key = root_certificate.public_key()
    google_public_key = load_public_key_from_file("res/pem/google.pem")
    aosp_ec_public_key = load_public_key_from_file("res/pem/aosp_ec.pem")
    aosp_rsa_public_key = load_public_key_from_file("res/pem/aosp_rsa.pem")
    knox_public_key = load_public_key_from_file("res/pem/knox.pem")
    if compare_keys(root_public_key, google_public_key):
        reply += "\n✅ Google hardware attestation root certificate"
    elif compare_keys(root_public_key, aosp_ec_public_key):
        reply += "\n🟡 AOSP software attestation root certificate (EC)"
    elif compare_keys(root_public_key, aosp_rsa_public_key):
        reply += "\n🟡 AOSP software attestation root certificate (RSA)"
    elif compare_keys(root_public_key, knox_public_key):
        reply += "\n✅ Samsung Knox attestation root certificate"
    else:
        reply += "\n❌ Unknown root certificate"

    # Validation of certificate revocation
    try:
        status_json = await load_from_url()
    except Exception:
        with open("res/json/status.json", 'r', encoding='utf-8') as file:
            status_json = json.load(file)
            reply += "\n⚠️ Using local revoked keybox list"
    status = status_json['entries'].get(serial_number_string, None)
    if status is None:
        reply += "\n✅ Serial number not found in Google's revoked keybox list"
    else:
        reply += f"\n❌ Serial number found in Google's revoked keybox list\n🔍 *Reason:* `{status['reason']}`"
    reply += f"\n⏱ *Check Time (UTC):* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    await bot.reply_to(message, reply, parse_mode='Markdown')
