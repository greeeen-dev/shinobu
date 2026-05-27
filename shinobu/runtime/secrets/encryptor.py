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
import zstandard
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Cipher import AES, ChaCha20_Poly1305
from Crypto import Hash
from Crypto import Random as CryptoRandom

available_mib: int = psutil.virtual_memory().total / 1048576

# Available algorithms
algo_available: list = [
    "aes-256-gcm",
    "xchacha20-poly1305" # Recommended
]

# Available KDFs
kdf_available: list = [
    "argon2", # Recommended
    "pbkdf2"
]

# KDF profiles
argon2_profiles: dict[str, argon2.Parameters] = {
    "argon2_high": argon2.profiles.RFC_9106_HIGH_MEMORY, # RFC9106 "FIRST RECOMMENDED" parameters, recommended for cold storage
    "argon2_low": argon2.profiles.RFC_9106_LOW_MEMORY # RFC9106 "SECOND RECOMMENDED" parameters, default, recommended for everything else (and when argon2_high isn't available)
}
pbkdf2_profiles: dict = {
    "pbkdf2_hmac_sha_256": {"hash": Hash.SHA256, "iterations": 600000}, # Default, recommended for PBKDF2
    "pbkdf2_hmac_sha_1": {"hash": Hash.SHA1, "iterations": 1300000} # Compatibility only, not recommended
}
kdf_profiles: dict[str, dict] = {
    "argon2": argon2_profiles,
    "pbkdf2": pbkdf2_profiles
}

# Available Argon2 profiles
argon2_available: list = [
    "argon2_low"
]

if available_mib >= 4096:
    # Enable high-memory profile
    # We need 2 GiB for argon2_high, so requiring 4 GiB is a safe minimum
    argon2_available.append("argon2_high")

# Available compression algorithms
compression_available: list[str] = [
    "zstd"
]

# Zstd profiles
zstd_available: list[str] = [
    "zstd_fast",
    "zstd_balanced",
    "zstd_best"
]

