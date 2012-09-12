from __future__ import absolute_import
from pip.basecommand import Command
from pip.exceptions import CommandError
import os
import tempfile
from pip.log import logger

class ReleaseCommand(Command):
    name = 'release'
    usage = '%prog [major|minor|implementation]'
    summary = 'Create a release'
    bundle = False

    RELEASE_TYPES = ['major', 'minor', 'implementation']

    def __init__(self):
        super(ReleaseCommand, self).__init__()
        #TODO: options

    def run(self, options, args):
        if len(args) != 1 or args[0] not in ReleaseCommand.RELEASE_TYPES:
            raise CommandError("Must specify the type of release, which is one of " + ",".join(ReleaseCommand.RELEASE_TYPES))
        logger.notify('Starting a {} release.'.format(args[0]))


ReleaseCommand()