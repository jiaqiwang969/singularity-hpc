__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2021, Vanessa Sochat"
__license__ = "MPL 2.0"


from shpc.logger import logger
import shpc.utils as utils
import shpc.defaults as defaults
import shpc.main.schemas as schemas
import ruamel_yaml

from datetime import datetime
import os
import jsonschema
import requests
import shutil
import json
import sys


class SingularityContainer:
    """
    A Singularity container controller.

    All container controllers should have the same general interface.
    """

    def __init__(self):
        try:
            from spython.main import Client

            self.client = Client
        except:
            logger.exit("singularity python (spython) is required to use singularity.")

    def pull(self, uri, dest):
        """Pull a container to a destination"""
        pull_folder = os.path.dirname(dest)
        name = os.path.basename(dest)
        return self.client.pull(uri, name=name, pull_folder=pull_folder)


class Tags:
    """Make it easy to interact with tags (name and version)"""

    def __init__(self, tagdict, latest):
        tagdict.update(latest)
        self._tags = tagdict
        self._latest = latest

    @property
    def latest(self):
        key = list(self._latest.keys())[0]
        return Tag(key, self._latest[key])

    def __contains__(self, key):
        return key in self._tags

    def get(self, key, default=None):
        digest = self._tags.get(key, default)
        if digest:
            return Tag(key, digest)


class Tag:
    """
    Convert a tag dictionary to a proper class for easy lookup
    """

    def __init__(self, name, digest):
        self.name = name
        self.digest = digest

    def __str__(self):
        return "%s:%s" % (self.name, self.digest)

    def __repr__(self):
        return str(self)


class ContainerConfig:
    """A ContainerConfig wraps a container.yaml file, intended for install."""

    def __init__(self, package_file):
        """Load a package file for a container."""
        self.load(package_file)
        self.validate()
        self.name = package_file.split(os.sep)[-2]

    def __str__(self):
        return "[container:%s]" % self.name

    def __repr__(self):
        return self.__str__()

    @property
    def tags(self):
        """
        Return a set of tags (including latest)
        """
        latest = self._config.get("latest")
        tags = self._config.get("tags", {})
        return Tags(tags, latest)

    @property
    def latest(self):
        """
        Return the latest tag
        """
        return self.tags.latest

    def dump(self, out=None):
        out = out or sys.stdout
        yaml = ruamel_yaml.YAML()
        yaml.dump(self._config, out)

    def get_url(self):
        """
        Given a loaded container recipe, get the registry url.
        """
        # Not in json schema, but currently required
        if "docker" not in self._config:
            logger.exit("A docker field is currently required in the config.")
        return self._config.get("docker")

    def get(self, key, default=None):
        return self._config.get(key, default)

    def __getattr__(self, key):
        """
        A direct get of an attribute, but default to None if doesn't exist
        """
        return self.get(key)

    def validate(self):
        """
        Validate a loaded config with jsonschema
        """
        jsonschema.validate(instance=self._config, schema=schemas.containerConfig)

    def load(self, package_file):
        """Load the settings file into the settings object"""

        # Exit quickly if the package does not exist
        if not os.path.exists(package_file):
            logger.exit("%s does not exist." % package_file)

        # Default to round trip so we can save comments
        yaml = ruamel_yaml.YAML()

        # Store the original settings for update as we go
        with open(package_file, "r") as fd:
            self._config = yaml.load(fd.read())
        self.package_file = package_file