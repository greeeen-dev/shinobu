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
import argon2
import psutil
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Cipher import AES
from Crypto import Hash
from Crypto import Random as CryptoRandom

available_mib: int = psutil.virtual_memory().total / 1048576

# Available KDFs
kdf_available: list = [
    "pbkdf2", "argon2"
]

# KDF profiles
argon2_profiles: dict[str, argon2.Parameters] = {
    "argon2_high": argon2.profiles.RFC_9106_HIGH_MEMORY,
    "argon2_low": argon2.profiles.RFC_9106_LOW_MEMORY
}
pbkdf2_profiles: dict = {
    "pbkdf2_hmac_sha_256": Hash.SHA256,
    "pbkdf2_hmac_sha_1": Hash.SHA1,
}
kdf_profiles: dict[str, dict] = {
    "argon2": argon2_profiles,
    "pbkdf2": pbkdf2_profiles
}

# Available Argon2 profiles
argon2_available: list = [
    "argon2_low"
]
if available_mib >= 2048:
    # Enable high-memory profile
    argon2_available.append("argon2_high")

class GCMEncryptedData:
    def __init__(self, ciphertext: str, tag: str, nonce: str, salt: str, kdf: str | None = None,
                 profile: str | None = None):
        self._ciphertext: str = ciphertext
        self._tag: str = tag
        self._nonce: str = nonce
        self._salt: str = salt
        self._kdf: str = kdf or "pbkdf2"
        self._profile: str = profile or "pbkdf2_hmac_sha_1"
        self._outdated: bool = False

        if not profile and self._kdf == "pbkdf2":
            self._outdated = True

        if self._kdf not in kdf_available:
            raise ValueError("Invalid KDF")

        if self._profile not in kdf_profiles[self._kdf]:
            raise ValueError("Invalid KDF profile")

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

    @property
    def kdf(self) -> str:
        return self._kdf

    @property
    def profile(self) -> str:
        return self._profile

    @property
    def outdated(self) -> bool:
        """Indicates whether the secrets needs re-encrypting."""
        return self._outdated

    def to_dict(self) -> dict:
        return {
            "ciphertext": self._ciphertext,
            "tag": self.tag,
            "nonce": self.nonce,
            "salt": self.salt,
            "kdf": self.kdf,
            "profile": self.profile
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GCMEncryptedData':
        return cls(
            ciphertext=data["ciphertext"],
            tag=data["tag"],
            nonce=data["nonce"],
            salt=data["salt"],
            kdf=data.get("kdf", "pbkdf2"),
            profile=data.get("profile")
        )

class GCMEncryptor:
    @staticmethod
    def derive_password_hash(password: str, salt: bytes, kdf: str = "argon2", profile: str | None = None):
        if kdf and kdf not in kdf_available:
            raise ValueError("Invalid KDF")

        # Get KDF profile
        if not profile:
            if kdf == "argon2":
                # For compatibility sake, we will use second-recommended Argon2 profile
                profile = "argon2_low"
            elif kdf == "pbkdf2":
                profile = "pbkdf2_hmac_sha_256"

        # Create password hash from selected KDF
        hashed_password: bytes | None = None

        if kdf == "argon2":
            if not profile in argon2_available:
                raise ValueError("Argon2 profile not available")

            argon2_profile: argon2.Parameters = argon2_profiles[profile]

            hashed_password = argon2.low_level.hash_secret_raw(
                secret=password.encode(),
                salt=salt,
                time_cost=argon2_profile.time_cost,
                memory_cost=argon2_profile.memory_cost,
                parallelism=argon2_profile.parallelism,
                hash_len=argon2_profile.hash_len,
                type=argon2_profile.type,
                version=argon2_profile.version
            )
        elif kdf == "pbkdf2":
            if not profile in pbkdf2_profiles:
                raise ValueError("PBKDF2 profile not available")

            hashed_password = PBKDF2(password, salt, dkLen=32, count=600000, hmac_hash_module=pbkdf2_profiles[profile])

        return hashed_password

    @staticmethod
    def encrypt(plaintext_data: str, password: str, kdf: str = "argon2", profile: str | None = None):
        """Encrypts a given string and returns encrypted data in base64 format."""
        if kdf and kdf not in kdf_available:
            raise ValueError("Invalid KDF")

        # Get KDF profile
        if not profile:
            if kdf == "argon2":
                # For compatibility sake, we will use second-recommended Argon2 profile
                profile = "argon2_low"
            elif kdf == "pbkdf2":
                profile = "pbkdf2_hmac_sha_256"

        # Generate random salt and nonce
        salt: bytes = CryptoRandom.get_random_bytes(16)
        nonce: bytes = CryptoRandom.get_random_bytes(12)
        encoded: bytes = plaintext_data.encode()

        # Create password hash from selected KDF
        __key: bytes = GCMEncryptor.derive_password_hash(password, salt, kdf=kdf, profile=profile)

        # Create encryption key
        __cipher = AES.new(__key, AES.MODE_GCM, nonce=nonce)
        result, tag = __cipher.encrypt_and_digest(encoded)

        # Return GCMEncryptedData object
        return GCMEncryptedData(
            ciphertext=base64.b64encode(result).decode('ascii'),
            tag=base64.b64encode(tag).decode('ascii'),
            nonce=base64.b64encode(nonce).decode('ascii'),
            salt=base64.b64encode(salt).decode('ascii'),
            kdf=kdf,
            profile=profile
        )

    @staticmethod
    def decrypt(data: GCMEncryptedData, password: str):
        """Decrypts a given encrypted object."""
        # Decode base64 strings to bytes
        nonce: bytes = base64.b64decode(data.nonce)
        tag: bytes = base64.b64decode(data.tag)
        salt: bytes = base64.b64decode(data.salt)
        ciphertext: bytes = base64.b64decode(data.ciphertext)

        # Create password hash from selected KDF
        __key: bytes | None = None
        kdf: str = data.kdf
        profile: str = data.profile

        # Generate key
        __key = GCMEncryptor.derive_password_hash(password, salt, kdf=kdf, profile=profile)
        __cipher = AES.new(__key, AES.MODE_GCM, nonce=nonce)

        # Return result
        result: bytes = __cipher.decrypt_and_verify(ciphertext, tag)
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
    encrypted_data: GCMEncryptedData = encryptor.encrypt(plaintext, "password", kdf="pbkdf2", profile="pbkdf2_hmac_sha_256")
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
    print(f"- kdf: {encrypted_data.kdf}")
    print(f"- kdf profile: {encrypted_data.profile}")
    print(f"- duration: {round(etime * 1000, 2)}ms")
    print("")

    # Print decrypted data
    print("Decrypted data info:")
    print(f"- plaintext: {decrypted_data if random_plaintext_length <= 1000 else '[omitted]'}")
    print(f"- duration: {round(dtime * 1000, 2)}ms")
    print("")

    # Test success!
    print("Encryptor works!")
