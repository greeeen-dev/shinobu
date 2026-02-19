from discord.ext import commands, bridge
from shinobu.runtime.secrets import fine_grained

class ShinobuCogMetadata:
    """A class representing metadata for a LabeledCog."""

    def __init__(self, name: str, description: str, emoji: str | None = None, visible_in_help: bool = True):
        self._name: str = name
        self._description: str = description
        self._emoji: str | None = emoji
        self._visible_in_help: bool = visible_in_help

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def emoji(self) -> str | None:
        return self._emoji

    @property
    def visible_in_help(self) -> bool:
        return self._visible_in_help

class ShinobuCog(commands.Cog):
    def __init__(self, bot):
        self.bot: bridge.Bot = bot
        self._shinobu_metadata: ShinobuCogMetadata | None = None
        self._shinobu_secrets: fine_grained.FineGrainedSecrets | None = None
        self._shinobu_files: fine_grained.FineGrainedSecureFiles | None = None

    def setup_shinobu_cog(self, bot, **kwargs):
        self.bot = bot
        self._shinobu_secrets: fine_grained.FineGrainedSecrets | None = None
        self._shinobu_files: fine_grained.FineGrainedSecureFiles | None = None

        # Get secure files wrapper if it exists
        if "files_wrapper" in kwargs:
            self._shinobu_files = kwargs.get("files_wrapper")

    def issue_entitlements(self, secrets: fine_grained.FineGrainedSecrets | None = None,
                           files: fine_grained.FineGrainedSecureFiles | None = None):
        """Issues entitlements to a Shinobu cog."""

        if self._shinobu_secrets is None:
            self._shinobu_secrets = secrets
        if self._shinobu_files is None:
            self._shinobu_files = files

    @property
    def shinobu_metadata(self) -> ShinobuCogMetadata:
        return self._shinobu_metadata

    @property
    def secrets(self) -> fine_grained.FineGrainedSecrets:
        return self._shinobu_secrets

    @property
    def files(self) -> fine_grained.FineGrainedSecureFiles:
        return self._shinobu_files
