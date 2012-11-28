from __future__ import absolute_import
from pip.basecommand import Command
from pip.exceptions import CommandError
import os
from pip.log import logger
from pip.util import find_command, call_subprocess

class ReleaseCommand(Command):
    name = 'release'
    usage = '%prog [major|minor|implementation]'
    summary = 'Create a release'
    bundle = False

    RELEASE_TYPES = ['major', 'minor', 'implementation']

    def __init__(self):
        super(ReleaseCommand, self).__init__()
        self.cmd = find_command('git')
        #TODO: options

    def _filter(self, line):
        return (logger.INFO, line)

    def gitcmd(self, args):
        full_cmd = [self.cmd]

    def run(self, options, args):
        print call_subprocess(
            [self.cmd, 'status'],
            filter_stdout=self._filter, show_stdout=False, cwd=os.path.curdir)

        if len(args) != 1 or args[0] not in ReleaseCommand.RELEASE_TYPES:
            raise CommandError("Must specify the type of release, which is one of " + ",".join(ReleaseCommand.RELEASE_TYPES))
        logger.notify('Starting a {} release.'.format(args[0]))


ReleaseCommand()