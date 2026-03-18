import asyncio
import discord
from typing import Any
from discord.ext import bridge

class ShinobuListNotImplemented(Exception):
    pass

class ShinobuListEntryField:
    def __init__(self, name: str, value: str):
        self._name: str = name
        self._value: str = value

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> str:
        return self._value

class ShinobuListEntry:
    def __init__(self, name: str, description: str | None = None, emoji: str | None = None):
        self._name: str = name
        self._description: str | None = description
        self._emoji: str | None = emoji
        self._fields: list[ShinobuListEntryField] = []
        self._parent: ShinobuListEntry | None = None
        self._children: list[ShinobuListEntry] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str | None:
        return self._description

    @property
    def emoji(self) -> str | None:
        return self._emoji

    @property
    def fields(self) -> list[ShinobuListEntryField]:
        return self._fields

    @property
    def parent(self) -> 'ShinobuListEntry':
        return self._parent

    @property
    def children(self) -> list['ShinobuListEntry']:
        return self._children

    def add_field(self, name: str, value: str):
        self._fields.append(ShinobuListEntryField(name, value))

    def set_parent(self, parent: 'ShinobuListEntry'):
        self._parent = parent

    def add_child(self, child: 'ShinobuListEntry'):
        if child in self._children:
            return

        child.set_parent(self)
        self._children.append(child)

class ShinobuListContent:
    def __init__(self, content: str | None = None, embed: Any | None = None, view: Any | None = None):
        self._content: str | None = content
        self._embed = embed
        self._view = view

    @property
    def text(self) -> str | None:
        return self._content

    @property
    def embed(self) -> Any | None:
        return self._embed

    @property
    def view(self) -> Any | None:
        return self._view

class ShinobuListBaseView:
    """A base class for list views."""

    def __init__(self, title: str, description: str, color: int):
        self._title: str = title
        self._description: str = description
        self._color: int = color
        self._entries: list[ShinobuListEntry] = []
        self._page: int = 0
        self._viewing: ShinobuListEntry | None = None

        # Search
        self._search: str | None = None
        self._past_search: str | None = None
        self._by_title: bool = True
        self._by_desc: bool = True
        self._use_both: bool = False

    @property
    def visible_current_entries(self) -> list[ShinobuListEntry]:
        if self._search:
            return self._search_entries()
        else:
            return self.current_entries

    @property
    def current_entries(self) -> list[ShinobuListEntry]:
        if self._viewing:
            return self._viewing.children
        else:
            return self._entries

    @property
    def max_page(self) -> int:
        return len(self.current_entries) // 20

    @property
    def is_head(self) -> bool:
        return not self._viewing and not self._search

    @property
    def is_leaf(self) -> bool:
        return len(self._viewing.children) == 0 if self._viewing else False

    def _search_entries(self) -> list[ShinobuListEntry]:
        results: list[ShinobuListEntry] = []

        for item in self.current_entries:
            name_match: bool = self._search.lower() in item.name.lower() and self._by_title
            desc_match: bool = self._search.lower() in item.description.lower() and self._by_desc
            valid_match: bool = name_match or desc_match

            if self._use_both and self._by_title and self._by_desc:
                valid_match: bool = name_match and desc_match

            if valid_match:
                results.append(item)

        return results

    def search(self, query: str, by_title: bool = True, by_desc: bool = True, use_both: bool = False):
        if use_both:
            by_title = True
            by_desc = True

        self._search = query
        self._by_desc = by_title
        self._by_desc = by_desc
        self._use_both = use_both

    def select(self, entry: ShinobuListEntry):
        if entry not in self._entries:
            self._viewing = None
        else:
            self._viewing = entry

            if self._search:
                self._past_search = self._search
                self._search = None

    def back(self):
        if self._search:
            self._search = None
        elif self._viewing:
            self._viewing = self._viewing.parent

            if self._past_search:
                self._search = self._past_search
                self._past_search = None

    def render(self) -> ShinobuListContent:
        raise ShinobuListNotImplemented()

    async def run(self, *args, **kwargs):
        raise ShinobuListNotImplemented()

