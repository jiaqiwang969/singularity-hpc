__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2021, Vanessa Sochat"
__license__ = "MPL 2.0"


from .client import Client
from .settings import Settings

from shpc.utils import check_install
from shpc.logger import logger
import os


# The client either exists and we have a database handle, or not

try:
    from sqlalchemy import or_
except ImportError:
    pass


def get_client(quiet=False, **kwargs):
    """
    Get a singularity HPC client based on the backend (e.g., LMOD)
    and container technology (currently just Singularity) of interest.

    Parameters
    ==========
    quiet: if True, suppress most output about the client (e.g. speak)

    """
    # Give the user a warning:
    if not check_install():
        logger.warning("Singularity is not installed, functionality might be limited.")
    Client.quiet = quiet

    # Load user settings, add to client
    settings = Settings(kwargs.get("settings_file"))
    sqlite_enabled = "or_" in globals() or not settings.database_disable

    # Add dummy or real database functions to the client
    if not sqlite_enabled or settings.get("disable_database", False):
        logger.warning("Database disabled. Install sqlalchemy for full functionality")
        from shpc.database.dummy import add, init_db

        Client.add = add
        Client._init_db = init_db
    else:
        from shpc.database.models import Collection, Container, init_db, Base
        from shpc.database.sqlite import (
            add,
            get,
            mv,
            rm,
            images,
            inspect,
            get_container,
            get_collection,
            get_or_create_collection,
        )

        # Add database actions
        Client._init_db = init_db
        Client.add = add
        Client.get = get
        Client.inspect = inspect
        Client.mv = mv
        Client.rm = rm
        Client.images = images

        # Collections
        Client.get_or_create_collection = get_or_create_collection
        Client.get_container = get_container
        Client.get_collection = get_collection

    # Initialize the database and client
    Client.settings = settings
    return Client()
