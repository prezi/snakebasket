import re
import os
import filecmp
import textwrap
import sys
from os.path import abspath, join, curdir, pardir

from nose.tools import assert_raises
from mock import patch

from pip.util import rmtree, find_command
from pip.exceptions import BadCommand

from tests.test_pip import (here, reset_env, run_pip, pyversion, mkdir,
                            src_folder, write_file)
from tests.local_repos import local_checkout
from tests.path import Path

def test_install_requirements_txt_processed():
    """
    Test requirements.txt is installed from repository.
    Note that we only test git, since that's all we use.
    """
    reset_env()
    args = ['install']
    args.extend(['-e',
                 '%s#egg=sb-test-package' %
                 local_checkout('git+http://github.com/prezi/sb-test-package.git')])
    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('sb-test-package', with_files=['.git'])
    result.assert_installed('pip-test-package', with_files=['.git'])

def test_install_requirements_with_env_processed():
    """
    Test requirements-ENV.txt is installed from repository if ENV is set and exists.
    """
    reset_env()
    args = ['install']
    args.extend(['--env', 'local', '-e',
                 '%s#egg=sb-test-package' %
                 local_checkout('git+http://github.com/prezi/sb-test-package.git')])
    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('sb-test-package', with_files=['.git'])
    # requirements-local.txt references 0.1.1 of pip-test-package
    assert 'Adding pip-test-package 0.1.1' in result.stdout

def test_install_requirements_recursive_env():
    """
    Test --env is propagated when installing requirements of requirements.
    """
    reset_env()
    args = ['install', '--env', 'local', '-e', 'git+http://github.com/prezi/sb-test-package.git@recursive-env-test#egg=recursive-env-test']
    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('recursive-env-test', with_files=['.git'])
    result.assert_installed('sb-test-package', with_files=['.git'])
    result.assert_installed('pip-test-package', with_files=['.git'])
    # recursive-env-test's requirements-local.txt references 0.1.1 of pip-test-package
    assert 'Adding pip-test-package 0.1.1' in result.stdout

def test_install_requirements_with_env_processed_recursive():
    """
    Test requirements-ENV.txt is installed from repository if ENV is set and exists.
    """
    reset_env()
    args = ['install']
    args.extend(['--env', 'local', '-e',
                 '%s#egg=sb-test-package' %
                 local_checkout('git+http://github.com/prezi/sb-test-package.git')])
    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('sb-test-package', with_files=['.git'])
    # requirements-local.txt references 0.1.1 of pip-test-package
    assert 'Adding pip-test-package 0.1.1' in result.stdout

def test_git_with_editable_with_no_requirements_for_env():
    """
    Snakebasket should revert to using requirements.txt if --env is specified but
    requirements-ENV.txt is not found.
    """
    reset_env()
    args = ['install']
    args.extend(['--env', 'badenv', '-e',
                 '%s#egg=sb-test-package' %
                 local_checkout('git+http://github.com/prezi/sb-test-package.git')])
    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('sb-test-package', with_files=['.git'])
    # requirements.txt references 0.1.2 of pip-test-package
    assert 'Adding pip-test-package 0.1.2' in result.stdout

