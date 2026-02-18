"""
Shinobu - Converse from anywhere, anytime.
Copyright (C) 2026-present  Green (@greeeen-dev)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import time
import base64
import random
import string
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Cipher import AES
from Crypto import Random as CryptoRandom

class GCMEncryptedData:
    def __init__(self, ciphertext: str, tag: str, nonce: str, salt: str):
        self._ciphertext: str = ciphertext
        self._tag: str = tag
        self._nonce: str = nonce
        self._salt: str = salt

    @property
    def ciphertext(self) -> str:
        return self._ciphertext

    @property
    def tag(self) -> str:
        return self._tag

    @property
    def nonce(self) -> str:
        return self._nonce

    @property
    def salt(self) -> str:
        return self._salt

    def to_dict(self) -> dict:
        return {
            "ciphertext": self._ciphertext,
            "tag": self.tag,
            "nonce": self.nonce,
            "salt": self.salt
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GCMEncryptedData':
        return cls(
            ciphertext=data["ciphertext"],
            tag=data["tag"],
            nonce=data["nonce"],
            salt=data["salt"]
        )

class GCMEncryptor:
    @staticmethod
    def encrypt(plaintext: str, password: str):
        """Encrypts a given string and returns encrypted data in base64 format."""
        # Generate random salt and nonce
        salt: bytes = CryptoRandom.get_random_bytes(16)
        nonce: bytes = CryptoRandom.get_random_bytes(12)
        encoded: bytes = plaintext.encode()

        # Create encryption key
        __key = PBKDF2(password, salt, dkLen=32, count=600000)
        __cipher = AES.new(__key, AES.MODE_GCM, nonce=nonce)
        result, tag = __cipher.encrypt_and_digest(encoded)

        # Return GCMEncryptedData object
        return GCMEncryptedData(
            ciphertext=base64.b64encode(result).decode('ascii'),
            tag=base64.b64encode(tag).decode('ascii'),
            nonce=base64.b64encode(nonce).decode('ascii'),
            salt=base64.b64encode(salt).decode('ascii')
        )

    @staticmethod
    def decrypt(data: GCMEncryptedData, password: str):
        """Decrypts a given encrypted object."""
        # Decode base64 strings to bytes
        nonce: bytes = base64.b64decode(data.nonce)
        tag: bytes = base64.b64decode(data.tag)
        salt: bytes = base64.b64decode(data.salt)
        data: bytes = base64.b64decode(data.ciphertext)

        # Generate key
        __key = PBKDF2(password, salt, dkLen=32, count=600000)
        __cipher = AES.new(__key, AES.MODE_GCM, nonce=nonce)

        # Return result
        result: bytes = __cipher.decrypt_and_verify(data, tag)
        return result.decode()

# Debug mode (generate a testing-only encryptor)
if __name__ == "__main__":
    random_plaintext_length = 100
    encryptor = GCMEncryptor()
    print(f"Testing GCMEncryptor encryption with {random_plaintext_length}-char plaintext with password 'password'...")

    # Generate plaintext
    plaintext = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(random_plaintext_length)])

    # Test encryption
    stime = time.time()
    encrypted_data: GCMEncryptedData = encryptor.encrypt(plaintext, "password")
    etime = time.time() - stime

    # Test decryption
    stime = time.time()
    decrypted_data: str = encryptor.decrypt(encrypted_data, "password")
    dtime = time.time() - stime

    # Print encrypted data
    print("Encrypted data info:")
    print(f"- ciphertext: {encrypted_data.ciphertext if random_plaintext_length <= 1000 else '[omitted]'}")
    print(f"- tag: {encrypted_data.tag}")
    print(f"- nonce: {encrypted_data.nonce}")
    print(f"- salt: {encrypted_data.salt}")
    print(f"- duration: {round(etime * 1000, 2)}ms")
    print("")

    # Print decrypted data
    print("Decrypted data info:")
    print(f"- plaintext: {decrypted_data if random_plaintext_length <= 1000 else '[omitted]'}")
    print(f"- duration: {round(dtime * 1000, 2)}ms")
    print("")

    # Test success!
    print("Encryptor works!")
