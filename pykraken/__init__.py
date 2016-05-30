import pkg_resources
__version__ = pkg_resources.get_distribution("pykraken").version
from .client import Client # NOQA