class EncryptedData:
    """A class representing data encrypted using any available algorithm."""

    def __init__(self, ciphertext: str, tag: str, nonce: str, salt: str, algorithm: str, kdf: str | None = None,
                 profile: str | None = None, compression: str | None = None, compression_profile: str | None = None,
                 raw: bool = False):
        self._ciphertext: str = ciphertext
        self._tag: str = tag
        self._nonce: str = nonce
        self._salt: str = salt
        self._algorithm: str = algorithm
        self._kdf: str = kdf or "pbkdf2"
        self._profile: str = profile or "pbkdf2_hmac_sha_1"
        self._compression: str | None = compression
        self._compression_profile: str | None = compression_profile
        self._raw: bool = raw
        self._outdated: bool = False

        if not profile and self._kdf == "pbkdf2":
            self._outdated = True

        if self._kdf not in kdf_available:
            raise ValueError("Invalid KDF")

        if self._profile not in kdf_profiles[self._kdf]:
            raise ValueError("Invalid KDF profile")

    @property
    def ciphertext(self) -> str:
        """Ciphertext generated after encryption in base64 format."""

        return self._ciphertext

    @property
    def tag(self) -> str:
        """Tag generated after encryption for MAC validation in base64 format."""

        return self._tag

    @property
    def nonce(self) -> str:
        """Nonce used for cipher derivation in base64 format."""

        return self._nonce

    @property
    def salt(self) -> str:
        """Salt used for key derivation in base64 format."""

        return self._salt

    @property
    def algorithm(self) -> str:
        """Algorithm used for encryption."""

        return self._algorithm

    @property
    def kdf(self) -> str:
        """KDF used for key derivation."""

        return self._kdf

    @property
    def profile(self) -> str:
        """KDF profile used for key derivation."""

        return self._profile

    @property
    def compression(self) -> str:
        """Compression algorithm used."""

        return self._compression

    @property
    def compression_profile(self) -> str:
        """Compression profile used."""

        return self._compression_profile

    @property
    def raw(self) -> bool:
        """Whether the original data was in bytes."""

        return self._raw

    @property
    def outdated(self) -> bool:
        """Indicates whether the secrets needs re-encrypting."""

        return self._outdated

    def to_dict(self) -> dict:
        """Returns the class data as a dict file (usually for on-disk storage)."""

        return {
            "ciphertext": self._ciphertext,
            "tag": self.tag,
            "nonce": self.nonce,
            "salt": self.salt,
            "algorithm": self.algorithm,
            "kdf": self.kdf,
            "profile": self.profile,
            "compression": self.compression,
            "compression_profile": self.compression_profile,
            "raw": self.raw
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'EncryptedData':
        """Creates a new EncryptedData object from a dict object."""

        if data.get("algorithm"):
            if data["algorithm"] not in algo_available:
                raise ValueError("Unsupported algorithm")

        return cls(
            ciphertext=data["ciphertext"],
            tag=data["tag"],
            nonce=data["nonce"],
            salt=data["salt"],
            algorithm=data.get("algorithm", "aes-256-gcm"),
            kdf=data.get("kdf", "pbkdf2"),
            profile=data.get("profile"),
            compression=data.get("compression"),
            compression_profile=data.get("compression_profile"),
            raw=data.get("raw", False)
        )

class GCMEncryptedData(EncryptedData):
    """A class representing data encrypted using AES-256-GCM."""

    def __init__(self, ciphertext: str, tag: str, nonce: str, salt: str, kdf: str | None = None,
                 profile: str | None = None, compression: str | None = None, compression_profile: str | None = None,
                 raw: bool = False):
        super().__init__(ciphertext, tag, nonce, salt, "aes-256-gcm", kdf=kdf, profile=profile,
                         compression=compression, compression_profile=compression_profile, raw=raw)

    @classmethod
    def from_dict(cls, data: dict) -> 'GCMEncryptedData':
        """Creates a new GCMEncryptedData object from a dict object.
        For most cases, you should use EncryptedData.from_dict(data)."""

        if data.get("algorithm"):
            if data["algorithm"] != "aes-256-gcm":
                raise ValueError("Not encrypted using AES-256-GCM")

        return cls(
            ciphertext=data["ciphertext"],
            tag=data["tag"],
            nonce=data["nonce"],
            salt=data["salt"],
            kdf=data.get("kdf", "pbkdf2"),
            profile=data.get("profile"),
            compression=data.get("compression"),
            compression_profile=data.get("compression_profile"),
            raw=data.get("raw", False)
        )


class XChaCha20EncryptedData(EncryptedData):
    """A class representing data encrypted using XChaCha20-Poly1305."""

    def __init__(self, ciphertext: str, tag: str, nonce: str, salt: str, kdf: str | None = None,
                 profile: str | None = None, compression: str | None = None, compression_profile: str | None = None,
                 raw: bool = False):
        super().__init__(ciphertext, tag, nonce, salt, "xchacha20-poly1305", kdf=kdf, profile=profile,
                         compression=compression, compression_profile=compression_profile, raw=raw)

    @classmethod
    def from_dict(cls, data: dict) -> 'XChaCha20EncryptedData':
        """Creates a new XChaCha20EncryptedData object from a dict object.
        For most cases, you should use EncryptedData.from_dict(data)."""

        if data.get("algorithm") != "xchacha20-poly1305":
            raise ValueError("Not encrypted using XChaCha20-Poly1305")

        return cls(
            ciphertext=data["ciphertext"],
            tag=data["tag"],
            nonce=data["nonce"],
            salt=data["salt"],
            kdf=data.get("kdf", "pbkdf2"),
            profile=data.get("profile"),
            compression=data.get("compression"),
            compression_profile=data.get("compression_profile"),
            raw=data.get("raw", False)
        )

class ZstdCompressor:
    # Level mapping
    level_mapping: dict[str, int] = {
        "zstd_fast": -1,
        "zstd_balanced": 3,
        "zstd_best": 22,
    }

    @staticmethod
    def compress(data: bytes, profile: str) -> bytes:
        level: int = ZstdCompressor.level_mapping.get(profile, 3)

        # Compress data
        compressor: zstandard.ZstdCompressor = zstandard.ZstdCompressor(level=level)
        return compressor.compress(data)

    @staticmethod
    def decompress(data: bytes) -> bytes:
        # Decompress data
        decompressor: zstandard.ZstdDecompressor = zstandard.ZstdDecompressor()
        return decompressor.decompress(data)

class BaseEncryptor:
    @staticmethod
    def decode_base64(data: EncryptedData):
        """Decodes base64 data for decryption."""

        nonce: bytes = base64.b64decode(data.nonce)
        tag: bytes = base64.b64decode(data.tag)
        salt: bytes = base64.b64decode(data.salt)
        ciphertext: bytes = base64.b64decode(data.ciphertext)
        return nonce, tag, salt, ciphertext

    @staticmethod
    def compress_bytes(data: bytes, compressor: str, compressor_profile: str) -> bytes:
        if compressor not in compression_available:
            raise ValueError("Invalid compressor. If we let you do this, you'd probably lose your data.")

        if compressor == "zstd":
            return ZstdCompressor.compress(data, compressor_profile)

        return data

    @staticmethod
    def decompress_bytes(data: bytes, compressor: str) -> bytes:
        if compressor not in compression_available:
            raise ValueError("Invalid compressor, you probably just lost your data. Congratulations.")

        if compressor == "zstd":
            return ZstdCompressor.decompress(data)

        return data

    @staticmethod
    def derive_password_hash(password: str, salt: bytes, kdf: str = "argon2", profile: str | None = None) -> bytearray:
        """Derives password hash using the KDF and KDF profile of choice."""

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
        hashed_password: bytearray | None = None

        if kdf == "argon2":
            if not profile in argon2_available:
                raise ValueError("Argon2 profile not available")

            argon2_profile: argon2.Parameters = argon2_profiles[profile]

            hashed_password = bytearray(argon2.low_level.hash_secret_raw(
                secret=password.encode(),
                salt=salt,
                time_cost=argon2_profile.time_cost,
                memory_cost=argon2_profile.memory_cost,
                parallelism=argon2_profile.parallelism,
                hash_len=argon2_profile.hash_len,
                type=argon2_profile.type,
                version=argon2_profile.version
            ))
        elif kdf == "pbkdf2":
            if not profile in pbkdf2_profiles:
                raise ValueError("PBKDF2 profile not available")

            hashed_password = bytearray(PBKDF2(
                password,
                salt,
                dkLen=32,
                count=pbkdf2_profiles[profile]["iterations"],
                hmac_hash_module=pbkdf2_profiles[profile]["hash"]
            ))

        return hashed_password

class GCMEncryptor(BaseEncryptor):
    @staticmethod
    def encrypt(plaintext_data: str | bytes, password: str, kdf: str = "argon2", profile: str | None = None,
                compression: str | None = None, compression_profile: str | None = None) -> GCMEncryptedData:
        """Encrypts a given string using AES-256-GCM and returns encrypted data."""

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

        # Compress data
        if compression and compression_profile:
            encoded = GCMEncryptor.compress_bytes(encoded, compression, compression_profile)

        # Create password hash from selected KDF
        key: bytearray = GCMEncryptor.derive_password_hash(password, salt, kdf=kdf, profile=profile)

        # Create encryption key
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)

        # Get ciphertext and tag
        result, tag = cipher.encrypt_and_digest(encoded)

        # Clear password hash
        for index in range(len(key)):
            key[index] = 0

        # Return GCMEncryptedData object
        return GCMEncryptedData(
            ciphertext=base64.b64encode(result).decode('ascii'),
            tag=base64.b64encode(tag).decode('ascii'),
            nonce=base64.b64encode(nonce).decode('ascii'),
            salt=base64.b64encode(salt).decode('ascii'),
            kdf=kdf,
            profile=profile,
            compression=compression,
            compression_profile=compression_profile
        )

    @staticmethod
    def decrypt(data: GCMEncryptedData | EncryptedData, password: str) -> str | bytes:
        """Decrypts data encrypted using AES-256-GCM."""

        # Decode base64 strings to bytes
        if data.algorithm != "aes-256-gcm":
            raise ValueError("Algorithm mismatch")

        nonce, tag, salt, ciphertext = BaseEncryptor.decode_base64(data)

        # Create password hash from selected KDF
        kdf: str = data.kdf
        profile: str = data.profile

        # Generate key
        key: bytearray = GCMEncryptor.derive_password_hash(password, salt, kdf=kdf, profile=profile)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)

        # Get result
        result: bytes = cipher.decrypt_and_verify(ciphertext, tag)

        # Clear password hash
        for index in range(len(key)):
            key[index] = 0

        # Decompress data
        if data.compression and data.compression_profile:
            result = GCMEncryptor.decompress_bytes(result, data.compression)

        if data.raw:
            return result
        else:
            return result.decode()

