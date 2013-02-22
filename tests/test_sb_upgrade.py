from nose.tools import nottest
from tests.test_pip import (here, reset_env, run_pip, assert_all_changes,
                            write_file, pyversion, _create_test_package,
                            _change_test_package_version)
from tests.local_repos import local_checkout

def test_no_upgrade_if_prefer_pinned():
    """
    No upgrade if 1)--prefer-pinned-revision is True and 2) previously installed version is pinned.

    """
    reset_env()
    run_pip('install', 'INITools==0.1', expect_error=True)
    result = run_pip('install','--prefer-pinned-revision', 'INITools', expect_error=True)
    assert not result.files_created, 'pip install INITools upgraded when it should not have'

def test_upgrade_if_no_prefer_pinned():
    """
    Upgrade if 1)--prefer-pinned-revision is False and 2) previously installed version is pinned.

    """
    env = reset_env()
    run_pip('install', 'INITools==0.1', expect_error=True)
    result = run_pip('install', 'INITools', expect_error=True)
    assert result.files_created, 'pip install --upgrade did not upgrade'
    assert env.site_packages/'INITools-0.1-py%s.egg-info' % pyversion not in result.files_created

def test_upgrade_redownloads_unnamed_reqs():
    """ Requirements with a URL only will be downloaded again if upgrade is specified. """
    pass

def test_pypi_packages_redownloaded_only_if_upgrade():
    """ PyPi packages should not be reinstalled unless the installation is an upgrade. """
    pass

def test_versions_old_new():
    """ SB should install new in this case. """
    pass


def test_versions_new_old():
    """ SB should install new in this case. """
    pass


def test_versions_none_old_new():
    """ SB should install newest (because of none) in this case. """
    pass


def test_versions_none_new_old():
    """ SB should install newest (because of none) in this case. """
    pass


def test_versions_old_none_new():
    """ SB should install newest (because of none) in this case. """
    pass


def test_versions_old_new_none():
    """ SB should install newest (because of none) in this case. """
    pass


def test_versions_new_none_old():
    """ SB should install newest (because of none) in this case. """
    pass


def test_versions_new_old_none():
    """ SB should install newest (because of none) in this case. """
    pass


def test_versions_prefpinned_none_old_new():
    """ SB should install new (because of prefpinned) in this case. """
    pass


def test_versions_prefpinned_none_new_old():
    """ SB should install new (because of prefpinned) in this case. """
    pass


def test_versions_prefpinned_old_none_new():
    """ SB should install new (because of prefpinned) in this case. """
    pass


def test_versions_prefpinned_old_new_none():
    """ SB should install new (because of prefpinned) in this case. """
    pass


def test_versions_prefpinned_new_none_old():
    """ SB should install new (because of prefpinned) in this case. """
    pass


def test_versions_prefpinned_new_old_none():
    """ SB should install new (because of prefpinned) in this case. """
    pass
