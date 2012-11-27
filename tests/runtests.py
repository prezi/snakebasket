import os
import sys
import xmlrpclib
from pkg_resources import load_entry_point
import nose.tools
import unittest.case

def add_dir_to_pythonpath(d):
    sys.path.insert(0, d)

add_dir_to_pythonpath(os.path.join(os.path.dirname(__file__), 'pip'))
# remove site-packages pip from python path and sys.modules
import re
mre = re.compile(".*pip.*")
sys.modules = dict((k,v) for k,v in sys.modules.iteritems() if re.match(mre, k) is None)
dre = re.compile(".*site-packages/pip-.*")
sys.path = [d for d in sys.path if re.match(dre, d) is None]

# patch assert_raises to allow always be true
def patched_assert_raises_context_exit(self, exc_type, exc_value, tb):
    if exc_type is None:
        try:
            exc_name = self.expected.__name__
        except AttributeError:
            exc_name = str(self.expected)
        raise self.failureException(
            "{0} not raised".format(exc_name))
    if not (issubclass(exc_type, self.expected) or (exc_value is not None and exc_value.__class__.__name__ == self.expected.__name__)):
        # let unexpected exceptions pass through
        return False
    self.exception = exc_value # store for later retrieval
    if self.expected_regexp is None:
        return True

    expected_regexp = self.expected_regexp
    if isinstance(expected_regexp, basestring):
        expected_regexp = re.compile(expected_regexp)
    if not expected_regexp.search(str(exc_value)):
        raise self.failureException('"%s" does not match "%s"' %
                 (expected_regexp.pattern, str(exc_value)))
    return True
sys.modules['unittest.case']._AssertRaisesContext.__exit__ = patched_assert_raises_context_exit

if __name__ == '__main__':
    sys.exit(
        load_entry_point('nose==1.2.1', 'console_scripts', 'nosetests')()
    )
