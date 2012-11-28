import sys
import os
from pip.req import InstallRequirement, InstallationError, _make_build_dir, parse_requirements, display_path, url_to_path
from pip.commands.install import InstallCommand, RequirementSet
from pip.exceptions import BestVersionAlreadyInstalled, CommandError
from pip.vcs import vcs
from urllib2 import HTTPError
import pkg_resources
from pip.log import logger
from pip.index import Link
import tempfile
import shutil

class RecursiveRequirementSet(RequirementSet):

    def __init__(self, *args, **kwargs):
        super(RecursiveRequirementSet, self).__init__(*args, **kwargs)
        self.requirements_env = None

    @property
    def requirements_env(self):
        return self.requirements_env

    @requirements_env.setter
    def requirements_env(self, value):
        self.requirements_env = value

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
            if not self.ignore_installed and not req_to_install.editable:
                req_to_install.check_if_exists()
                if req_to_install.satisfied_by:
                    if self.upgrade:
                        if not self.force_reinstall:
                            try:
                                url = finder.find_requirement(
                                    req_to_install, self.upgrade)
                            except BestVersionAlreadyInstalled:
                                best_installed = True
                                install = False
                            else:
                                # Avoid the need to call find_requirement again
                                req_to_install.url = url.url

                        if not best_installed:
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
                if req_to_install.url and req_to_install.url.lower().startswith('file:'):
                    logger.notify('Unpacking %s' % display_path(url_to_path(req_to_install.url)))
                else:
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

                    location = req_to_install.build_location(self.build_dir, not self.is_download)
                    ## FIXME: is the existance of the checkout good enough to use it?  I don't think so.
                    unpack = True
                    url = None
                    if not os.path.exists(os.path.join(location, 'setup.py')):
                        ## FIXME: this won't upgrade when there's an existing package unpacked in `location`
                        if req_to_install.url is None:
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
                                reqs.append(subreq)
                                self.add_requirement(subreq)
                    if req_to_install.name not in self.requirements:
                        self.requirements[req_to_install.name] = req_to_install
                    if self.is_download:
                        self.reqs_to_cleanup.append(req_to_install)
                else:
                    self.reqs_to_cleanup.append(req_to_install)

                if install:
                    self.successfully_downloaded.append(req_to_install)
                    if bundle and (req_to_install.url and req_to_install.url.startswith('file:///')):
                        self.copy_to_build_dir(req_to_install)
            finally:
                logger.indent -= 2


    def install_requirements_txt(self, req_to_install):
        rtxt_candidates = ["requirements.txt"]
        if self.requirements_env:
            rtxt_candidates.insert(0, "requirements-{0}.txt".format(self.requirements_env))
        for r in rtxt_candidates:
            fullpath = os.path.join(req_to_install.source_dir, r)
            if os.path.exists(fullpath):
                logger.notify("Found {0} in {1}, installing extra dependencies.".format(r, req_to_install.name))
                return parse_requirements(fullpath, req_to_install.name, None, opts)
        return []

class RInstallCommand(InstallCommand):
    summary = 'Recursively install packages'

    def __init__(self):
        super(RInstallCommand, self).__init__()
        # Add env variable to specify which requirements.txt to run
        self.parser.add_option(
            '--env',
            dest='env',
            action='store',
            default=None,
            metavar='ENVIRONMENT',
            help='Specifies an environment (eg, production). This means requirements-ENV.txt will be evaluated by snakebasket.')

    def run(self, options, args):
        if options.download_dir:
            options.no_install = True
            options.ignore_installed = True
        options.build_dir = os.path.abspath(options.build_dir)
        options.src_dir = os.path.abspath(options.src_dir)
        install_options = options.install_options or []
        if options.use_user_site:
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
            ignore_installed=options.ignore_installed,
            ignore_dependencies=options.ignore_dependencies,
            force_reinstall=options.force_reinstall)
        requirement_set.requirements_env = options.env
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
            opts = {'name': self.name}
            if options.find_links:
                msg = ('You must give at least one requirement to %(name)s '
                       '(maybe you meant "pip %(name)s %(links)s"?)' %
                       dict(opts, links=' '.join(options.find_links)))
            else:
                msg = ('You must give at least one requirement '
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
            requirement_set.install(install_options, global_options)
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
            lib_dir = os.path.join(temp_target_dir, "lib/python/")
            for item in os.listdir(lib_dir):
                shutil.move(
                    os.path.join(lib_dir, item),
                    os.path.join(options.target_dir, item)
                )
            shutil.rmtree(temp_target_dir)
        return requirement_set

RInstallCommand()