class XChaCha20Encryptor(BaseEncryptor):
    @staticmethod
    def encrypt(plaintext_data: str | bytes, password: str, kdf: str = "argon2", profile: str | None = None,
                compression: str | None = None, compression_profile: str | None = None) -> XChaCha20EncryptedData:
        """Encrypts a given string using XChaCha20-Poly1305 and returns encrypted data."""

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
        nonce: bytes = CryptoRandom.get_random_bytes(24)

        # Get bytes
        raw: bool = False
        if type(plaintext_data) is bytes:
            raw = True
            encoded = plaintext_data
        else:
            encoded: bytes = plaintext_data.encode()

        # Compress data
        if compression and compression_profile:
            encoded = XChaCha20Encryptor.compress_bytes(encoded, compression, compression_profile)

        # Create password hash from selected KDF
        key: bytearray = XChaCha20Encryptor.derive_password_hash(password, salt, kdf=kdf, profile=profile)

        # Create encryption key
        cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)

        # Get ciphertext and tag
        result, tag = cipher.encrypt_and_digest(encoded)

        # Clear password hash
        for index in range(len(key)):
            key[index] = 0

        # Return XChaCha20EncryptedData object
        return XChaCha20EncryptedData(
            ciphertext=base64.b64encode(result).decode('ascii'),
            tag=base64.b64encode(tag).decode('ascii'),
            nonce=base64.b64encode(nonce).decode('ascii'),
            salt=base64.b64encode(salt).decode('ascii'),
            kdf=kdf,
            profile=profile,
            compression=compression,
            compression_profile=compression_profile,
            raw=raw
        )

    @staticmethod
    def decrypt(data: XChaCha20EncryptedData | EncryptedData, password: str) -> str | bytes:
        """Decrypts data encrypted using XChaCha20-Poly1305."""

        if data.algorithm != "xchacha20-poly1305":
            raise ValueError("Algorithm mismatch")

        # Decode base64 strings to bytes
        nonce, tag, salt, ciphertext = BaseEncryptor.decode_base64(data)

        # Create password hash from selected KDF
        kdf: str = data.kdf
        profile: str = data.profile

        # Generate key
        key: bytearray = XChaCha20Encryptor.derive_password_hash(password, salt, kdf=kdf, profile=profile)
        cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)

        # Get result
        result: bytes = cipher.decrypt_and_verify(ciphertext, tag)

        # Clear password hash
        for index in range(len(key)):
            key[index] = 0

        # Decompress data
        if data.compression and data.compression_profile:
            result = XChaCha20Encryptor.decompress_bytes(result, data.compression)

        if data.raw:
            return result
        else:
            return result.decode()

