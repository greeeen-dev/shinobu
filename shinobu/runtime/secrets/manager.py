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

import ujson as json
import traceback
import string
import copy
import base64
from Crypto.Random import random
from shinobu.runtime.secrets import encryptor

class RawEncryptor:
    """A raw encryptor"""
    def __init__(self, password):
        self.__password = password
        self.__encryptor: encryptor.AutoEncryptor = encryptor.AutoEncryptor()

    def encrypt(self, data) -> encryptor.EncryptedData:
        return self.__encryptor.encrypt(data, self.__password)

    def decrypt(self, encrypted_data: encryptor.EncryptedData) -> str:
        return self.__encryptor.decrypt(encrypted_data, self.__password)

class TokenStore:
    """Shinobu's secret manager. Should only be used in the context of the bootscript to enforce module-level
    isolation from the runtime."""

    def __init__(self, password: str, filename: str | None = None, debug: bool = False,
                 content_override: dict | None = None, onetime: list | None = None, read_only: bool = True,
                 write_only: bool = False):
        self.__encryptor: encryptor.AutoEncryptor = encryptor.AutoEncryptor()
        self.__password: str = password
        self.__filename: str = filename or '.secrets.json'
        self.__one_time: list = copy.copy(onetime) if onetime else []
        self.__accessed: list = []
        self.__read_only: bool = read_only
        self.__write_only: bool = write_only
        self.__data: dict = copy.copy(content_override) if content_override else {}
        self.__debug = debug

        # Prevent TokenStore from being read-only and write-only at the same time
        if read_only and write_only:
            raise ValueError("TokenStore can't be read-only AND write-only, make up your mind please")

        # Ensure password is given
        if not password:
            raise ValueError('Encryption password must be provided')

        # Create test key for decryption testing
        self._create_test_key()

        # Try to load data if possible
        try:
            self.load()
        except FileNotFoundError:
            pass

    @property
    def debug(self):
        return self.__debug

    @property
    def tokens(self):
        tokens = list(self.__data.keys())
        tokens.remove('test')
        return tokens

    @property
    def tokens_raw(self):
        return list(self.__data.keys())

    @property
    def accessed(self):
        return self.__accessed

    @property
    def read_only(self):
        return self.__read_only

    @property
    def write_only(self):
        return self.__write_only

    @property
    def needs_reencryption(self) -> bool:
        test_data: encryptor.EncryptedData = encryptor.EncryptedData.from_dict(self.__data['test'])
        return test_data.outdated

    def load(self, filename: str | None = None):
        if not filename:
            filename = self.__filename

        with open(filename, 'r') as file:
            self.__data = json.load(file)

    def _create_test_key(self):
        """Creates a test key for decryption testing."""
        if not 'test' in self.__data.keys():
            encrypted_data: encryptor.EncryptedData = self.__encryptor.encrypt(
                ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(16)]),
                self.__password
            )

            self.__data['test'] = encrypted_data.to_dict()

    def test_decrypt(self, password=None):
        # Ensure test key exists
        self._create_test_key()

        # noinspection PyBroadException
        try:
            test_data: encryptor.EncryptedData = encryptor.EncryptedData.from_dict(self.__data['test'])
            self.__encryptor.decrypt(test_data, password or self.__password)
        except:
            # We have an error here, perhaps the password is wrong?
            if self.__debug:
                traceback.print_exc()

            return False

        # If things go smoothly, we can signal that decryption works
        return True

    def retrieve(self, identifier):
        """Retrieves an encrypted secret."""

        # Prevent access for wrote-only mode
        if self.write_only:
            raise RuntimeError("TokenStore is in write-only mode")

        # Is this a one-time access secret?
        if identifier in self.__one_time:
            if identifier in self.__accessed:
                # Secret has already been accessed, prevent access
                raise ValueError('Secret has already been retrieved')

            # Allow access to secret, but prevent any further access attempts
            self.__accessed.append(identifier)

        # Create encrypted data object
        data: encryptor.EncryptedData = encryptor.EncryptedData.from_dict(self.__data[identifier])

        # Decrypt and return
        return self.__encryptor.decrypt(data, self.__password)

    def retrieve_raw(self, identifier):
        """Retrieves the ciphertext for a secret.
        This is useless on its own, as the salt, nonce, tag, and password are needed to decrypt the ciphertext."""

        return self.__data[identifier]['ciphertext']

    def add_token(self, identifier, token):
        """Adds a token."""

        # Prevent access for read-only mode
        if self.read_only:
            raise RuntimeError("TokenStore is in read-only mode")

        # Prevent overwriting tokens
        if identifier in self.__data.keys():
            raise KeyError('Secret already exists')

        # Encrypt and save token
        encrypted_data = encryptor.EncryptedData = self.__encryptor.encrypt(token, self.__password)
        self.__data.update({identifier: encrypted_data.to_dict()})
        self.save()
        return len(self.__data)

    def replace_token(self, identifier, token, password):
        """Replaces a secret. Password is required for confirmation."""

        # Prevent access for read-only mode
        if self.read_only:
            raise RuntimeError("TokenStore is in read-only mode")

        # Password prompt to prevent unauthorized token deletion
        if not self.test_decrypt(password=password):
            raise ValueError('Invalid password')

        if not identifier in self.tokens:
            raise KeyError('Token does not exist')

        if identifier == 'test':
            raise ValueError('Cannot replace token, this is needed for password verification')

        # Get new data
        encrypted_data: encryptor.EncryptedData = self.__encryptor.encrypt(token, self.__password)

        # Overwrite old secret
        self.__data.update({identifier: encrypted_data.to_dict()})
        self.save()

    def delete_token(self, identifier, password):
        """Removes a secret. Password is required for confirmation."""

        # Prevent access for read-only mode
        if self.read_only:
            raise RuntimeError("TokenStore is in read-only mode")

        # Password prompt to prevent unauthorized token deletion
        if not self.test_decrypt(password=password):
            raise ValueError('Invalid password')

        # Ensure token exists
        if not identifier in self.tokens:
            raise KeyError('Token does not exist')

        # Prevent test token deletion
        if identifier == 'test':
            raise ValueError('Cannot delete token, this is needed for password verification')

        # Delete token
        del self.__data[identifier]
        self.save()

        # Return remaining tokens
        return len(self.__data)

    def reencrypt(self, current_password, password):
        """Re-encrypts entire TokenStore data with a new password. Current password is required for confirmation."""

        # Prevent access for read-only mode
        if self.read_only:
            raise RuntimeError("TokenStore is in read-only mode")

        # Check password
        if not self.test_decrypt(password=current_password):
            raise ValueError('Invalid password')

        # Re-encrypt everything
        for key in self.__data.keys():
            token = self.retrieve(key)
            encrypted: encryptor.EncryptedData = self.__encryptor.encrypt(token, password)
            self.__data[key] = encrypted.to_dict()

        self.__password = password
        self.save()

    def save(self, filename: str | None = None):
        """Saves the current TokenStore state to a file."""

        # Prevent access for read-only mode
        if self.read_only:
            raise RuntimeError("TokenStore is in read-only mode")

        # Set default filename
        if not filename:
            filename = ".secrets.json"

        # Ensure test value exists
        self._create_test_key()

        # Write file
        with open(filename, 'w+') as file:
            # noinspection PyTypeChecker
            json.dump(self.__data, file)
