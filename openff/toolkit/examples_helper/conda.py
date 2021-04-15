"""Python wrapper around the mamba and conda cli tools"""

import subprocess as sp
from pathlib import Path

from openff.toolkit.examples_helper.utils import echo


def cmd(*args, text=True, check=True, **kwargs):
    """Run conda or mamba with the given commands and arguments"""
    return sp.run(["conda", *args], text=text, check=check, **kwargs)


def create_environment(prefix=None, name=None, dry_run=False, quiet=False):
    """Create a new conda environment with the given prefix or name"""
    conda_args = []
    if dry_run:
        conda_args.append("--dry-run")
    if quiet:
        conda_args.append("--quiet")

    if prefix and name:
        raise ValueError("prefix and name are mutually exclusive")
    if not (prefix or name):
        raise ValueError("prefix or name is required")
    if prefix:
        conda_args.append("--prefix")
        conda_args.append(str(prefix))
    if name:
        conda_args.append("--name")
        conda_args.append(str(name))

    cmd("create", *conda_args)


def update_envs(environments, prefix=None, name=None, dry_run=False, quiet=False):
    """Update the conda environment given by prefix or name with the provided environment.yml files"""
    conda_args = []
    if prefix and name:
        raise ValueError("prefix and name are mutually exclusive")
    if prefix:
        conda_args.append("--prefix")
        conda_args.append(str(prefix))
    elif name:
        conda_args.append("--name")
        conda_args.append(str(name))
    if quiet:
        conda_args.append("--quiet")

    if dry_run:
        echo("conda env update", *conda_args, *environments)
    else:
        cmd(
            "env",
            "update",
            *conda_args,
            *environments,
        )


def get_current_prefix():
    """Return the currently active conda environment

    Hacky as hell, but Conda doesn't seem to provide a robust solution:
    https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#determining-your-current-environment
    """
    proc = cmd("info", "--envs", capture_output=True)
    for line in proc.stdout.splitlines():
        if line.startswith("#"):
            continue
        _name, _, prefix = line.partition(" * ")
        if prefix:
            return Path(prefix.strip())
    raise ValueError("Could not determine prefix")


def overwrite_local_module(module_name, local_module, name=None, prefix=None):
    """Overwrite a module installed from Conda with a local module"""

    conda_args = []
    if prefix and name:
        raise ValueError("prefix and name are mutually exclusive")
    if prefix:
        conda_args.append("--prefix")
        conda_args.append(str(prefix))
    elif name:
        conda_args.append("--name")
        conda_args.append(str(name))

    cmd("uninstall", *conda_args, "--force", module_name)
    cmd("run", *conda_args, "--cwd", local_module, "pip", "install", "-e", ".")