class AutoEncryptor:
    """An encryptor that encrypts and decrypts data using multiple algorithms."""

    @staticmethod
    def encrypt(plaintext_data: str | bytes, password: str, algorithm: str = "xchacha20-poly1305", kdf: str = "argon2",
                profile: str | None = None, compression: str | None = None, compression_profile: str | None = None
                ) -> EncryptedData:
        """Encrypts a given string using the algorithm of choice and returns encrypted data.

        XChaCha20-Poly1305 (xchacha20-poly1305) algorithm with Argon2 KDF (argon2) using
        argon2_low profile (argon2_high for cold storage if available) is recommended."""

        if algorithm not in algo_available:
            raise ValueError(f"Invalid algorithm {algorithm}")

        if algorithm == "xchacha20-poly1305":
            return XChaCha20Encryptor.encrypt(
                plaintext_data, password, kdf=kdf, profile=profile, compression=compression,
                compression_profile=compression_profile
            )
        else:
            # Fallback to AES-256-GCM (although this should've been handled)
            return GCMEncryptor.encrypt(
                plaintext_data, password, kdf=kdf, profile=profile, compression=compression,
                compression_profile=compression_profile
            )

    @staticmethod
    def decrypt(data: EncryptedData, password: str) -> str | bytes:
        """Decrypts encrypted data."""

        if data.algorithm not in algo_available:
            raise ValueError(f"Invalid algorithm {data.algorithm}")

        if data.algorithm == "xchacha20-poly1305":
            return XChaCha20Encryptor.decrypt(data, password)
        else:
            # Fallback to AES-256-GCM (although this should've been handled)
            return GCMEncryptor.decrypt(data, password)

