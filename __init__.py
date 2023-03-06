
import importlib_metadata

from .efinance_datafeed import EfinanceDatafeed as Datafeed

try:
    __version__ = importlib_metadata.version("vnpy_efinance")
except importlib_metadata.PackageNotFoundError:
    __version__ = "dev"
