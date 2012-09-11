import sys
from pip import version_control, load_command, command_dict
from snakebasket.commands.pip import install

sb_cmd_dict = {}

def help(args, options):
    print "help"

def main(args):
    install_pip_patches()
    init_pip()
    command, options, args = parse_args(args)
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
    load_command(cmd_name)
    commandfn = command_dict[cmd_name]
    return commandfn.main(args, options)

def install_pip_patches():
    sys.modules['pip.commands.install'] = install

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
    initial_args = sys.argv[1:]
    # No worrying about bash-completion now...
    # autocomplete()
    version_control()