# Debug mode (generate a testing-only encryptor)
if __name__ == "__main__":
    random_plaintext_length = 100
    encryptor = AutoEncryptor()

    # Set encryption configs here
    algo = "xchacha20-poly1305"
    kdf_used = "argon2"
    kdf_profile = "argon2_low"

    algo_mapping = {
        "aes-256-gcm": "GCM",
        "xchacha20-poly1305": "XChaCha20"
    }
    kdf_mapping = {
        "argon2": "Argon2",
        "pbkdf2": "PBKDF2"
    }

    # Print available KDF and Profiles
    print("Available KDFs:")
    for kdf_entry in kdf_available:
        print(f"- {kdf_entry} ({', '.join(kdf_profiles[kdf_entry])})")
    print("")

    # Generate plaintext
    plaintext = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(random_plaintext_length)])
    print(f"Testing {algo_mapping[algo]}Encryptor encryption (KDF {kdf_mapping[kdf_used]}, {kdf_profile}) with {len(plaintext)}-char plaintext with password 'password'...")
    print("")

    # Test encryption
    stime = time.time()
    encrypted_data: EncryptedData = encryptor.encrypt(
        plaintext, "password", algorithm=algo, kdf=kdf_used, profile=kdf_profile, compression="zstd",
        compression_profile="zstd_balanced"
    )
    etime = time.time() - stime

    # Test decryption
    stime = time.time()
    decrypted_data: str = encryptor.decrypt(encrypted_data, "password")
    dtime = time.time() - stime

    # Print encrypted data
    print("Encrypted data info:")
    print(f"- ciphertext: {encrypted_data.ciphertext if len(plaintext) <= 1000 else '[omitted]'}")
    print(f"- ciphertext length: {len(encrypted_data.ciphertext)}")
    print(f"- tag: {encrypted_data.tag}")
    print(f"- nonce: {encrypted_data.nonce}")
    print(f"- salt: {encrypted_data.salt}")
    print(f"- algorithm: {encrypted_data.algorithm}")
    print(f"- kdf: {encrypted_data.kdf}")
    print(f"- kdf profile: {encrypted_data.profile}")
    print(f"- compressor: {encrypted_data.compression}")
    print(f"- compressor profile: {encrypted_data.compression_profile}")
    print(f"- duration: {round(etime * 1000, 2)}ms")
    print("")

    # Print decrypted data
    print("Decrypted data info:")
    print(f"- plaintext: {decrypted_data if len(plaintext) <= 1000 else '[omitted]'}")
    print(f"- duration: {round(dtime * 1000, 2)}ms")
    print("")

    # Test success!
    print("Encryptor works!")
