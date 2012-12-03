from snakebasket import versions
from nose.tools import assert_equal, assert_raises
from pip.exceptions import InstallationError
from tests.test_pip import (here, reset_env, run_pip, pyversion, mkdir,
                            src_folder, write_file)
from tests.local_repos import local_checkout
from mock import Mock

# Only planned tests in this file right now

def test_pre_existing_editable_dir_get_git_pull_before_use()
    """ Not implemented yet: pre-existing editable distributions should get a git fetch before use for comparisons """
    assert True
