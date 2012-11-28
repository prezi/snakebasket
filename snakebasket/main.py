import sys
from pip import main as pip_main

def main(*args, **kwargs):
    #install_pip_patches()
    return pip_main(*args, **kwargs)

def install_pip_patches():
    from patches import patched_git_get_src_requirement
    from snakebasket.commands.pip import install
    from snakebasket.commands import release
    import pip.vcs.git
    sys.modules['pip.commands.install'] = install
    sys.modules['pip.commands.release'] = release
    sys.modules['pip.vcs.git'].Git.get_src_requirement = patched_git_get_src_requirement
