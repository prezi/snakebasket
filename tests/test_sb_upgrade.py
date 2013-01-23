
def test_upgrade_redownloads_unnamed_reqs():
    """ Requirements with a URL only will be downloaded again if upgrade is specified. """
    pass

def test_pypi_packages_redownloaded_only_if_upgrade_specified():
    """ PyPi packages should not be reinstalled unless --upgrade is specified. """
    pass


# Test with a github repo, which has at least 3 versions
#  - old: older version
#  - new: newer version
#  - ha a newest version in the branch
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
