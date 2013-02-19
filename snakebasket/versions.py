"""
This file defines how versions of packages are compared.
Currently supported:
- comparing versions of editable (VCS) packages (if they're stored in git).
- comparing versions of non-editable packages.
Mixing the two results in the editable package always winning.

pip maintains a requirement set when processing a list of requirements to install.
When pip encounters a new requirement (by finding another requirements.txt for example),
that requirement is added to the requirement set. One by one, pip takes an element off the
requirement_set and installs it, adding any new dependencies to the requirement set if necessary.

The installation process is split into two steps. First, all packages and their dependencies are
downloaded. In the second step, the downloaded packages are all installed.

As pip moves through the process, packages can be:
* already installed before pip even started
* queued to be downloaded (in the requirement_set in pip lingo)
* already downloaded, but not yet installed
* just installed in this pip session
"""
from pip.exceptions import InstallationError
import re
from pip.util import call_subprocess
from pip.log import logger
import os
from pip.vcs import subversion, git, bazaar, mercurial
import pkg_resources
from distutils.version import StrictVersion, LooseVersion
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
        pinned_versions = [v for v in versions if v is not None]
        if len(pinned_versions) == 1 and self.prefer_pinned_revision:
            versions = [pinned_versions[0], pinned_versions[0]]
        else:
            versions = ["HEAD" if v is None else v for v in versions]
        commithashes = [ver if self.is_valid_commit_hash(ver) else self.get_commit_hash_of_version_string(ver) for ver in versions]
        if commithashes[0] == commithashes[1]:
            response = self.EQ
        elif self.is_parent_of(commithashes[0], commithashes[1]):
            response = self.LT
        elif self.is_parent_of(commithashes[1], commithashes[0]):
            response = self.GT
        if response is None:
            raise SeparateBranchException((ver1, commithashes[0]), (ver2, commithashes[1]))
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

    @staticmethod
    def do_fetch(repodir):
        call_subprocess(['git', 'fetch', '-q'], cwd=repodir)

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
            repository_name = os.path.basename(remote_repository[:-len(branch) - 1])  # remove the slash
        else:
            repository_name = os.path.basename(remote_repository)

        vcs_class(remote_repository).obtain(checkout_dir)
        return checkout_dir

    @classmethod
    def get_version_string_from_url(cls, req_url):
        """Extract editable requirement version from it's URL. A version is a git object (commit hash, tag or branch). """
        version = cls.version_re.search(req_url)
        if version is not None and len(version.groups()) == 1:
            version_string = version.groups()[0]
            if len(version_string) > 0:
                return version_string
        return None

    def get_commit_hash_of_version_string(self, version_string):
        ret = call_subprocess(['git', 'show-ref', '--dereference', version_string],
            show_stdout=False, cwd=self.checkout_dir)
        return ret.splitlines()[-1].split(" ")[0]

    def is_parent_of(self, parent, child):
        ret = call_subprocess(['git', 'merge-base', parent, child],
            show_stdout=False, cwd=self.checkout_dir)
        return ret.rstrip() == parent


