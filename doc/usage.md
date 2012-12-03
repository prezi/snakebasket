Snakebasket
---
Snakebasket is a backwards-compatible pip extension to pip. To install snakebasket, run:
`curl -ss -L http://href.prezi.com/snakebasket | bash -s`
Once snakebasket is installed, replace `pip` with `sb` in commands. For example, to install a new requirement, run:
`sb install X`

## Features
Snakebasket overrides the pip _install_ command, adding the following features:
* If an editable requirement includes a requirements.txt file in its root, this file is also processed (meaning the
  requirements within are also installed).
* An optional `--env` parameter may be passed to `sb install`, in which case the requirements list for that particular
  environment is used instead of the standard `requirements.txt`. For example, the command
  `sb install --env local git@github.com:prezi/sb-test-package.git#egg=sb-test-package` will install requirements from
  `requirements-local.txt` instead of `requirements.txt`. This is recursive, so if direct requirements have a
  `requirements-local.txt` of their own, that file will be processed. If no `requirements-local.txt` exists in the root
  of direct or indirect requirements, snakebasket will fall back to using `requirements.txt` if it exists.
* Conflicting version resolution. Standard pip does not allow two versions of the same requirement to appear in the
  project's `requirements.txt` file (or any file included within). This can become an issue when common components are
  used by several dependencies of an application, each using a different revision. For editable requirements stored in
  git repositories, snakebasket will check out the git repository, and find the newest version in case there are several
  candidates.

## Implementation
Snakebasket does change any files in the pip source distribution. Instead, the module for the `install` command is
patched to include the additional features. All standard pip unit tests pass with snakebasket. In addition tests have
been written for the new features.