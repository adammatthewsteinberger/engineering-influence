# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a marketplace index and downloads a plugin file from it, checking the hash before anything else."""

import hashlib
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.bundle_fetcher_interface import BundleFetcherInterface
from engineering_influence.interfaces.plugin_index_parser_interface import (
    PluginIndexParserInterface,
)
from engineering_influence.interfaces.plugin_parser_interface import PluginParserInterface
from engineering_influence.interfaces.skill_files_interface import SkillFilesInterface
from engineering_influence.models.plugin_bundle import PluginBundle
from engineering_influence.models.plugin_download import PluginDownload
from engineering_influence.models.plugin_index import PluginIndex
from engineering_influence.services.interfaces.plugin_marketplace_interface import (
    PluginMarketplaceInterface,
)


class PluginMarketplace(PluginMarketplaceInterface):
    """The only thing here that can reach a network, and only when a person runs a command that says so.

    An index is a file on disk or an ``https://`` address. A download goes to the address the index gives,
    for at most ``max_bytes``, and **what comes back is hashed before it is read as anything**: bytes whose
    SHA-256 is not the one the index promised are discarded and nothing is saved. Only then is the file
    read as a plugin, which must be the plugin the index named, at the version it named. The file is saved
    beside where the person said, never over an existing file, and **nothing is installed**: a person
    reads it with ``ei plugins show`` and installs it with ``ei plugins add``, and a run never contacts a
    marketplace at all.
    """

    def __init__(
        self,
        fetcher: BundleFetcherInterface,
        files: SkillFilesInterface,
        indexes: PluginIndexParserInterface,
        plugins: PluginParserInterface,
        max_bytes: int = 512 * 1024,
    ) -> None:
        self._fetcher = fetcher
        self._files = files
        self._indexes = indexes
        self._plugins = plugins
        self._max_bytes = max_bytes

    def index(self, address: str) -> PluginIndex:
        """The index at a file path or an https address, or an ApplicationError saying why it is not usable."""
        return self._indexes.parse(self._read(address))

    def download(self, address: str, name: str, folder: Path) -> PluginDownload:
        """Download the named plugin to ``folder``, checked against the index's hash; nothing is installed."""
        entry = self.index(address).find(name)
        if entry is None:
            raise self._refused("PLUGIN_NOT_IN_INDEX", f"the index lists no plugin named {name!r}")
        data = self._fetcher.fetch(entry.url, self._max_bytes)
        digest = hashlib.sha256(data).hexdigest()
        if digest != entry.sha256:
            raise self._refused(
                "PLUGIN_HASH_MISMATCH",
                f"what was downloaded for {entry.identifier()} is not what the index promised: "
                f"its hash starts {digest[:12]}, the index's starts {entry.sha256[:12]}; nothing was saved",
            )
        plugin = self._plugins.parse(data, entry.name)
        if plugin.version != entry.version:
            raise self._refused(
                "PLUGIN_VERSION_MISMATCH",
                f"the index lists {entry.identifier()}, but the file is {plugin.identifier()}; "
                "nothing was saved",
            )
        path = folder / f"{entry.name}.toml"
        if self._files.read(path) is not None:
            raise self._refused(
                "PLUGIN_FILE_EXISTS",
                f"{path} already exists; move it, or choose another --output folder",
                409,
            )
        self._files.write(path, data, False)
        return PluginDownload(entry, PluginBundle(plugin, digest), path)

    def _read(self, address: str) -> bytes:
        if address.startswith("https://"):
            return self._fetcher.fetch(address, self._max_bytes)
        if "://" in address:
            raise self._refused(
                "PLUGIN_INDEX_REFUSED", "an index is a file on disk or an https:// address"
            )
        data = self._files.read(Path(address))
        if data is None:
            raise self._refused("PLUGIN_INDEX_MISSING", f"there is no index at {address}")
        return data

    @staticmethod
    def _refused(code: str, message: str, status: int = 422) -> ApplicationError:
        return ApplicationError(code=code, message=message, http_status=status)
