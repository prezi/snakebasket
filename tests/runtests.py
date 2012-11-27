import os
import sys
import xmlrpclib
from pkg_resources import load_entry_point

def add_dir_to_pythonpath(d):
    sys.path.insert(0, d)

add_dir_to_pythonpath(os.path.join(os.path.dirname(__file__), 'pip'))
# remove site-packages pip from python path and sys.modules
import re
mre = re.compile(".*pip.*")
sys.modules = dict((k,v) for k,v in sys.modules.iteritems() if re.match(mre, k) is None)
dre = re.compile(".*site-packages/pip-.*")
sys.path = [d for d in sys.path if re.match(dre, d) is None]


if __name__ == '__main__':
    sys.exit(
        load_entry_point('nose==1.2.1', 'console_scripts', 'nosetests')()
    )
