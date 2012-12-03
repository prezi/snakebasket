"""
This file defines how versions of packages are compared.
Currently supported:
- comparing versions of editable (VCS) packages (if they're stored in git).
- comparing versions of non-editable packages.
Mixing the two is not currently supported

pip maintains a requirement set when processing a list of requirements to install.
When pip encounters a new requirement (by finding another requirements.txt for example),
that requirement is added to the requirement set. One by one, pip takes an element off the
requirement_set and installs it, adding any new dependencies to the requirement set if necessary.

As pip moves through the requirement set, packages can be:
1. already installed before pip even started
2. installed in this pip session
3. not installed yet, waiting in the requirement set.

Currently, this file only deals with the scenario where the package versions in conflict are both in state 3.
This may need to change in the future (in this case, we'd also have to deal with an existing checkout).
In these cases there is no existing checkout of the git repo containing the project, so a temporary checkout
must be made to determine the relationship between the two commits.
"""
from pip.exceptions import InstallationError
import re
from pip.util import call_subprocess
from pip.log import logger
from tempfile import mkdtemp
import os
from pip.vcs import subversion, git, bazaar, mercurial
from shutil import rmtree

class GitVersionComparator(object):

    LT = -1
    EQ = 0
    GT = 1
    version_re = re.compile(r'@([^/#@]*)#')
    commit_hash_re = re.compile("[a-z0-9]{5,40}")

    def __init__(self, pkg_repo_url):
        self.pkg_repo_url = pkg_repo_url

    def compare_versions(self, ver1, ver2):
        # short-circuit the comparison in the trivial case
        if ver1 == ver2:
            return self.EQ
        response = None
        exc = None
        self.create_checkout_parent()
        try:
            self.checkout_pkg_repo()
            commithashes =  [ver if self.is_valid_commit_hash(ver) else self.get_commit_hash_of_version_string(ver) for ver in [ver1, ver2]]
            if commithashes[0] == commithashes[1]:
                response = self.EQ
            elif self.is_parent_of(commithashes[0], commithashes[1]):
                response = self.LT
            elif self.is_parent_of(commithashes[1], commithashes[0]):
                response = self.GT
        except Exception, e:
            exc = e
        finally:
            self.remove_checkout_parent()
        if exc is not None:
            raise exc
        if response is None:
            raise InstallationError("Versions specified (%s and %s) point to commits which are not on the same line (%s and %s)." % (ver1, ver2, commithashes[0], commithashes[1]))
        return response

    def is_valid_commit_hash(self, hash_candidate):
        if re.match(self.commit_hash_re, hash_candidate) is None:
            return False
        try:
            ret = call_subprocess(['git', 'log', '-n', '1', hash_candidate, '--pretty=oneline'],
                show_stdout=False, cwd=self.checkout_dir)
            return ret.split(" ")[0] == hash_candidate
        except InstallationError:
            # call_subprocess returns raises an InstallationError when the return value of a command is not 0.
            # In this case it just means the given commit is not in the git repo.
            return False

    # copied from tests/local_repos.py
    def checkout_pkg_repo(self):
        remote_repository = self.pkg_repo_url
        vcs_classes = {'svn': subversion.Subversion,
                       'git': git.Git,
                       'bzr': bazaar.Bazaar,
                       'hg': mercurial.Mercurial}
        default_vcs = 'svn'
        if '+' not in self.pkg_repo_url:
            remote_repository = '%s+%s' % (default_vcs, remote_repository)
        vcs, repository_path = remote_repository.split('+', 1)
        vcs_class = vcs_classes[vcs]
        branch = ''
        if vcs == 'svn':
            branch = os.path.basename(remote_repository)
            repository_name = os.path.basename(remote_repository[:-len(branch)-1]) # remove the slash
        else:
            repository_name = os.path.basename(remote_repository)

        destination_path = os.path.join(self.checkout_parent_dir, repository_name)
        if not os.path.exists(destination_path):
            vcs_class(remote_repository).obtain(destination_path)
        self.checkout_dir = destination_path

    @classmethod
    def get_version_string_from_req(cls, req):
        """Extract editable requirement version from it's URL. A version is a git object (commit hash, tag or branch). """
        req_url = None
        try:
            req_url = req.url
        except AttributeError:
            pass
        if req_url is None:
            raise InstallationError(
                'No URL associated with editable requirement in version conflict. Cannot resolve (%s)' % req.name)
        version = GitVersionComparator.version_re.search(req_url)
        if version is not None and len(version.groups()) == 1:
            return version.groups()[0]
        # If there is no version information, the version they want is HEAD.
        return 'HEAD'

    def create_checkout_parent(self):
        self.checkout_parent_dir = mkdtemp()

    def remove_checkout_parent(self):
        rmtree(self.checkout_parent_dir)

    def get_commit_hash_of_version_string(self, version_string):
        ret = call_subprocess(['git', 'show-ref', '--dereference', version_string],
            show_stdout=False, cwd=self.checkout_dir)
        return ret.splitlines()[-1].split(" ")[0]

    def is_parent_of(self, parent, child):
        ret = call_subprocess(['git', 'merge-base', parent, child],
            show_stdout=False, cwd=self.checkout_dir)
        return ret.rstrip() == parent

class InstallReqChecker(object):

    def __init__(self):
        self.comparison_cache = ({}, {}) # two maps, one does a->b, the other one does b->a

    # The order of the operands doesn't matter, so we search both dicts.
    def get_cached_comparison_result(self, a, b):
        if self.comparison_cache[0].has_key(a) and self.comparison_cache[0].get(a).has_key(b):
            return self.comparison_cache[0][a][b]
        if self.comparison_cache[1].has_key(a) and self.comparison_cache[1][a].has_key(b):
            return self.comparison_cache[1][a][b]
        return None

    def save_comparison_result(self, a, b, result):
        if not self.comparison_cache[0].has_key(a):
            self.comparison_cache[0][a] = {}
        self.comparison_cache[0][a][b] = result
        if not self.comparison_cache[1].has_key(b):
            self.comparison_cache[1][b] = {}
        self.comparison_cache[1][b][a] = result

    def is_install_req_newer(self, install_req, existing_req):
        """Find the newer version of two editable packages"""
        reqs_in_conflict = [install_req, existing_req]
        editable_reqs = [req for req in reqs_in_conflict if req.editable == True]
        if len(editable_reqs) == 2:
            # This is an expensive comparison, so let's cache results
            competing_version_urls = [str(r.url) for r in reqs_in_conflict]
            result = self.get_cached_comparison_result(*competing_version_urls)
            if result is None:
                cmp = GitVersionComparator(install_req.url)
                result = cmp.compare_versions(*[GitVersionComparator.get_version_string_from_req(r) for r in reqs_in_conflict]) == cmp.GT
                self.save_comparison_result(competing_version_urls[0], competing_version_urls[1], result)
            else:
                logger.notify("USING CACHED COMPARISON: %s %s -> %s" % (competing_version_urls[0], competing_version_urls[1], result))
            return result
        elif len(editable_reqs) == 0:
            return reqs_in_conflict[0].req > reqs_in_conflict[1].req
        else: # mixed bag
            logger.notify("Conflicting requirements for %s, using editable version" % install_req.name)
            return editable_reqs[0] == install_req
