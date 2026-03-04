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

# An intermediate script for running Shinobu with the configured Python install or venv.

import os
import sys
import json

class ShinobuInstallData:
    def __init__(self, environment: str | None = None, is_venv: bool = False, setup: bool = False):
        self.environment: str = environment or ("python3" if sys.platform != "win32" else "py -3")
        self.is_venv: bool = is_venv
        self.setup: bool = setup

    def to_dict(self) -> dict:
        return {
            "environment": self.environment,
            "is_venv": self.is_venv,
            "setup": self.setup
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data.get("environment"), data.get("is_venv", False), data.get("setup", False))

def install_dependencies(data: ShinobuInstallData) -> bool:
    if data.is_venv:
        return os.system(f"{data.environment} -m pip install -r requirements.txt") == 0
    else:
        # Do user install to prevent permission issues
        return os.system(f"{data.environment} -m pip install -r requirements.txt --user") == 0

# Get arguments
args: list = sys.argv.copy()

# Remove filepath argument
args.pop(0)

# Get install data
installed: bool = False
install_data: ShinobuInstallData | None = None

try:
    with open(".install.json", "r") as file:
        install_data = ShinobuInstallData.from_dict(json.load(file))
except FileNotFoundError:
    # We need to install Shinobu
    pass
except json.JSONDecodeError:
    # Installation is corrupted
    print("Your Shinobu install is corrupted. Launcher will proceed with reinstallation.")
else:
    installed = True

if not installed:
    # Do initial setup
    install_data = ShinobuInstallData()
    use_venv: bool = False

    print("Before running the installer, we need to set up our environment.")

    if sys.platform == "win32":
        print("Using global environment on Windows. For virtual environments, use Linux or macOS.")
    elif "--skip-env-setup" in args:
        args.remove("--skip-env-setup")
        print("Using .venv/bin/python as environment.")
        install_data.environment = ".venv/bin/python"
        install_data.is_venv = True
    else:
        print("Would you like to use a virtual environment? This is highly recommended to prevent package conflicts " +
              "between multiple Python projects.")
        print("Please note this will create a virtual environment in .venv.")
        use_venv = input("Yes (y)/No (n): ").lower() == "y"

    if use_venv:
        # Set up virtual environment
        install_data.environment = ".venv/bin/python"
        install_data.is_venv = True
        venv_setup: bool = os.system("python3 -m venv .venv") == 0

        if not venv_setup:
            print("Virtual environment setup failed, aborting.")
            sys.exit(1)

    # Install dependencies
    print("Installing dependencies...")
    dependencies_installed: bool = install_dependencies(install_data)
    if dependencies_installed:
        print("Dependencies installed.")
    else:
        print("Dependencies install failed, aborting.")
        sys.exit(1)

    # Write install file
    with open(".install.json", "w+") as file:
        json.dump(install_data.to_dict(), file)
else:
    if "--install-deps" in args:
        args.remove("--install-deps")

        print("Installing dependencies...")
        dependencies_installed: bool = install_dependencies(install_data)
        if dependencies_installed:
            print("Dependencies installed.")
            sys.exit(0)
        else:
            print("Dependencies install failed.")
            sys.exit(1)

if not install_data.setup and not "--install" in args:
    args.append("--install")

if "--skip-env-setup" in args:
    args.remove("--skip-env-setup")

# Create arguments string
args_string: str = " ".join(args)

# Run Shinobu with environment defined in install data
os.system(f"{install_data.environment} -m shinobu {args_string}")
