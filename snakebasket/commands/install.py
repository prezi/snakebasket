import sys
import os
from pip.req import InstallRequirement, InstallationError, _make_build_dir, parse_requirements, Requirements
from pip.commands.install import InstallCommand, RequirementSet
from pip.exceptions import BestVersionAlreadyInstalled, CommandError, DistributionNotFound
from pip.vcs import vcs
from urllib2 import HTTPError
import pkg_resources
from pip.log import logger
from pip.index import Link
import tempfile
import shutil
from pip.backwardcompat import home_lib
from pip.locations import virtualenv_no_global
from pip.util import dist_in_usersite
from pip.baseparser import create_main_parser 
from ..versions import  InstallReqChecker, PackageData

class ExtendedRequirements(Requirements):
    def __init__(self, *args, **kwargs):
        super(ExtendedRequirements, self).__init__(*args, **kwargs)

    def __delitem__(self, key, value):
        if key in self._keys:
            self._keys = [k for k in self._keys if k != key]
        del self._dict[key]

class RecursiveRequirementSet(RequirementSet):

    def __init__(self, *args, **kwargs):
        super(RecursiveRequirementSet, self).__init__(*args, **kwargs)
        self.options = None
        self.requirements = ExtendedRequirements()
        self.install_req_checker = InstallReqChecker(
            self.src_dir,
            self.requirements,
            self.successfully_downloaded)

    def set_options(self, value):
        self.options = value
        self.install_req_checker.prefer_pinned_revision = value.prefer_pinned_revision

    def prepare_files(self, finder, force_root_egg_info=False, bundle=False):

        """Prepare process. Create temp directories, download and/or unpack files."""
        unnamed = list(self.unnamed_requirements)
        reqs = list(self.requirements.values())
        while reqs or unnamed:
            if unnamed:
                req_to_install = unnamed.pop(0)
            else:
                req_to_install = reqs.pop(0)
            install = True
            best_installed = False
            not_found = None
            if not self.ignore_installed and not req_to_install.editable:
                req_to_install.check_if_exists()

                if req_to_install.satisfied_by:

                    substitute = self.install_req_checker.get_available_substitute(req_to_install)

                    # if the req_to_install is identified as the best available substitue
                    # AND
                    # ( no version with req_to_install.name has been installed 
                        # OR a different version of req_to_install.name has been installed
                    # )
                    # then set the self.upgrade flag to True to install req_to_install

                    if (
                        req_to_install == substitute.requirement
                        and
                        (
                            req_to_install.name not in self.install_req_checker.pre_installed
                            or
                            self.install_req_checker.pre_installed[req_to_install.name].requirement is not req_to_install
                        )
                    ):
                        self.upgrade = True 

                    if self.upgrade:
                        if not self.force_reinstall and not req_to_install.url:
                            try:
                                url = finder.find_requirement(
                                    req_to_install, self.upgrade)
                            except BestVersionAlreadyInstalled:
                                best_installed = True
                                install = False
                            except DistributionNotFound:
                                not_found = sys.exc_info()[1]
                            else:
                                # Avoid the need to call find_requirement again
                                req_to_install.url = url.url

                        if not best_installed:
                            #don't uninstall conflict if user install and conflict is not user install
                            if not (self.use_user_site and not dist_in_usersite(req_to_install.satisfied_by)):
                                req_to_install.conflicts_with = req_to_install.satisfied_by
                            req_to_install.satisfied_by = None
                    else:
                        install = False
                if req_to_install.satisfied_by:
                    if best_installed:
                        logger.notify('Requirement already up-to-date: %s'
                                      % req_to_install)
                    else:
                        logger.notify('Requirement already satisfied '
                                      '(use --upgrade to upgrade): %s'
                                      % req_to_install)
            if req_to_install.editable:
                logger.notify('Obtaining %s' % req_to_install)
            elif install:
                logger.notify('Downloading/unpacking %s' % req_to_install)
            logger.indent += 2
            try:
                is_bundle = False
                if req_to_install.editable:
                    if req_to_install.source_dir is None:
                        location = req_to_install.build_location(self.src_dir)
                        req_to_install.source_dir = location
                    else:
                        location = req_to_install.source_dir
                    if not os.path.exists(self.build_dir):
                        _make_build_dir(self.build_dir)
                    req_to_install.update_editable(not self.is_download)
                    if self.is_download:
                        req_to_install.run_egg_info()
                        req_to_install.archive(self.download_dir)
                    else:
                        req_to_install.run_egg_info()
                elif install:
                    ##@@ if filesystem packages are not marked
                    ##editable in a req, a non deterministic error
                    ##occurs when the script attempts to unpack the
                    ##build directory

                    # NB: This call can result in the creation of a temporary build directory
                    location = req_to_install.build_location(self.build_dir, not self.is_download)

                    ## FIXME: is the existance of the checkout good enough to use it?  I don't think so.
                    unpack = True
                    url = None
                    if not os.path.exists(os.path.join(location, 'setup.py')):
                        ## FIXME: this won't upgrade when there's an existing package unpacked in `location`
                        if req_to_install.url is None:
                            if not_found:
                                raise not_found
                            url = finder.find_requirement(req_to_install, upgrade=self.upgrade)
                        else:
                            ## FIXME: should req_to_install.url already be a link?
                            url = Link(req_to_install.url)
                            assert url
                        if url:
                            try:
                                self.unpack_url(url, location, self.is_download)
                            except HTTPError:
                                e = sys.exc_info()[1]
                                logger.fatal('Could not install requirement %s because of error %s'
                                             % (req_to_install, e))
                                raise InstallationError(
                                    'Could not install requirement %s because of HTTP error %s for URL %s'
                                    % (req_to_install, e, url))
                        else:
                            unpack = False
                    if unpack:
                        is_bundle = req_to_install.is_bundle
                        if is_bundle:
                            req_to_install.move_bundle_files(self.build_dir, self.src_dir)
                            for subreq in req_to_install.bundle_requirements():
                                reqs.append(subreq)
                                self.add_requirement(subreq)
                        elif self.is_download:
                            req_to_install.source_dir = location
                            req_to_install.run_egg_info()
                            if url and url.scheme in vcs.all_schemes:
                                req_to_install.archive(self.download_dir)
                        else:
                            req_to_install.source_dir = location
                            req_to_install.run_egg_info()
                            if force_root_egg_info:
                                # We need to run this to make sure that the .egg-info/
                                # directory is created for packing in the bundle
                                req_to_install.run_egg_info(force_root_egg_info=True)
                            req_to_install.assert_source_matches_version()
                            #@@ sketchy way of identifying packages not grabbed from an index
                            if bundle and req_to_install.url:
                                self.copy_to_build_dir(req_to_install)
                                install = False
                            # req_to_install.req is only avail after unpack for URL pkgs
                        # repeat check_if_exists to uninstall-on-upgrade (#14)
                        req_to_install.check_if_exists()
                        if req_to_install.satisfied_by:
                            if self.upgrade or self.ignore_installed:
                                #don't uninstall conflict if user install and and conflict is not user install
                                if not (self.use_user_site and not dist_in_usersite(req_to_install.satisfied_by)):
                                    req_to_install.conflicts_with = req_to_install.satisfied_by
                                req_to_install.satisfied_by = None
                            else:
                                install = False
                if not is_bundle:
                    ## FIXME: shouldn't be globally added:
                    finder.add_dependency_links(req_to_install.dependency_links)
                    if (req_to_install.extras):
                        logger.notify("Installing extra requirements: %r" % ','.join(req_to_install.extras))
                    if not self.ignore_dependencies:
                        for req in req_to_install.requirements(req_to_install.extras):
                            try:
                                name = pkg_resources.Requirement.parse(req).project_name
                            except ValueError:
                                e = sys.exc_info()[1]
                                ## FIXME: proper warning
                                logger.error('Invalid requirement: %r (%s) in requirement %s' % (req, e, req_to_install))
                                continue
                            if self.has_requirement(name):
                                ## FIXME: check for conflict
                                continue
                            subreq = InstallRequirement(req, req_to_install)
                            reqs.append(subreq)
                            self.add_requirement(subreq)
                        if req_to_install.editable and req_to_install.source_dir:
                            for subreq in self.install_requirements_txt(req_to_install):
                                if self.add_requirement(subreq):
                                    reqs.append(subreq)
                    if not self.has_requirement(req_to_install.name):
                        #'unnamed' requirements will get added here
                        self.add_requirement(req_to_install)
                    if self.is_download or req_to_install._temp_build_dir is not None:
                        self.reqs_to_cleanup.append(req_to_install)
                else:
                    self.reqs_to_cleanup.append(req_to_install)

                if install:
                    self.successfully_downloaded.append(req_to_install)
                    if bundle and (req_to_install.url and req_to_install.url.startswith('file:///')):
                        self.copy_to_build_dir(req_to_install)
            finally:
                logger.indent -= 2


    def add_requirement(self, install_req):
        name = install_req.name
        install_req.as_egg = self.as_egg
        install_req.use_user_site = self.use_user_site
        if not name:
            #url or path requirement w/o an egg fragment
            # make sure no list item has this same url:
            if install_req.url is None or len([i for i in self.unnamed_requirements if i.url == install_req.url]) == 0:
                self.unnamed_requirements.append(install_req)
            return True
        satisfied_by = self.install_req_checker.get_available_substitute(install_req)
        if satisfied_by is not None:
            logger.notify("Package %s already satisfied by %s" % (name, satisfied_by.__repr__()))
        else:
            self.requirements[name] = install_req
        for n in self.install_req_checker.get_all_aliases(name):
            self.requirement_aliases[n] = name
        return satisfied_by is None

    def install_requirements_txt(self, req_to_install):
        """If ENV is set, try to parse requirements-ENV.txt, falling back to requirements.txt if it exists."""
        rtxt_candidates = ["requirements.txt"]
        if self.options and self.options.env:
            rtxt_candidates.insert(0, "requirements-{0}.txt".format(self.options.env))
        for r in rtxt_candidates:
            fullpath = os.path.join(req_to_install.source_dir, r)
            if os.path.exists(fullpath):
                logger.notify("Found {0} in {1}, installing extra dependencies.".format(r, req_to_install.name))
                return parse_requirements(fullpath, req_to_install.name, None, self.options)
        return []

