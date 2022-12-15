# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
import os
import pathlib
import subprocess
import typing as t

import capellambse
from capellambse import helpers
from capellambse.loader import modelinfo

from . import FileHandler

LOGGER = logging.getLogger(__name__)


class SubversionFileHandler(FileHandler):
    """File handler for ``svn://`` protocols.

    Parameters
    ----------
    path
        The base URL of the remote subversion server.
    revision
        The revision to use. If not given or ``None``, use the latest
        revision available at construction time.
    username
        The user name for authentication with the subversion server.
    password
        The password for authentication with the subversion server.

    See Also
    --------
    capellambse.loader.filehandler.FileHandler :
        Documentation of common parameters.
    """

    def __init__(
        self,
        path: str | os.PathLike,
        *,
        revision: int | str | None = None,
        username: str | None = None,
        password: str | None = None,
        subdir: str | pathlib.PurePosixPath = "/",
    ) -> None:
        super().__init__(path, subdir=subdir)
        self.__revision = revision
        self.__username = username
        self.__password = password

        self.__cache_dir = pathlib.Path(
            capellambse.dirs.user_cache_dir, "models", helpers.hashslug(path)
        )
        self.__cache_dir.mkdir(parents=True, exist_ok=True)

        co_args = ("checkout", "--depth=empty", self.path, self.__cache_dir)
        try:
            self.__svn(*co_args)
        except subprocess.CalledProcessError as err:
            LOGGER.warning("Initial checkout failed, trying to clean up")
            try:
                self.__svn("cleanup")
                LOGGER.info("Cleanup successful, retrying checkout")
                self.__svn(*co_args)
            except subprocess.CalledProcessError:
                raise err from None

    def open(
        self,
        filename: str | pathlib.PurePosixPath,
        mode: t.Literal["r", "rb", "w", "wb"] = "rb",
    ) -> t.BinaryIO:
        path = helpers.normalize_pure_path(filename, base=self.subdir)
        if "w" in mode:
            raise NotImplementedError("Writing to SVN is not supported yet")
        for segment in reversed(path.parents[1:-1]):
            self.__svn("update", "--depth=immediates", segment)
        self.__svn("update", "--depth=immediates", path.parent)
        return open(self.__cache_dir / path, "rb")

    def get_model_info(self) -> modelinfo.ModelInfo:
        if self.__revision is not None:
            revision = str(self.__revision)
        else:
            revision = None

        return modelinfo.ModelInfo(
            url=str(self.path),
            revision=revision,
        )

    def __svn(self, subcommand: str, *args: t.Any) -> bytes:
        returncode = 0
        stderr = b""

        cmd = ["svn", "--non-interactive", subcommand]
        if self.__username:
            cmd += ["--username", self.__username]
        if self.__password:
            cmd += ["--password", self.__password]
        if self.__revision:
            cmd += ["--revision", str(self.__revision)]
        cmd += [str(i) for i in args]

        LOGGER.debug("Running svn command %r", cmd)
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                cwd=self.__cache_dir,
            )
            returncode = proc.returncode
            stderr = proc.stderr
            return proc.stdout
        except subprocess.CalledProcessError as err:
            returncode = err.returncode
            stderr = err.stderr
            raise
        finally:
            level = (logging.DEBUG, logging.WARNING)[returncode != 0]
            for line in stderr.decode("utf-8").splitlines():
                LOGGER.getChild("stderr").log(level, "%s", line)
