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
import getpass
import json
import tomllib
import tomli_w
from shinobu.runtime.secrets import manager

class ShinobuInstallerCLI:
    def __init__(self):
        self._tokenstore: manager.TokenStore | None = None
        self.platforms_available: dict[str, str] = {"discord": "Discord", "stoat": "Stoat", "fluxer": "Fluxer"}

        # Get configs
        self.config_data: dict = self.get_config("configs/main.toml")
        self.stoat_config_data: dict = self.get_config("configs/stoat.toml")
        self.fluxer_config_data: dict = self.get_config("configs/fluxer.toml")

    @staticmethod
    def get_config(filename: str) -> dict:
        try:
            with open(filename, "rb") as config_file:
                return tomllib.load(config_file)
        except (tomllib.TOMLDecodeError, FileNotFoundError):
            return {}

    @staticmethod
    def bool_choice() -> bool:
        while True:
            raw_choice: str = input("Yes (y)/No (n):").lower()

            if raw_choice == "y":
                return True
            elif raw_choice == "n":
                return False

    @staticmethod
    def get_stoat_id(prompt: str) -> str | None:
        while True:
            raw_input: str = input(prompt)

            # Check input length
            if len(raw_input) != 26:
                print("Invalid input. Stoat IDs must be 26 characters.")
                continue

            return raw_input

    @staticmethod
    def get_snowflake(prompt: str) -> int | None:
        while True:
            raw_input: str = input(prompt)

            # Check input length
            if len(raw_input) < 17:
                print("Invalid input. Snowflakes must be 17 characters or longer.")
                continue

            try:
                snowflake: int = int(raw_input)
            except ValueError:
                print("Invalid input. Snowflakes must be a number.")
                continue

            return snowflake

    @staticmethod
    def get_integer(prompt: str, strict: bool = False) -> int | None:
        while True:
            raw_input: str = input(prompt)

            try:
                number: int = int(raw_input)
            except ValueError:
                if strict:
                    print("Invalid input. Input must be a number.")
                    continue

                return None

            return number

    def setup_platform(self, platform: str, config: dict):
        platform_name: str = self.platforms_available[platform]

        # Set up config dict
        if not config.get("system"):
            config.update({"system": {"owner_id": None, "admin_ids": []}})
        else:
            config["system"].update({"owner_id": None, "admin_ids": []})

        # Get owner ID
        if platform == "stoat":
            owner_id: int | str = self.get_stoat_id(f"Owner's {platform_name} ID: ")
        else:
            owner_id: int | str = self.get_snowflake(f"Owner's {platform_name} ID: ")
        config["system"]["owner_id"] = owner_id

        # Prompt for admins
        print("Would you like to add admins to your bot?")
        setup_admins: bool = self.bool_choice()

        if setup_admins:
            while True:
                # Add admin
                if platform == "stoat":
                    admin_id: int | str = self.get_stoat_id(f"Admin's {platform_name} ID: ")
                else:
                    admin_id: int | str = self.get_snowflake(f"Admin's {platform_name} ID: ")
                config["system"]["admin_ids"].append(admin_id)
                print(f"User {admin_id} has been added as an admin.")

                # Prompt for more admins
                print("Add more admins?")
                continue_setup_admins: bool = self.bool_choice()

                if not continue_setup_admins:
                    break

        if platform != "discord" and f"TOKEN_{platform.upper()}" not in self._tokenstore.tokens:
            # Set up token
            print(f"We will now ask for the {platform_name} bot token. This is not your encryption password.")
            print("WARNING: DO NOT SHARE YOUR BOT TOKENS.")
            token: str = getpass.getpass("Bot token: ")
            self._tokenstore.add_token(f"TOKEN_{platform.upper()}", token)

        if platform != "discord":
            print(f"{platform_name} setup complete.\n")

    def run(self):
        steps: int = 3

        # get install data
        install_data: dict = {}
        try:
            with open(".install.json", "r") as file:
                install_data = json.load(file)
        except (json.JSONDecodeError, FileNotFoundError):
            print("Could not find install data. Run the launcher first.")
            sys.exit(1)

        should_setup_secrets: bool = True
        print("Welcome to the Shinobu installer! >w<")

        # Check if tokens exist before install
        if os.path.exists(".secrets.json"):
            should_setup_secrets = False

        # Step 1: Set up owner and admins
        print(f"Setup (1/{steps})\n")
        print("We will need to configure an instance owner and instance admins.")
        print("The owner (usually you) has access to all administrative tools for the Shinobu instance including "+
              "Python code evaluation, while admins can manage Spaces, moderators, etc.")
        print("We will set this up for Discord for now. You can set this up for other platforms when configuring them.")

        # Set up Discord
        self.setup_platform("discord", self.config_data)

        # Step 2: Set up tokenstore
        print(f"Setup (2/{steps})\n")

        if not should_setup_secrets:
            print("You seem to have an encrypted secrets file already. Would you like to use it?")
            print("WARNING: If you choose not to use existing files, all existing Shinobu data will be lost. THIS CANNOT BE UNDONE!")
            should_setup_secrets: bool = not self.bool_choice()

        if should_setup_secrets:
            # Delete old secrets file (if it exists)
            if os.path.exists(".secrets.json"):
                os.remove(".secrets.json")

            # Purge all data (if any)
            if os.path.isdir("data"):
                for file in os.listdir("data"):
                    if not os.path.isfile(f"data/{file}"):
                        continue

                    os.remove(f"data/{file}")
            else:
                os.mkdir("data")

            print("To set up encrypted secrets and secure files, you need to set up an encryption password.")
            print("Choose a password that's memorable yet secure. This should NOT be your Discord password.")
            print("Keep your password somewhere safe as we can't recover your data if you lose your password!")

            while True:
                encryption_password: str = getpass.getpass("Encryption password: ")
                encryption_password_confirm: str = getpass.getpass("Confirm encryption password: ")

                if encryption_password == encryption_password_confirm:
                    break
                else:
                    print("Passwords do not match.")

            # Set up TokenStore
            self._tokenstore = manager.TokenStore(encryption_password)
            self._tokenstore.save()
        else:
            while True:
                encryption_password: str = getpass.getpass("Encryption password: ")
                self._tokenstore = manager.TokenStore(encryption_password)

                if self._tokenstore.test_decrypt():
                    break

                print("Decryption test failed. Your password is likely invalid.")
                continue

        if "TOKEN" not in self._tokenstore.tokens:
            # Set up token
            print(f"We will now ask for the Discord bot token. This is not your encryption password.")
            print("WARNING: DO NOT SHARE YOUR BOT TOKENS.")
            token: str = getpass.getpass("Bot token: ")
            self._tokenstore.add_token("TOKEN", token)

        print("")

        # Step 3: Set up platforms
        print(f"Setup (3/{steps})\n")

        # List platforms
        while True:
            print("Platforms available:")

            index: int = 1
            mapping: dict[int, str] = {}

            for platform in self.platforms_available:
                if platform == "discord":
                    # We've already set this up
                    continue

                mapping[index] = platform

                print(f"- {index}. {self.platforms_available[platform]} (ID: {platform})")
                index += 1

            selected: int | None = self.get_integer("Type an index to set up a platform or anything else to continue: ")

            if not selected:
                break
            elif selected < 1 or selected >= index:
                break

            # Get selected platform
            selected_platform: str = mapping[selected]

            if selected_platform == "stoat":
                self.setup_platform("stoat", self.stoat_config_data)
            elif selected_platform == "fluxer":
                self.setup_platform("fluxer", self.fluxer_config_data)

        # Write configs
        with open("configs/main.toml", "wb+") as file:
            tomli_w.dump(self.config_data, file)
        with open("configs/stoat.toml", "wb+") as file:
            tomli_w.dump(self.stoat_config_data, file)
        with open("configs/fluxer.toml", "wb+") as file:
            tomli_w.dump(self.fluxer_config_data, file)

        # Write install data
        install_data.update({"setup": True})

        with open(".install.json", "w+") as file:
            json.dump(install_data, file)

        print("Installation complete! Rerun the launcher to start Shinobu.")
