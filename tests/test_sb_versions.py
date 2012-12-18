from snakebasket import versions
from nose.tools import assert_equal, assert_raises
from pip.exceptions import InstallationError
from tests.test_pip import (here, reset_env, run_pip, pyversion, mkdir,
                            src_folder, write_file)
from tests.local_repos import local_checkout
from mock import Mock

def test_comparison():
    """ Comparison of version strings works for editable git repos """
    url_template = "git+http://github.com/prezi/sb-test-package.git@%s#egg=sb-test-package"
    def make_req(ver):
        req = Mock()
        req.name = "sb-test-packag"
        req.url = url_template % ver
        req.editable = True
        return req
    reset_env()
    checker = versions.InstallReqChecker()
    # commit hashes are compared as they should be:
    assert_equal(checker.is_install_req_newer(make_req('0.1.1'), make_req('0.1.2')), False)
    assert_equal(checker.is_install_req_newer(make_req('0.1.2'), make_req('0.1.1')), True)

    # tags are compared has they should be:
    assert_equal(checker.is_install_req_newer(make_req('6e513083955aded92f1833ff460dc233062a7292'), make_req('bd814b468924af1d41e9651f6b0d4fe0dc484a1e')), False)
    assert_equal(checker.is_install_req_newer(make_req('bd814b468924af1d41e9651f6b0d4fe0dc484a1e'), make_req('6e513083955aded92f1833ff460dc233062a7292')), True)

    # different aliases of the same commit id compare to be equal:
    assert_equal(checker.is_install_req_newer(make_req('master'), make_req('HEAD')), False)
    assert_equal(checker.is_install_req_newer(make_req('HEAD'), make_req('master')), False)

    def helper():
        checker.is_install_req_newer(make_req('test_branch_a'), make_req('test_branch_b'))
    # Divergent branches cannot be compared
    assert_raises(InstallationError, helper)

def test_requirement_set_will_include_correct_version():
    """ Out of two versions of the same package, the requirement set will contain the newer one. """
    reset_env()
    local_url = local_checkout('git+http://github.com/prezi/sb-test-package.git')
    args = ['install',
        # older version
        '-e', '%s@0.2.0#egg=sb-test-package' % local_url,
        # newer version
        '-e', '%s@0.2.1#egg=sb-test-package' % local_url]
    result = run_pip(*args, **{"expect_error": True})
    result.assert_installed('sb-test-package')
    assert "Cleaned up comparison directories." in result.stdout
    result = run_pip('freeze', **{"expect_error": True})
    v020 = '431bb08e4569bf22939d82591edb15e4074c4986'
    v021 = 'c55fc812d322dad26ffcc78263df1ba8e3c6134e'
    assert not (v020 in result.stdout)
    assert v021 in result.stdout

def test_editable_reqs_override_pypi_packages():
    """ Not Implemented: If a conflicing editable and pypi package are given, the editable will be installed. """
    pass

def test_requirement_aliases():
    """ Not Implemented: If two packages have names which are aliases of each other, they will be detected as version of the same package. """
    pass

def test_prefer_pinned_revision():
    """ Not Implemented: If --prefer_pinned_revision is given, than an explicitly specified version of a package is chosen over an implicit master/HEAD. """
    pass
