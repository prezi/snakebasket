from snakebasket import versions
from nose.tools import assert_equal, assert_raises
from pip.exceptions import InstallationError
from tests.test_pip import (here, reset_env, run_pip, pyversion, mkdir,
                            src_folder, write_file)
from tests.local_repos import local_checkout

def test_comparator():
    """ Comparison of version strings works for editable git repos """
    cmp = versions.GitVersionComparator('git+http://github.com/prezi/sb-test-package.git@0.1.1#egg=pip-test-package')
    # tags are compared has they should be:
    assert_equal(cmp.compare_versions('0.1.1', '0.1.2'), cmp.LT)
    # different aliases of the same commit id compare to be equal:
    assert_equal(cmp.compare_versions('master', 'HEAD'), cmp.EQ)
    def helper():
        cmp.compare_versions('test_branch_a', 'test_branch_b')
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
    result = run_pip('freeze', **{"expect_error": True})
    v020 = '431bb08e4569bf22939d82591edb15e4074c4986'
    v021 = 'c55fc812d322dad26ffcc78263df1ba8e3c6134e'
    assert not (v020 in result.stdout)
    assert v021 in result.stdout
