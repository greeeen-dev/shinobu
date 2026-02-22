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

import os
import sys
import copy
import argparse
import ujson as json
import orjson
import getpass
import discord
from discord.ext import commands
from dotenv import load_dotenv
from shinobu.runtime import runtime
from shinobu.runtime.secrets import manager, fine_grained, encryptor
from shinobu.runtime.models import shinobu_cog
from shinobu.cli import secrets as secrets_cli

# Manifest path
manifest_path = os.path.join(os.path.dirname(__file__), "manifest.json")

# Prevent attacks via import
if __name__ != "__main__":
    raise RuntimeError("Bootscript should not be imported!")

# Create argument parser
parser = argparse.ArgumentParser(
    prog="shinobu",
    description="Converse from anywhere, anytime. Shinobu is a versatile cross-platform bridge bot."
)
parser.add_argument("--secrets", help="Launches the Secrets Manager CLI.", action="store_true")
launch_args = parser.parse_args()

# Get launch options
launch_secrets_cli: bool = launch_args.secrets

# Create TokenStore variable (do not initialize yet)
tokenstore: manager.TokenStore | None = None

# Create RawEncryptor variable (do not initialize yet)
raw_encryptor: manager.RawEncryptor | None = None

# Create password variable
password: str | None = None

class SecretsIssuingAuthority:
    """Issues FineGrainedSecrets objects."""

    def __init__(self):
        self._wrappers_secrets: dict = {}
        self._wrappers_files: dict = {}
        self._cogs_wrapper_map_secrets: dict = {}
        self._cogs_wrapper_map_files: dict = {}
        self._cogs_registered_secrets: dict | None = None
        self._cogs_registered_files: dict | None = None
        self._accessed_secrets: set = set()
        self._accessed_files: set = set()

        # Load plugins
        self.load_plugins()

    @staticmethod
    def _sanity_check(entitlements: dict) -> bool:
        """Checks if an entitlement dict is valid."""

        # Ensure entitlements is a dict
        if type(entitlements) is not dict:
            return False

        # Check if we even have requested entitlements
        if len(entitlements.keys()) == 0:
            # We'll assume these are valid
            return True

        # Run sanity checks
        invalid_entitlements = False
        for entitlement in entitlements:
            if invalid_entitlements:
                # Stop as check failed already
                break

            if type(entitlements[entitlement]) is not list:
                # Stop checks
                invalid_entitlements = True
                break

            for secret in entitlements[entitlement]:
                if type(secret) is not str:
                    # Stop checks on next loop
                    invalid_entitlements = True
                    break

        return not invalid_entitlements

    def _load_manifest(self, filepath):
        # Read plugin data
        with open(filepath, 'r') as file:
            data = json.load(file)

        # Retrieve entitlements
        entitlements_secrets = data.get("entitlements_secrets", {})
        entitlements_files = data.get("entitlements_files", {})

        # Does the module describe its intents?
        intents = data.get("intents", {})
        if "entitlements_secrets" not in intents:
            entitlements_secrets = {}
        if "entitlements_files" not in intents:
            entitlements_files = {}

        # Run sanity checks
        entitlements_secrets_valid = self._sanity_check(entitlements_secrets)
        entitlements_files_valid = self._sanity_check(entitlements_files)

        # Just to be strict, we'll enforce both entitlements to be valid
        if not entitlements_secrets_valid and entitlements_files_valid:
            return

        # Grant entitlements
        for cog in entitlements_secrets:
            self._cogs_registered_secrets.update({cog: entitlements_secrets[cog]})
        for cog in entitlements_files:
            self._cogs_registered_files.update({cog: entitlements_files[cog]})

    def load_plugins(self):
        if self._cogs_registered_secrets is not None or self._cogs_registered_files is not None:
            raise ValueError("Plugins already loaded")

        self._cogs_registered_secrets = {}
        self._cogs_registered_files = {}

        # Load builtin manifest
        self._load_manifest(manifest_path)

        if not os.path.exists("plugins"):
            # There's no plugins to load!
            return

        # Load entitlements for each plugin
        for plugin in os.listdir("plugins"):
            # Skip non-JSON files (these aren't plugin entries)
            if not plugin.endswith(".json"):
                continue

            # Grant entitlements for plugin
            self._load_manifest(plugin)

    def check_cog_secrets_entitlements(self, cog: str) -> bool:
        """Checks if a cog has entitlements to secrets."""
        return cog in self._cogs_registered_secrets

    def check_cog_files_entitlements(self, cog: str) -> bool:
        """Checks if a cog has entitlements to secure files."""
        return cog in self._cogs_registered_files

    def issue_secrets_cog(self, cog: str) -> fine_grained.FineGrainedSecrets:
        """Issues a FineGrainedSecrets object for a cog."""

        # Return cached wrapper if available
        if cog in self._cogs_wrapper_map_secrets:
            return self._cogs_wrapper_map_secrets[cog]

        # Issue wrapper
        wrapper: fine_grained.FineGrainedSecrets = self.issue(
            self._cogs_registered_secrets.get(cog, [])
        )
        self._cogs_wrapper_map_secrets.update({cog: wrapper})
        return wrapper

    def issue_files_cog(self, cog: str) -> fine_grained.FineGrainedSecureFiles:
        """Issues a FineGrainedSecureFiles object for a cog."""

        # Return cached wrapper if available
        if cog in self._cogs_wrapper_map_files:
            return self._cogs_wrapper_map_files[cog]

        # Issue wrapper
        wrapper: fine_grained.FineGrainedSecureFiles = self.issue(
            self._cogs_registered_files.get(cog, []),
            is_file=True
        )
        self._cogs_wrapper_map_files.update({cog: wrapper})
        return wrapper

    def issue(self, secrets: list, is_file: bool = False) -> fine_grained.FineGrainedSecrets | fine_grained.FineGrainedSecureFiles:
        """Issues a FineGrainedWrapper object."""

        # Prevent entitlements mutation
        requested_entitlements = copy.copy(secrets)

        # Run sanity checks
        if len(requested_entitlements) == 0:
            raise ValueError("Cannot issue a FineGrainedWrapper without entitlements")

        for entitlement in requested_entitlements:
            # If entitlement is not a string, we ignore it to prevent mutable variables
            # from being in the requested entitlements
            if type(entitlement) is not str:
                raise ValueError("Entitlement must be a string")

            if entitlement in self._accessed_secrets and not is_file:
                raise ValueError(f"Entitlement to secret {entitlement} already issued")

            if entitlement in self._accessed_files and is_file:
                raise ValueError(f"Entitlement to file {entitlement} already issued")

        # Issue entitlements
        if is_file:
            wrapper: fine_grained.FineGrainedSecureFiles = ActualFineGrainedSecureFiles()
            self._wrappers_files.update({id(wrapper): requested_entitlements})
            self._accessed_files.update(requested_entitlements)
        else:
            wrapper: fine_grained.FineGrainedSecrets = ActualFineGrainedSecrets()
            self._wrappers_secrets.update({id(wrapper): requested_entitlements})
            self._accessed_secrets.update(requested_entitlements)

        return wrapper

    def retrieve(self, wrapper: fine_grained.FineGrainedSecrets, secret: str) -> str:
        """Retrieves a secret for a FineGrainedSecrets object."""

        # Ensure wrapper is valid
        if id(wrapper) not in self._wrappers_secrets.keys():
            raise ValueError("Wrapper is either invalid or revoked")

        # Get wrapper entitlements
        wrapper_entitlements = self._wrappers_secrets.get(id(wrapper), [])

        # Does the wrapper have entitlements to the secret?
        if secret not in wrapper_entitlements:
            raise ValueError("Wrapper does not have entitlements to this secret")

        # Get secret
        return tokenstore.retrieve(secret)

    def _check_file_entitlement(self, wrapper: fine_grained.FineGrainedSecureFiles, filename: str):
        """Checks if a wrapper has entitlements to a file."""

        # Ensure wrapper is valid
        if id(wrapper) not in self._wrappers_files.keys():
            raise ValueError("Wrapper is either invalid or revoked")

        # Get wrapper entitlements
        wrapper_entitlements = self._wrappers_files.get(id(wrapper), [])

        # Does the wrapper have entitlements to the file?
        if filename not in wrapper_entitlements:
            raise ValueError("Wrapper does not have entitlements to this file")

    def read(self, wrapper: fine_grained.FineGrainedSecureFiles, filename: str) -> str:
        """Reads a file for a FineGrainedSecureFiles object."""

        # Ensure wrapper has entitlements
        self._check_file_entitlement(wrapper, filename)

        if not filename.isalnum():
            raise ValueError("Filename should be alphanumeric")

        # Load file
        try:
            with open(f"data/{filename}.json", 'r') as file:
                data: dict = json.load(file)
        except FileNotFoundError:
            # Return empty file
            return ""

        encrypted_data = encryptor.GCMEncryptedData.from_dict(data)

        # Decrypt file
        return raw_encryptor.decrypt(encrypted_data)

    def save(self, wrapper: fine_grained.FineGrainedSecureFiles, filename: str, data: str):
        # Ensure wrapper has entitlements
        self._check_file_entitlement(wrapper, filename)

        # Encrypt data
        encrypted_data: encryptor.GCMEncryptedData = raw_encryptor.encrypt(data)

        # Save encrypted data
        with open(f"data/{filename}.json", 'w+') as file:
            # noinspection PyTypeChecker
            json.dump(encrypted_data.to_dict(), file)