class PackageData(object):

    # states
    UNKNOWN = 0
    PREINSTALLED = 1
    SELECTED = 2
    OBTAINED = 3

    def __init__(self, name, url=None, editable=False, location=None, version=None, comes_from=None, requirement=None):
        self.name = name
        self.url = url
        self.editable = editable
        self.location = location
        self.version = version
        self.comes_from = comes_from
        self.state = PackageData.UNKNOWN
        # The original InstallRequirement for FrozenRequirement from which this data was extracted
        self.requirement = requirement

    def __repr__(self):
        str = "%s %s" % (
            "(unnamed package)" if self.name is None else self.name,
            "(no version)" if self.version is None else "(version %s)" % self.version
        )
        if self.url is not None:
            str = str + " from %s" % self.url
        if self.editable:
            str = str + " [Editable]"
        return str

    def __cmp__(self, other):
        if self.version is None or other.version is None:
            # cannot compare None version
            raise Exception("Unable to compare None versions")
        try:
            sv = StrictVersion()
            sv.parse(self.version)
            return sv.__cmp__(other.version)
        except Exception:
            return LooseVersion(self.version).__cmp__(LooseVersion(other.version))

    def clone_dir(self, src_dir):
        # This method should only be run on editable InstallRequirement objects.
        if self.requirement is not None and hasattr(self.requirement, "build_location"):
            return self.requirement.build_location(src_dir)
        raise Exception("Cant't find build_location")

    @classmethod
    def from_dist(cls, dist, pre_installed=False):
        # dist is either an InstallRequirement or a FrozenRequirement.
        # We have to deal with installs from a URL (no name), pypi installs (with and without explicit versions)
        # and editable installs from git.
        name = None if not hasattr(dist, 'name') else dist.name
        editable = False if not hasattr(dist, 'editable') else dist.editable
        comes_from = None if not hasattr(dist, 'comes_from') else dist.comes_from
        url = None
        location = None
        version = None

        if comes_from is None and pre_installed:
            comes_from = "[already available]"

        if hasattr(dist, 'req'):
            if type(dist.req) == str:
                url = dist.req
                version = GitVersionComparator.get_version_string_from_url(url)
            elif hasattr(dist.req, 'specs') and len(dist.req.specs) == 1 and len(dist.req.specs[0]) == 2 and dist.req.specs[0][0] == '==':
                version = dist.req.specs[0][1]
        if url is None and hasattr(dist, 'url'):
            url = dist.url
        if hasattr(dist, 'location'):
            location = dist.location
        elif name is not None and url is not None and editable:
            # TODO: use non-virtualenv basedir instead of '/' if not in virtualenv
            location_candidate = os.path.join(os.environ.get('VIRTUAL_ENV', '/'), 'src', dist.name, '.git')
            if os.path.exists(location_candidate):
                location = location_candidate
                if hasattr(dist, 'url') and dist.url:
                    version = GitVersionComparator.get_version_string_from_url(dist.url)
                if version is None:
                    ret = call_subprocess(['git', 'log', '-n', '1', '--pretty=oneline'], show_stdout=False, cwd=location)
                    version = ret.split(" ")[0]
        pd = cls(
            name=name,
            url=url,
            location=location,
            editable=editable,
            version=version,
            comes_from=comes_from,
            requirement=dist)
        if pre_installed:
            pd.state = PackageData.PREINSTALLED
        return pd


