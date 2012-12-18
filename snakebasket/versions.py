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
import pkg_resources
from pip import FrozenRequirement
from pip.vcs.git import Git
from distutils.version import LooseVersion
import itertools

class SeparateBranchException(Exception):
    def __init__(self, *args, **kwargs):
        self.candidates = args

class GitVersionComparator(object):

    LT = -1
    EQ = 0
    GT = 1
    version_re = re.compile(r'@([^/#@]*)#')
    commit_hash_re = re.compile("[a-z0-9]{5,40}")

    def __init__(self, pkg_repo_dir, prefer_pinned_revision=False):
        self.checkout_dir = pkg_repo_dir
        self.prefer_pinned_revision = prefer_pinned_revision

    def compare_versions(self, ver1, ver2):
        # short-circuit the comparison in the trivial case
        if ver1 == ver2:
            return self.EQ
        response = None
        versions = [ver1, ver2]
        # Both versions can't be None, because would would have already returned self.EQ then.
        if self.prefer_pinned_revision:
            pinned_version = [v for v in versions if v is not None][0]
            versions = [pinned_version, pinned_version]
        else:
            versions = ["HEAD" if v is None else v for v in versions]
        commithashes =  [ver if self.is_valid_commit_hash(ver) else self.get_commit_hash_of_version_string(ver) for ver in versions]
        if commithashes[0] == commithashes[1]:
            response = self.EQ
        elif self.is_parent_of(commithashes[0], commithashes[1]):
            response = self.LT
        elif self.is_parent_of(commithashes[1], commithashes[0]):
            response = self.GT
        if response is None:
            raise SeparateBranchException((ver1, commithashes[0]),(ver2, commithashes[1]))
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
    @staticmethod
    def checkout_pkg_repo(remote_repository, checkout_dir):
        vcs_classes = {'svn': subversion.Subversion,
                       'git': git.Git,
                       'bzr': bazaar.Bazaar,
                       'hg': mercurial.Mercurial}
        default_vcs = 'svn'
        if '+' not in remote_repository:
            remote_repository = '%s+%s' % (default_vcs, remote_repository)
        vcs, repository_path = remote_repository.split('+', 1)
        vcs_class = vcs_classes[vcs]
        branch = ''
        if vcs == 'svn':
            branch = os.path.basename(remote_repository)
            repository_name = os.path.basename(remote_repository[:-len(branch)-1]) # remove the slash
        else:
            repository_name = os.path.basename(remote_repository)

        vcs_class(remote_repository).obtain(checkout_dir)
        return checkout_dir

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
        version = cls.version_re.search(req_url)
        if version is not None and len(version.groups()) == 1:
            return version.groups()[0]
        return None

    def get_commit_hash_of_version_string(self, version_string):
        ret = call_subprocess(['git', 'show-ref', '--dereference', version_string],
            show_stdout=False, cwd=self.checkout_dir)
        return ret.splitlines()[-1].split(" ")[0]

    def is_parent_of(self, parent, child):
        ret = call_subprocess(['git', 'merge-base', parent, child],
            show_stdout=False, cwd=self.checkout_dir)
        return ret.rstrip() == parent

