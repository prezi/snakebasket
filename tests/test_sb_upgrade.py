from nose.tools import nottest
from tests.test_pip import (here, reset_env, run_pip, assert_all_changes,
                            write_file, pyversion, _create_test_package,
                            _change_test_package_version)
from tests.local_repos import local_checkout
import re

def test_no_upgrade_pypi_if_prefer_pinned():
    """
    No upgrade of pypi package if 1)--prefer-pinned-revision is True and 2) previously installed version is pinned.

    """
    reset_env()
    run_pip('install', 'INITools==0.1', expect_error=True)
    result = run_pip('install','--prefer-pinned-revision', 'INITools', expect_error=True)
    assert not result.files_created, 'pip install INITools upgraded when it should not have'

def test_upgrade_pypi_if_no_prefer_pinned():
    """
    Upgrade pypi package if 1)--prefer-pinned-revision is False (default) and 2) previously installed version is pinned.

    """
    env = reset_env()
    run_pip('install', 'INITools==0.1', expect_error=True)
    result = run_pip('install', 'INITools', expect_error=True)
    assert result.files_created, 'pip install --upgrade did not upgrade'
    assert env.site_packages/'INITools-0.1-py%s.egg-info' % pyversion not in result.files_created

def test_no_upgrade_editable_if_prefer_pinned():
    """
    No upgrade of editable if 1)--prefer-pinned-revision is True and 2) previously installed version is pinned.

    """
    reset_env()

    local_url = local_checkout('git+http://github.com/prezi/sb-test-package.git')

    args = ['install',
        # older version
        '-e', '%s@0.2.0#egg=sb-test-package' % local_url]

    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('sb-test-package')

    args = ['install',
        '--prefer-pinned-revision',
        # unpinned newer version
        '-e', '%s#egg=sb-test-package' % local_url]
    result = run_pip(*args, **{"expect_error": True})

    # worrysome_files_created are all files that aren't located in .git/, created by the comparison `git fetch`
    expected_files_regex = re.compile('[.]git')
    worrysome_files_created = [file_path for file_path in result.files_created.keys() if not expected_files_regex.search(file_path)]

    assert not worrysome_files_created, 'sb install sb-test-package upgraded when it should not have'

def test_upgrade_editable_if_no_prefer_pinned():
    """
    Upgrade editable if 1)--prefer-pinned-revision is False (default) and 2) previously installed version is pinned.

    """
    env = reset_env()
    # run_pip('install', 'INITools==0.1', expect_error=True)
    # result = run_pip('install', 'INITools', expect_error=True)
    # assert result.files_created, 'pip install --upgrade did not upgrade'
    # assert env.site_packages/'INITools-0.1-py%s.egg-info' % pyversion not in result.files_created