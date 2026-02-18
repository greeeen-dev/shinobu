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

import sys
import traceback
import getpass
from shinobu.runtime.secrets import manager

class ShinobuSecretsCLI:
    def __init__(self, tokenstore: manager.TokenStore):
        self._tokenstore: manager.TokenStore = tokenstore

    @property
    def commands(self) -> dict:
        """Returns a mapping of CLI commands."""

        return {
            'add-token': self.add_token,
            'replace-token': self.replace_token,
            'delete-token': self.delete_token,
            'list-tokens': self.list_tokens,
            'reencrypt-tokens': self.reencrypt_tokens,
            'help': self.command_help,
            'exit': lambda: sys.exit(0)
        }

    def add_token(self):
        identifier = input('Token identifier: ').upper()
        if identifier == '':
            print('\x1b[31;1mIdentifier cannot be empty.\x1b[0m')
            return
        token = getpass.getpass('Token: ')

        try:
            tokens = self._tokenstore.add_token(identifier, token)
        except KeyError:
            print('\x1b[31;1mToken already exists.\x1b[0m')
            return

        print(f'\x1b[36;1mToken added successfully. You now have {tokens - 1} tokens.\x1b[0m')

    def replace_token(self):
        identifier = input('Token identifier: ').upper()
        if identifier == '':
            print('\x1b[31;1mIdentifier cannot be empty.\x1b[0m')
            return
        token = getpass.getpass('New token: ')
        password = getpass.getpass('Encryption password: ')

        print('\x1b[37;41;1mWARNING: THIS TOKEN WILL BE REPLACED!\x1b[0m')
        print('\x1b[33;1mThis process is irreversible. Once it\'s done, there\'s no going back!\x1b[0m')
        print()
        print('\x1b[33;1mProceed anyways? (y/n)\x1b[0m')

        try:
            confirm = input().lower()
            if not confirm == 'y':
                raise ValueError()
        except (ValueError, KeyboardInterrupt):
            print('\x1b[31;1mAborting.\x1b[0m')
            return

        try:
            self._tokenstore.replace_token(identifier, token, password)
        except KeyError:
            print('\x1b[31;1mToken does not exist.\x1b[0m')
            return
        except ValueError:
            print('\x1b[31;1mInvalid password. Your encryption password is needed to replace or delete tokens.\x1b[0m')
            return

        print('\x1b[36;1mToken replaced successfully.\x1b[0m')

    def delete_token(self):
        identifier = input('Token identifier: ').upper()
        if identifier == '':
            print('\x1b[31;1mIdentifier cannot be empty.\x1b[0m')
            return
        password = getpass.getpass('Encryption password: ')

        print('\x1b[37;41;1mWARNING: THIS TOKEN WILL BE DELETED!\x1b[0m')
        print('\x1b[33;1mThis process is irreversible. Once it\'s done, there\'s no going back!\x1b[0m')
        print()
        print('\x1b[33;1mProceed anyways? (y/n)\x1b[0m')

        try:
            confirm = input().lower()
            if not confirm == 'y':
                raise ValueError()
        except (ValueError, KeyError):
            print('\x1b[31;1mAborting.\x1b[0m')
            return

        try:
            tokens = self._tokenstore.delete_token(identifier, password)
        except KeyError:
            print('\x1b[31;1mToken does not exist.\x1b[0m')
            return
        except ValueError:
            print('\x1b[31;1mInvalid password. Your encryption password is needed to replace or delete tokens.\x1b[0m')
            return

        print(f'\x1b[36;1mToken deleted successfully. You now have {tokens - 1} tokens.\x1b[0m')

    def list_tokens(self):
        print(f'\x1b[36;1mYou have {len(self._tokenstore.tokens)} tokens.\x1b[0m')

        for index in range(len(self._tokenstore.tokens)):
            token = self._tokenstore.tokens[index]
            print(f'\x1b[36m{index + 1}. {token}\x1b[0m')

    def reencrypt_tokens(self):
        current_password = getpass.getpass('Current encryption password: ')
        password = getpass.getpass('New encryption password: ')
        confirm_password = getpass.getpass('Confirm encryption password: ')

        if not password == confirm_password:
            print('\x1b[31;1mPasswords do not match.\x1b[0m')
            return

        del confirm_password

        print('\x1b[37;41;1mWARNING: YOUR TOKENS WILL BE RE-ENCRYPTED!\x1b[0m')
        print('\x1b[33;1mYou will need to use your new encryption password to start Unifier.\x1b[0m')
        print('\x1b[33;1mThis process is irreversible. Once it\'s done, there\'s no going back!\x1b[0m')
        print()
        print('\x1b[33;1mProceed anyways? (y/n)\x1b[0m')

        try:
            confirm = input().lower()
            if not confirm == 'y':
                raise ValueError()
        except (ValueError, KeyboardInterrupt):
            print('\x1b[31;1mAborting.\x1b[0m')
            return

        try:
            self._tokenstore.reencrypt(current_password, password)
        except ValueError:
            print('\x1b[31;1mInvalid password. Your current encryption password is needed to re-encrypt tokens.\x1b[0m')
            return

        print('\x1b[36;1mTokens have been re-encrypted successfully.\x1b[0m')

    def command_help(self):
        print('\x1b[36;1mCommands:\x1b[0m')
        for command in self.commands:
            print(f'\x1b[36m{command}\x1b[0m')

    def run(self):
        while True:
            try:
                command = input('> ').lower()
            except KeyboardInterrupt:
                break

            # noinspection PyBroadException
            try:
                self.commands[command]()
            except KeyError:
                print('\x1b[33;1mInvalid command. Type "help" for a list of commands.\x1b[0m')
            except KeyboardInterrupt:
                pass
            except SystemExit:
                break
            except:
                traceback.print_exc()
                print('\x1b[31;1mAn error occurred.\x1b[0m')