class InstallReqChecker(object):

    def __init__(self, src_dir, requirements, successfully_downloaded):
        self.src_dir = src_dir
        self.comparison_cache = ({}, {})  # two maps, one does a->b, the other one does b->a
        self.pre_installed = {}  # maps name -> PackageData
        self.repo_up_to_date = {}  # maps local git clone path -> boolean
        self.requirements = requirements
        self.successfully_downloaded = successfully_downloaded
        try:
            self.load_installed_distributions()
        except Exception, e:
            logger.notify("Exception loading installed distributions " + str(e))
            raise
        self.prefer_pinned_revision = False

    def load_installed_distributions(self):
        import pip
        from pip.util import get_installed_distributions
        for dist in get_installed_distributions(local_only=True):
            pd = PackageData.from_dist(pip.FrozenRequirement.from_dist(dist, [], find_tags=True), pre_installed=True)
            if pd.editable and pd.location is not None:
                self.repo_up_to_date[pd.location] = False
            self.pre_installed[pd.name] = pd

    def checkout_if_necessary(self, pd):
        if pd.location is None:
            pd.location = GitVersionComparator.checkout_pkg_repo(pd.url, pd.clone_dir(self.src_dir))
            self.repo_up_to_date[pd.location] = True
        # self.repo_up_to_date[pd.location] is False if the git repo existed before this
        # snakebasket run, and has not yet been fetched (therefore may contain old data).
        elif self.repo_up_to_date.get(pd.location, True) == False:
            # Do a git fetch for repos which were not checked out recently.
            logger.notify("Performing git fetch in pre-existing directory %s" % pd.location)
            GitVersionComparator.do_fetch(pd.location)
            self.repo_up_to_date[pd.location] = True
        return pd.location

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
        return

    def find_potential_substitutes(self, name):
        """
        Returns other versions of the given package in requirement/downloaded/installed states without examining their
        version.
        """
        aliases = self.get_all_aliases(name)
        for package_name in aliases:
            if package_name in self.requirements:
                return PackageData.from_dist(self.requirements[package_name])
        downloaded = list(itertools.chain(*[
            [r for r in self.successfully_downloaded if r.name == pkg_resources] for package_name in aliases]))
        if downloaded:
            return PackageData.from_dist(downloaded[0])
        for package_name in aliases:
            if self.pre_installed.has_key(package_name):
                return PackageData.from_dist(self.pre_installed[package_name])

    def get_available_substitute(self, install_req):
        """Find an available substitute for the given package.
           Returns a PackageData object.
        """
        pd = PackageData.from_dist(install_req)
        if pd.name is None:
            # cannot find alternative versions without a name.
            return None

        existing_req = self.find_potential_substitutes(pd.name)
        if existing_req is None:
            return None

        packages_in_conflict = [pd, existing_req]
        editables = [p for p in packages_in_conflict if p.editable]
        if len(editables) == 2:
            # This is an expensive comparison, so let's cache results
            competing_version_urls = [str(r.url) for r in packages_in_conflict]
            cmp_result = self.get_cached_comparison_result(*competing_version_urls)
            if cmp_result is None:
                # We're comparing two versions of an editable because we know we're going to use the software in
                # the given repo (its just the version that's not decided yet).
                # So let's check out the repo into the src directory. Later (when we have the version) update_editable
                # will use the correct version anyway.
                repo_dir = self.checkout_if_necessary(packages_in_conflict[0])
                cmp = GitVersionComparator(repo_dir, self.prefer_pinned_revision)
                try:
                    versions = [GitVersionComparator.get_version_string_from_url(r.url) for r in packages_in_conflict]
                    if len([v for v in versions if v == None]) == 2:
                        # if either the existing requirement or the new candidate has no version info and is editable,
                        # we better update our clone and re-run setup.
                        return None  # OPTIMIZE return with the installed version
                    cmp_result = cmp.compare_versions(*versions)

                    self.save_comparison_result(competing_version_urls[0], competing_version_urls[1], cmp_result)
                except SeparateBranchException, exc:
                    raise InstallationError(
                        "%s: Conflicting versions cannot be compared as they are not direct descendants according to git. Exception: %s, Package data: %s." % (
                        packages_in_conflict[0].name,
                        str([p.__dict__ for p in packages_in_conflict]),
                        str(exc.args)))
            else:
                logger.debug("using cached comparison: %s %s -> %s" % (competing_version_urls[0], competing_version_urls[1], cmp_result))
            return None if cmp_result == GitVersionComparator.GT else packages_in_conflict[1]
        elif len(editables) == 0:
            versioned_packages = [p for p in packages_in_conflict if p.version is not None]
            if len(versioned_packages) == 0:
                if packages_in_conflict[0].url == packages_in_conflict[1].url:
                    # It doesn't matter which InstallationRequirement object we use, they represent the same dependency.
                    return packages_in_conflict[1]
                else:
                    raise InstallationError("%s: Package installed with no version information from different urls: %s and %s" % (packages_in_conflict[0].name, packages_in_conflict[0].url, packages_in_conflict[1].url))
            elif len(versioned_packages) == 1:

                # if the package to be installed is the versioned package
                if(packages_in_conflict[0] == versioned_packages[0]):
                    return None if self.prefer_pinned_revision else packages_in_conflict[1]

                # else the versioned package is the one already installed
                else:
                    return packages_in_conflict[1] if self.prefer_pinned_revision else None

            else:
                return packages_in_conflict[0] if packages_in_conflict[0] > packages_in_conflict[1] else packages_in_conflict[1]
        else:  # mixed case
            logger.notify("Conflicting requirements for %s, using editable version" % install_req.name)
            return editables[0]
