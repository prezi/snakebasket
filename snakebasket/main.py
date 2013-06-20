import sys
from pip import main as pip_main

def main(*args, **kwargs):
    install_pip_patches()
    return pip_main(*args, **kwargs)

def install_pip_patches():
    from snakebasket.commands import install
    sys.modules['pip'].commands['install'] = install.RInstallCommand
    return
    import pip.vcs.git
    from patches import patched_git_get_src_requirement
    sys.modules['pip.vcs.git'].Git.get_src_requirement = patched_git_get_src_requirement