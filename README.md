Snakebasket
===============

snakebasket is a layer on top of [pip](https://github.com/pypa/pip) which makes multi-package python development a little easier:

snakebasket does two things:

1. Recursively reads requirements from simple `requirements.txt` or old-school `setup.ph` files during `sb install`.

2. Chooses and installs the latest depedency versions, in the case of conflicting requirements.

Installation
---
Within your [virtualenv](https://pypi.python.org/pypi/virtualenv) of choice, run:
`curl -ss -L http://href.prezi.com/snakebasket | bash -s`

Development
---
Because snakebasket includes a particular [pip](https://github.com/pypa/pip) commit as a sub-repo, use
```bash
$ git clone --recursive git@github.com:prezi/snakebasket.git 
```
to clone both snakebasket and the pip sub-repo completely.

##Testing

To run snakebasket tests, you must first create a virtualenv
and add the necessary testing packages:
```bash
$ virtualenv --distribute --no-site-packages -p python2.6 sb-venv
$ . sb-venv/bin/activate
(sb-venv)$ pip install -r requirements-development.txt 
```
To run tests, make sure the virtualenv is active, then execute the
following from the project root:
```bash
(sb-venv)$ cd tests/
(sb-venv)$ python runtests.py
```
Warnings about certificates are expected, pay them no attention:
```
warning: bitbucket.org certificate with fingerprint 24:9c:45:8b:9c:aa:ba:55:4e:01:6d:58:ff:e4:28:7d:2a:14:ae:3b not verified (check hostfingerprints or web.cacerts config setting)
```

### Detailed Description
In the Python world, pip is a popular tool for installing packages and dependencies:

`$ pip install Django`

or, if you have a list of dependencies:

`$ pip install -r packages_we_need.txt`

pip works great for basic applications with few dependencies and a flat structure (packages that don't depend on other packages which then depend on other packages), but when you try and use pip for an application like this:

![dependency hell](https://github.com/prezi/snakebasket/wiki/dependency_hell.jpg)

pip chokes. And that's where snakebasket comes in.

snakebasket does two big things that help make up for pip's shortcomings: 

**1. Installs recursive dependencies.**

With pip, every desired package needs to be manually `pip install`ed.

snakebasket `sb install`s (via `pip install`) a list of dependencies from the desired package's `requirements.txt` file—and then it installs further packages from the `requirements.txt` file of every subsequent dependency, recursively.

**2. Decides between conflicting versions of the same package.**

pip allows exactly one version of a package to be specified in a given environment, and thus expects all packages to depend on that same single version. In this example:

```python
#foo/setup.py
setup(
    name="foo",
    ...
    packages["ReportLab=1.7"]
)
```

```python
#bar/setup.py
setup(
    name="bar",
    ...
    packages["ReportLab=0.9"]
)
```

where foo.py and bar.py are installed in the same environment, pip would break as it only allows one of the versions to exist at a given time, and it has no mechanism to properly decide which to install.

Thus, to use pip by itself is to have to manually keep all versions in sync across an environment. In complex applications with many contributors, this doesn't scale well.

In the above situation, snakebasket picks the latest version, and then it `sb install`s that decision.

You can specify package dependencies in a few ways (including via setup.py above), but the recommended way is to specify the requirements in a simple `requirements.txt` (or `requirements-$POSTFIX.txt`) from which snakebasket automatically reads:

```
#foo/requirements.txt
ReportLab=1.7
```

```
#bar/requirements.txt
ReportLab=0.9
```

Explicit versions are always recommended. Regardless of where it is in the hierarchy, the latest specified version of any dependency is the one that will ultimately be installed. If an explicit version is not specified, snakebasket interprets that to mean the latest available version.

The only situation where the non-latest version could be installed is where one depedency version is implict (not pinned), another (earlier) dependency version is explicit, and the install command is `sb install --prefer-pinned-revision`.

Of course, all of this *makes a huge assumption on the backwards compatibility of dependencies*. snakebasket currently relies on this assumption.