class ShinobuListDiscordView(ShinobuListBaseView):
    def get_breadcrumbs(self, entry: ShinobuListEntry) -> list[str]:
        if entry.parent:
            return self.get_breadcrumbs(entry.parent) + [entry.name]
        else:
            return [entry.name]

    def _build_embed(self) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            title=self._title,
            description=self._description,
            color=self._color
        )

        # Show current selected entry
        if not self.is_head:
            embed.title = f"{self._title} / {' / '.join(self.get_breadcrumbs(self._viewing))}"
            embed.description = f"Viewing: {self._viewing.emoji} {self._viewing.name}"

            if self._search:
                embed.title = embed.title + ' / search'
                embed.description = f"Searching: `{self._search}"

        # Render current selected entry info
        if self.is_leaf:
            embed.description = f"# {self._viewing.emoji} {self._viewing.name}\n{self._viewing.description}"

            for field in self._viewing.fields:
                embed.add_field(name=field.name, value=field.value, inline=False)

        # Render page number
        if not self.is_leaf:
            embed.set_footer(text=f"Page {self._page + 1} of {self.max_page + 1}")

        return embed

    def _build_view(self) -> discord.ui.View:
        view: discord.ui.View = discord.ui.View(store=False)

        # Add selection
        if not self.is_head:
            # Get items
            options: list[discord.SelectOption] = []
            for index in range(len(self.visible_current_entries)):
                entry: ShinobuListEntry = self.visible_current_entries[index]
                options.append(discord.SelectOption(
                    label=entry.name, value=str(index), emoji=entry.emoji
                ))

            view.add_item(discord.ui.ActionRow(
                discord.ui.Select(
                    placeholder="Select an option...",
                    custom_id="navigation_select",
                    options=options,
                    disabled=len(self.visible_current_entries) == 0
                )
            ))

        # Add search options
        if self._search:
            view.add_item(discord.ui.ActionRow(
                discord.ui.Button(
                    label="By name",
                    style=discord.ButtonStyle.green if self._by_title else discord.ButtonStyle.gray,
                    disabled=self._use_both,
                    custom_id="search_name"
                ),
                discord.ui.Button(
                    label="By description",
                    style=discord.ButtonStyle.green if self._by_desc else discord.ButtonStyle.gray,
                    disabled=self._use_both,
                    custom_id="search_desc"
                ),
                discord.ui.Button(
                    label="Match both" if self._use_both else "Match either",
                    style=discord.ButtonStyle.blurple if self._use_both else discord.ButtonStyle.gray,
                    custom_id="search_both"
                )
            ))

        # Add navigation buttons
        if not self.is_leaf:
            view.add_item(discord.ui.ActionRow(
                discord.ui.Button(
                    emoji="\U000023EA",
                    custom_id="navigation_first",
                    style=discord.ButtonStyle.blurple,
                    disabled=self._page==0
                ),
                discord.ui.Button(
                    emoji="\U000025C0\U0000FE0F",
                    custom_id="navigation_previous",
                    style=discord.ButtonStyle.blurple,
                    disabled=self._page == 0
                ),
                discord.ui.Button(
                    emoji="\U000025B6\U0000FE0F",
                    custom_id="navigation_next",
                    style=discord.ButtonStyle.blurple,
                    disabled=self._page == self.max_page
                ),
                discord.ui.Button(
                    emoji="\U000023E9",
                    custom_id="navigation_last",
                    style=discord.ButtonStyle.blurple,
                    disabled=self._page == self.max_page
                ),
                discord.ui.Button(
                    label="Search",
                    emoji="\U000023EA",
                    custom_id="navigation_search",
                    style=discord.ButtonStyle.green,
                    disabled=self._page == 0
                )
            ))

        # Add back button
        if not self.is_head:
            view.add_item(discord.ui.ActionRow(
                discord.ui.Button(
                    label="Back",
                    emoji="\U00002B05\U0000FE0F",
                    custom_id="navigation_back"
                )
            ))

        return view

    def render(self) -> ShinobuListContent:
        embed: discord.Embed = self._build_embed()
        view: discord.ui.View = self._build_view()
        return ShinobuListContent(embed=embed, view=view)

    async def run(self, bot: bridge.Bot, initiator: discord.Interaction):
        content: ShinobuListContent = self.render()
        message: discord.Message = (await initiator.response().send_message(
            content=content.text,
            embed=content.embed,
            view=content.view
        )).message

        # Wait for interactions
        def check(incoming: discord.Interaction):
            return incoming.user.id == initiator.user.id and incoming.channel_id == initiator.channel_id

        while True:
            try:
                # noinspection PyUnresolvedReferences
                interaction: discord.Interaction = await bot.wait_for("interaction", check=check, timeout=60)
            except asyncio.TimeoutError:
                # Stop loop
                await message.edit(view=None)
                break