# Create variable for SecretsIssuingAuthority (do not initialize yet)
secrets_authority: SecretsIssuingAuthority | None = None

class ActualFineGrainedSecrets(fine_grained.FineGrainedSecrets):
    """The parent class has no idea how to retrieve secrets, so we use a child class to give
    it that ability via overwriting."""

    def retrieve(self, secret: str) -> str:
        return secrets_authority.retrieve(self, secret)

class ActualFineGrainedSecureFiles(fine_grained.FineGrainedSecureFiles):
    """The parent class has no idea how to retrieve secrets, so we use a child class to give
    it that ability via overwriting."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def read(self, filename: str) -> str:
        return secrets_authority.read(self, filename)

    def read_json(self, filename: str) -> dict:
        return orjson.loads(secrets_authority.read(self, filename) or "{}")

    def save(self, filename: str, data: str):
        # This operation can take a very long time (at least a few hundred milliseconds)!
        # It is not recommended to thread this task, consider running it in an asyncio
        # loop executor instead if you need the function to be non-blocking.

        secrets_authority.save(self, filename, data)

    def save_json(self, filename: str, data: dict):
        secrets_authority.save(self, filename, orjson.dumps(data).decode())

class ExtensionCogMap:
    """Keeps track of extensions and its cogs."""

    def __init__(self):
        self.__map = {}
        self.__applied = []

    @staticmethod
    def check_for_match(extension, cog):
        """Checks if an extension has a possible match with a cog."""

        # Ensure cog is a subclass of shinobu_cog.ShinobuCog
        if (
                type(cog) is commands.Cog or type(cog) is shinobu_cog.ShinobuCog or
                not isinstance(cog, shinobu_cog.ShinobuCog)
        ):
            raise TypeError("Cog must be a subclass of shinobu_cog.ShinobuCog")

        # Get expected cog type
        try:
            expected_type = extension.get_cog_type()
        except AttributeError:
            return False

        return type(cog) is expected_type

    def add(self, extension, cog):
        if extension in self.__map:
            raise KeyError("Extension already mapped")

        if type(cog) in self.__applied:
            raise ValueError("Cog already mapped to an extension")

        self.__map.update({extension: cog})
        self.__applied.append(type(cog))

    def get(self, extension):
        return self.__map.get(extension)

# Create ExtensionCogMap variable (do not initialize yet)
extension_map: ExtensionCogMap | None = None

class ModuleLoader:
    """Loads a plugin with all of its entitlements."""

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @staticmethod
    def _get_entitlements(package: str) -> dict:
        """Returns a dict with entitlements."""

        extras: dict = {}

        # Check if we have entitlements
        has_secrets_entitlements: bool = secrets_authority.check_cog_secrets_entitlements(package)
        has_files_entitlements: bool = secrets_authority.check_cog_files_entitlements(package)

        if has_secrets_entitlements:
            extras.update({"secrets_wrapper": secrets_authority.issue_secrets_cog(package)})
        if has_files_entitlements:
            extras.update({"files_wrapper": secrets_authority.issue_files_cog(package)})

        return extras

    def _issue_entitlements(self, package: str):
        """Issues entitlements to an extension."""

        # Get entitlements
        entitlements: dict = self._get_entitlements(package)

        # Save time by not going through the cog scan if there's no entitlements
        if len(entitlements) == 0:
            return

        # Try to get matching cog from cache
        matching_cog: shinobu_cog.ShinobuCog | commands.Cog | None = extension_map.get(package)

        if not matching_cog:
            # Fetch matching cog
            extension_obj = self.bot.extensions[package]

            for cog in self.bot.cogs:
                cog_obj = self.bot.cogs[cog]
                has_match: bool = extension_map.check_for_match(extension_obj, cog_obj)

                if has_match:
                    # Cache for future reference
                    matching_cog = cog_obj
                    extension_map.add(package, cog_obj)
                    break

        if matching_cog:
            # Issue entitlements
            if isinstance(matching_cog, shinobu_cog.ShinobuCog):
                matching_cog.issue_entitlements(
                    secrets=entitlements.get("secrets_wrapper"),
                    files=entitlements.get("files_wrapper")
                )

    def load_extension(self, package: str, *args, **kwargs):
        """Loads a cog and registers entitlements if available."""

        # Load extension
        self.bot.load_extension(package, *args, **kwargs)

        # Issue entitlements
        self._issue_entitlements(package)

    def reload(self, cog, *args, **kwargs):
        """Loads a cog."""

        entitlements: dict = self._get_entitlements(cog)

        self.bot.reload_extension(cog, *args, **kwargs)

def start_bot():
    """Starts Shinobu!"""

    global tokenstore, secrets_authority, raw_encryptor, extension_map, password

    # Regenerate bootscript-level objects
    tokenstore = manager.TokenStore(
        password,
        debug=False,
        read_only=True,
        onetime=["TOKEN"]
    )
    secrets_authority = SecretsIssuingAuthority()
    raw_encryptor = manager.RawEncryptor(
        password
    )
    extension_map = ExtensionCogMap()

    # Create intents object
    intents = discord.Intents.all()
    # noinspection PyDunderSlots,PyUnresolvedReferences
    intents.presences = False

    # Create Shinobu bot instance
    bot: runtime.ShinobuBot = runtime.ShinobuBot(command_prefix="sh!", intents=intents, manifest=manifest_path)
    bot.setup_entitlements_loader(ModuleLoader(bot))
    bot.load_builtins()

    # Start bot!
    bot.run(tokenstore.retrieve("TOKEN"))

def start_secrets_cli():
    """Launches the Secrets Manager CLI."""
    global password
    cli_tokenstore = manager.TokenStore(password, debug=False, read_only=False)
    cli_encryptor = manager.RawEncryptor(password)
    cli: secrets_cli.ShinobuSecretsCLI = secrets_cli.ShinobuSecretsCLI(cli_tokenstore, cli_encryptor)
    cli.run()

# Start Shinobu Runtime
if __name__ == "__main__":
    try:
        load_dotenv()

        # Check if password is in env file (dangerous!)
        if os.environ.get("SHINOBU_ENCRYPTION_PASSWORD"):
            print("WARNING: Inheriting password from .env file. Do not store your password here for production environments.")
            password = os.environ.get("SHINOBU_ENCRYPTION_PASSWORD")
        else:
            # Prompt for password (safer!)
            password = getpass.getpass("Encryption password: ")

        if launch_secrets_cli:
            start_secrets_cli()
        else:
            start_bot()
    except KeyboardInterrupt:
        print("Exiting...")
        sys.exit(0)
    else:
        print("Exiting...")
