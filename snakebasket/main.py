import sys
from pip import version_control, load_all_commands, command_dict

sb_cmd_dict = {}

def help(args, options):
    print "help"

def main(args):
    install_pip_patches()
    init_pip()
    command, args, options = parse_args(args)
    return run_command(command, args, options)

def run_command(command, args, options):
    if is_pip_command(command):
        return run_pip_command(command, args, options)
    elif sb_cmd_dict.has_key(command):
        return sb_cmd_dict[command](args, options)
    else:
        from pip.baseparser import parser
        parser.error('{0} is not a valid snakebasket command'.format(command))
        exit(1)

def is_pip_command(cmd):
    return command_dict.has_key(cmd)

def run_pip_command(cmd_name, args, options):
    commandfn = command_dict[cmd_name]
    return commandfn.main(args, options)

def install_pip_patches():
    from patches import patched_git_get_src_requirement
    from snakebasket.commands.pip import install
    from snakebasket.commands import release
    import pip.vcs.git
    sys.modules['pip.commands.install'] = install
    sys.modules['pip.commands.release'] = release
    sys.modules['pip.vcs.git'].Git.get_src_requirement = patched_git_get_src_requirement

def parse_args(args):
    from pip.baseparser import parser
    options, args = parser.parse_args(args)
    if options.help and not args:
        args = ['help']
    if not args:
        parser.error('You must give a commands (use "sb help" to see a list of commands)')
    command = args[0].lower()
    return (command, args[1:], options)


def init_pip():
    # No worrying about bash-completion now...
    # autocomplete()
    load_all_commands()
    version_control()
