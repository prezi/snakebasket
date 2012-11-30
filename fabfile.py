import os.path
from fabric.api import local, env
from fabric.utils import fastprint
from prezi.fabric.s3 import CommonTasks, S3Deploy, NoopServiceManager

env.forward_agent = True
env.user = 'publisher'
env.roledefs = {'production': [], 'stage': [], 'local': []}



class SingleVirtualenvS3Deploy(S3Deploy):
    def __init__(self, app_name, buckets, revno):
        super(SingleVirtualenvS3Deploy, self).__init__(app_name, buckets, revno)
        self.service = NoopServiceManager(self)
        self.virtualenv = SingleVirtualenvService(self)


class SingleVirtualenvService(object):
    def __init__(self, deployer):
        self.deployer = deployer
        self.tarball_path = self.deployer.build_dir + '.tar'
        self.tarbz_path = self.tarball_path + '.bz2'
        self.tarbz_name = os.path.basename(self.tarbz_path)

    def build_tarbz(self):
        self.build_venv()
        self.compress_venv()

    def cleanup(self):
        local('rm -rf %s %s' % (self.tarbz_path, self.deployer.build_dir))

    def build_venv(self):
        fastprint('Building single virtualenv service in %s\n' % self.deployer.build_dir)
        # init + update pip submodule
        local('git submodule init; git submodule update')
        # builds venv
        self.run_virtualenv_cmd("--distribute --no-site-packages -p python2.7 %s" % self.deployer.build_dir)
        # installs app + dependencies
        local(' && '.join(
            ['. %s/bin/activate' % self.deployer.build_dir,
             'pip install --exists-action=s -e `pwd`/pip#egg=pip -e `pwd`@master#egg=snakebasket -r requirements-development.txt']
        ))
        # makes venv relocatable
        self.run_virtualenv_cmd("--relocatable -p python2.7 %s" % self.deployer.build_dir)

    def compress_venv(self):
        fastprint('Compressing virtualenv')
        local('tar -C %(build_dir)s/.. -cjf %(tarbz_path)s %(dirname)s' % {
            'build_dir': self.deployer.build_dir,
            'tarbz_path': self.tarbz_path,
            'dirname': os.path.basename(self.deployer.build_dir)
        })

    def run_virtualenv_cmd(self, args):
        if not isinstance(args, list):
            args = args.split()
        fastprint('Running virtualenv with args %s\n' % args)
        local("env VERSIONER_PYTHON_VERSION='' virtualenv %s" % ' '.join(args))

    @property
    def upload_source(self):
        return self.tarbz_path

    @property
    def upload_target(self):
        return self.tarbz_name


tasks = CommonTasks(SingleVirtualenvS3Deploy, 'snakebasket', None)
snakebasket_build = tasks.build
cleanup = tasks.cleanup
