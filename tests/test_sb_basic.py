import re
import os
import filecmp
import textwrap
import sys
from os.path import abspath, join, curdir, pardir

from nose.tools import assert_raises

from pip.util import rmtree, find_command
from pip.exceptions import BadCommand

from tests.test_pip import (here, reset_env, run_pip, pyversion, mkdir,
                            src_folder, write_file)

def test_sb_install_from_mirrors_with_specific_mirrors():
    """
    Test installing a package from a specific PyPI mirror.
    """
    e = reset_env()
    result = run_pip('install', '-vvv', '--index-url', 'https://pypi.python.org/simple/', 'INITools==0.2')
    egg_info_folder = e.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
    initools_folder = e.site_packages / 'initools'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)
