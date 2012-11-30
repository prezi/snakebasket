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

    def __init__(self, pkg_repo_url):
        self.pkg_repo_url = pkg_repo_url

    def compare_versions(self, ver1, ver2):
        response = None
        exc = None
        self.create_checkout_parent()
        try:
            self.checkout_pkg_repo()
            commithash1 = self.get_commit_hash_of_version_string(ver1)
            commithash2 = self.get_commit_hash_of_version_string(ver2)
            if commithash1 == commithash2:
                response = self.EQ
            elif self.is_parent_of(commithash1, commithash2):
                response = self.LT
            elif self.is_parent_of(commithash2, commithash1):
                response = self.GT
        except Exception, e:
            exc = e
        finally:
            self.remove_checkout_parent()
        if exc is not None:
            raise exc
        if response is None:
            raise InstallationError("Versions specified (%s and %s) point to commits which are not on the same line (%s and %s)." % (ver1, ver2, commithash1, commithash2))
        return response

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

def all_candidates_editable(reqs_in_conflict):
    """All candidates should be editable or not-editable, no mixing"""
    non_editables = len([req for req in reqs_in_conflict if req.editable == False])
    if non_editables == len(reqs_in_conflict):
        return False
    elif non_editables == 0:
        return True
    else:
        if len([req for req in reqs_in_conflict if req.editable == False]) > 0:
            raise InstallationError(
                'Double requirement given (%s) and one of the candidates is not editable. Mixing editable and non-editable requirements unsupported.' % (str(reqs_in_conflict[0].name)))

def is_install_req_newer(install_req, requirement_set):
    """Find the newer version of two editable packages"""
    reqs_in_conflict = [install_req, requirement_set.get_requirement(install_req.name)]
    if all_candidates_editable(reqs_in_conflict):
        cmp = GitVersionComparator(install_req.url)
        return cmp.compare_versions(*[cmp.get_version_string_from_req(r) for r in reqs_in_conflict]) == cmp.GT
    else:
        return reqs_in_conflict[0].req > reqs_in_conflict[1].req
