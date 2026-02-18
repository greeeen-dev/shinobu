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

# Note: This class is only to be used for typing in development. It does absolutely nothing
# except providing the structure of the secrets wrapper.

class FineGrainedWrapper:
    """Base class for FineGrainedSecrets and FineGrainedSecureFiles."""

class FineGrainedSecrets(FineGrainedWrapper):
    """Fine-grained secrets."""

    def retrieve(self, secret: str) -> str:
        return ""

class FineGrainedSecureFiles(FineGrainedWrapper):
    """Fine-grained secure files."""

    def read(self, filename: str) -> str:
        return ""

    def read_json(self, filename: str) -> dict:
        return {}

    def save(self, filename: str, data: str):
        return

    def save_json(self, filename: str, data: dict):
        return
