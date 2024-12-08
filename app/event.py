# -*- coding: utf-8 -*-
# @Time: 2024/7/28 19:55
# @FileName: event.py
# @Software: PyCharm
# @GitHub: KimmyXYC
import aiohttp
import json
import tempfile
import time
import os
import xml.etree.ElementTree as ET
from loguru import logger
from datetime import datetime, timezone
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

    params = {
        "ts": int(time.time())
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                raise Exception(f"Error fetching data: {response.status}")
            return await response.json()


def get_device_ids_and_algorithms(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    results = []
    for keybox in root.findall('Keybox'):
        device_id = keybox.get('DeviceID')

        for key in keybox.findall('Key'):
            algorithm = key.get('algorithm')
            device_info = {
                'DeviceID': device_id if device_id else 'Unknown',
                'Algorithm': algorithm if algorithm else 'Unknown'
            }
            results.append(device_info)
    return results


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


def parse_private_key(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    private_key = root.find('.//PrivateKey')
    if private_key is not None:
        return private_key.text.strip()
    else:
        raise Exception("No PrivateKey found.")


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
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(downloaded_file)
        temp_file.flush()
        temp_file.close()
        try:
            pem_number = parse_number_of_certificates(temp_file.name)
            pem_certificates = parse_certificates(temp_file.name, pem_number)
            private_key = parse_private_key(temp_file.name)
            keybox_info = get_device_ids_and_algorithms(temp_file.name)
            os.remove(temp_file.name)
        except Exception as e:
            logger.error(f"[Keybox Check][message.chat.id]: {e}")
            await bot.reply_to(message, e)
            os.remove(temp_file.name)
            return
    try:
        certificate = x509.load_pem_x509_certificate(
            pem_certificates[0].encode(),
            default_backend()
        )
        try:
            private_key = serialization.load_pem_private_key(
                private_key.encode(),
                password=None,
                backend=default_backend()
            )
            check_private_key = True
        except Exception:
            check_private_key = False
    except Exception as e:
        logger.error(f"[Keybox Check][message.chat.id]: {e}")
        await bot.reply_to(message, e)
        return

    # Keybox Information
    reply = f"📱 *Device ID:* `{keybox_info[0]['DeviceID']}`"
    reply += f"\n🔑 *Algorithm:* `{keybox_info[0]['Algorithm']}`"
    reply += "\n----------------------------------------"

    # Certificate Validity Verification
    serial_number = certificate.serial_number
    serial_number_string = hex(serial_number)[2:].lower()
    reply += f"\n🔐 *Serial number:* `{serial_number_string}`"
    subject = certificate.subject
    reply += "\nℹ️ *Subject:* `"
    for rdn in subject:
        reply += f"{rdn.oid._name}={rdn.value}, "
    reply = reply[:-2]
    reply += "`"
    not_valid_before = certificate.not_valid_before_utc
    not_valid_after = certificate.not_valid_after_utc
    current_time = datetime.now(timezone.utc)
    is_valid = not_valid_before <= current_time <= not_valid_after
    if is_valid:
        reply += "\n✅ Certificate within validity period"
    elif current_time > not_valid_after:
        reply += "\n❌ Expired certificate"
    else:
        reply += "\n❌ Invalid certificate"

    # Private Key Verification
    if check_private_key:
        private_key_public_key = private_key.public_key()
        certificate_public_key = certificate.public_key()
        if compare_keys(private_key_public_key, certificate_public_key):
            reply += "\n✅ Matching private key and certificate public key"
        else:
            reply += "\n❌ Mismatched private key and certificate public key"
    else:
        reply += "\n❌ Invalid private key"

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
        except Exception:
            flag = False
            break
    if flag:
        reply += "\n✅ Valid keychain"
    else:
        reply += "\n❌ Invalid keychain"

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

    # Number of Certificates in Keychain
    if pem_number >= 4:
        reply += "\n🟡 More than 3 certificates in the keychain"

    # Validation of certificate revocation
    try:
        status_json = await load_from_url()
    except Exception:
        logger.error("Failed to fetch Google's revoked keybox list")
        with open("res/json/status.json", 'r', encoding='utf-8') as file:
            status_json = json.load(file)
            reply += "\n⚠️ Using local revoked keybox list"

    status = None
    for i in range(pem_number):
        certificate = x509.load_pem_x509_certificate(pem_certificates[i].encode(), default_backend())
        serial_number = certificate.serial_number
        serial_number_string = hex(serial_number)[2:].lower()
        if status_json['entries'].get(serial_number_string, None):
            status = status_json['entries'][serial_number_string]
            break
    if not status:
        reply += "\n✅ Serial number not found in Google's revoked keybox list"
    else:
        reply += f"\n❌ Serial number found in Google's revoked keybox list\n🔍 *Reason:* `{status['reason']}`"
    reply += f"\n⏱ *Check Time (UTC):* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    await bot.reply_to(message, reply, parse_mode='Markdown')