class InstallReqChecker(object):

    def __init__(self, src_dir):
        self.src_dir = src_dir
        self.git_checkout_folders = {} # stores a (url, up_to_date) pair
        self.comparison_cache = ({}, {}) # two maps, one does a->b, the other one does b->a
        self.available_distributions = pkg_resources.AvailableDistributions()
        self.load_installed_distributions()
        self.prefer_pinned_revision = False


    def load_installed_distributions(self):
            for dist_name in self.available_distributions:
                for current_dist in self.available_distributions[dist_name]:
                    frozen_req_for_dist = FrozenRequirement.from_dist(current_dist, [], find_tags=True)
                    if (not self.git_checkout_folders.has_key(dist_name)) and frozen_req_for_dist.editable and frozen_req_for_dist.req[0:4] == 'git+':
                        # add this editable package to the list of editables
                        self.set_checkout_dir(dist_name, current_dist.location, False)


    def set_checkout_dir(self, requirement_name, location, up_to_date=True):
        self.git_checkout_folders[requirement_name] = (location, up_to_date)

    def get_checkout_dir(self, requirement_name):
        if self.git_checkout_folders.has_key(requirement_name):
            return self.git_checkout_folders[requirement_name][0]
        return None

    def checkout_dir_needs_update(self, requirement_name):
        return self.git_checkout_folders.has_key(requirement_name) and self.git_checkout_folders[requirement_name][1] == False

    def checkout_if_necessary(self, install_req):
        checkout_dir = self.get_checkout_dir(install_req.name)
        if checkout_dir is None:
            repo_dir = GitVersionComparator.checkout_pkg_repo(install_req.url, install_req.build_location(self.src_dir))
            self.set_checkout_dir(install_req.name, repo_dir)
        elif self.checkout_dir_needs_update(install_req.name):
            # Do a git fetch for repos which were not checked out recently.
            Git(install_req.url).update(checkout_dir, ['origin/master'])
            self.set_checkout_dir(install_req.name, checkout_dir, True)
        return self.get_checkout_dir(install_req.name)

    # Both directions are saved, but the outcome is the opposite, eg:
    # 0.1.2 vs 0.1.1 -> GT
    # 0.1.1 vs 0.1.2 -> LT
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
        self.comparison_cache[1][b][a] = result * -1

    def get_all_aliases(self, name):
        return [
            name,
            name.lower(),
            name.upper(),
            name.replace("-", "_"),
            name.replace("_", "-"),
            name[0].upper() + name[1:]]

    def filter_for_aliases(self, name, req_list):
        return list(itertools.chain(*[
            [r for r in req_list if r.name == alias] for alias in self.get_all_aliases(name)]))

    def req_installed_version(self, install_req):
        if not hasattr(install_req, 'name') or install_req.name is None:
            return None
        dist_list = list(itertools.chain(*[self.available_distributions[name] for name in self.get_all_aliases(install_req.name)]))
        if len(dist_list) == 0:
            return None
        for already_installed_req in dist_list:
            if self.is_install_req_newer(already_installed_req, install_req):
                return already_installed_req
        return None

    @classmethod
    def req_greater_than(cls, install_req1, install_req2):
        return LooseVersion(install_req1.req.__str__()) > LooseVersion(install_req2.req.__str__())

    def is_install_req_newer(self, install_req, existing_req):
        """Find the newer version of two editable packages"""
        reqs_in_conflict = [install_req, existing_req]
        editable_reqs = [req for req in reqs_in_conflict if req.editable == True]
        if len(editable_reqs) == 2:
            # This is an expensive comparison, so let's cache results
            competing_version_urls = [str(r.url) for r in reqs_in_conflict]
            cmp_result = self.get_cached_comparison_result(*competing_version_urls)
            if cmp_result is None:
                # We're comparing two versions of an editable because we know we're going to use the software in
                # the given repo (its just the version that's not decided yet).
                # So let's check out the repo into the src directory. Later (when we have the version) update_editable
                # will use the correct version anyway.
                repo_dir = self.checkout_if_necessary(install_req)
                cmp = GitVersionComparator(repo_dir, self.prefer_pinned_revision)
                try:
                    cmp_result = cmp.compare_versions(*[GitVersionComparator.get_version_string_from_req(r) for r in reqs_in_conflict])
                    self.save_comparison_result(competing_version_urls[0], competing_version_urls[1], cmp_result)
                except SeparateBranchException, exc:
                    raise InstallationError("%s: Conflicting versions cannot be compared as they are not direct descendants according to git.\n%s version %s (commit id %s)\n%s version %s (commit id %s)." % (
                        install_req.name,
                        reqs_in_conflict[0].url,
                        exc.args[0][0],
                        exc.args[0][1],
                        reqs_in_conflict[1].url,
                        exc.args[1][0],
                        exc.args[1][1]))
            else:
                logger.debug("using cached comparison: %s %s -> %s" % (competing_version_urls[0], competing_version_urls[1], cmp_result))
            return cmp_result == GitVersionComparator.GT
        elif len(editable_reqs) == 0:
            return self.req_greater_than(*reqs_in_conflict)
        else: # mixed case
            logger.notify("Conflicting requirements for %s, using editable version" % install_req.name)
            return editable_reqs[0] == install_req