class RInstallCommand(InstallCommand):
    summary = 'Recursively install packages'

    def __init__(self, *args, **kw):
        super(RInstallCommand, self).__init__(*args, **kw)
        # Add env variable to specify which requirements.txt to run
        self.parser.add_option(
            '--env',
            dest='env',
            action='store',
            default=None,
            metavar='ENVIRONMENT',
            help='Specifies an environment (eg, production). This means requirements-ENV.txt will be evaluated by snakebasket.')
        self.parser.add_option(
            '--prefer-pinned-revision',
            dest='prefer_pinned_revision',
            action='store_true',
            default=False,
            help='When comparing editables with explicitly given version with the default (no-version data in URL), use the pinned version.')


    def run(self, options, args):
        if options.download_dir:
            options.no_install = True
            options.ignore_installed = True
        options.build_dir = os.path.abspath(options.build_dir)
        options.src_dir = os.path.abspath(options.src_dir)
        install_options = options.install_options or []
        if options.use_user_site:
            if virtualenv_no_global():
                raise InstallationError("Can not perform a '--user' install. User site-packages are not visible in this virtualenv.")
            install_options.append('--user')
        if options.target_dir:
            options.ignore_installed = True
            temp_target_dir = tempfile.mkdtemp()
            options.target_dir = os.path.abspath(options.target_dir)
            if os.path.exists(options.target_dir) and not os.path.isdir(options.target_dir):
                raise CommandError("Target path exists but is not a directory, will not continue.")
            install_options.append('--home=' + temp_target_dir)
        global_options = options.global_options or []
        index_urls = [options.index_url] + options.extra_index_urls
        if options.no_index:
            logger.notify('Ignoring indexes: %s' % ','.join(index_urls))
            index_urls = []

        finder = self._build_package_finder(options, index_urls)

        requirement_set = RecursiveRequirementSet(
            build_dir=options.build_dir,
            src_dir=options.src_dir,
            download_dir=options.download_dir,
            download_cache=options.download_cache,
            upgrade=options.upgrade,
            as_egg=options.as_egg,
            ignore_installed=options.ignore_installed,
            ignore_dependencies=options.ignore_dependencies,
            force_reinstall=options.force_reinstall,
            use_user_site=options.use_user_site)
        requirement_set.set_options(options)
        for name in args:
            requirement_set.add_requirement(
                InstallRequirement.from_line(name, None))
        for name in options.editables:
            requirement_set.add_requirement(
                InstallRequirement.from_editable(name, default_vcs=options.default_vcs))
        for filename in options.requirements:
            for req in parse_requirements(filename, finder=finder, options=options):
                requirement_set.add_requirement(req)
        if not requirement_set.has_requirements:
            if args or options.editables or options.requirements:
                msg = 'All requirements seem to be already satisfied.'
                logger.notify(msg)
            else:
                opts = {'name': self.name}
                if options.find_links:
                    msg = ('You must give at least one valid requirement to %(name)s '
                           '(maybe you meant "pip %(name)s %(links)s"?)' %
                           dict(opts, links=' '.join(options.find_links)))
                else:
                    msg = ('You must give at least one valid requirement '
                           'to %(name)s (see "pip help %(name)s")' % opts)
                logger.warn(msg)

            return

        if (options.use_user_site and
            sys.version_info < (2, 6)):
            raise InstallationError('--user is only supported in Python version 2.6 and newer')

        import setuptools
        if (options.use_user_site and
            requirement_set.has_editables and
            not getattr(setuptools, '_distribute', False)):

            raise InstallationError('--user --editable not supported with setuptools, use distribute')

        if not options.no_download:
            requirement_set.prepare_files(finder, force_root_egg_info=self.bundle, bundle=self.bundle)
        else:
            requirement_set.locate_files()

        if not options.no_install and not self.bundle:
            requirement_set.install(install_options, global_options, root=options.root_path)
            installed = ' '.join([req.name for req in
                                  requirement_set.successfully_installed])
            if installed:
                logger.notify('Successfully installed %s' % installed)
        elif not self.bundle:
            downloaded = ' '.join([req.name for req in
                                   requirement_set.successfully_downloaded])
            if downloaded:
                logger.notify('Successfully downloaded %s' % downloaded)
        elif self.bundle:
            requirement_set.create_bundle(self.bundle_filename)
            logger.notify('Created bundle in %s' % self.bundle_filename)
            # Clean up
        if not options.no_install or options.download_dir:
            requirement_set.cleanup_files(bundle=self.bundle)
        if options.target_dir:
            if not os.path.exists(options.target_dir):
                os.makedirs(options.target_dir)
            lib_dir = home_lib(temp_target_dir)
            for item in os.listdir(lib_dir):
                shutil.move(
                    os.path.join(lib_dir, item),
                    os.path.join(options.target_dir, item)
                )
            shutil.rmtree(temp_target_dir)
        return requirement_set