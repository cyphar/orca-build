## `orca-build` ##

`orca-build` allows you to build OCI images from a `Dockerfile` or `Orcafile`. It
doesn't require a daemon or root privileges to operate. It is a fairly small
Python wrapper around the following projects (which are obviously requirements
to use `orca-build`):

* [`umoci`](https://github.com/openSUSE/umoci)
* [`runC`](https://github.com/opencontainers/runc)
* [`skopeo`](https://github.com/projectatomic/skopeo)

This was a [SUSE Hackweek project][hw] and is mainly intended to be a simple
tool for users that might want to create images as a rootless user, or to play
around with a simple PoC of how various OCI technologies can interact with each
other.

[hw]: https://hackweek.suse.com/15/projects/orca-build-oci-images-from-dockerfiles

### Usage ###

The usage is kinda like `docker build`. You provide it a build context that
contains a `Dockerfile` and `orca-build` does the rest. I plan to add support for
some more of the `docker build` flags in the near future, but at the moment it
works pretty well.

```
usage: orca-build [-h] [--clean] [--gc] [--output OUTPUT] [--verbose]
                  [--build-arg NAME=value] [-t TAGS]
                  ctx

Build an OCI image from a Dockerfile context. Rootless containers are also
supported out-of-the-box.

positional arguments:
  ctx                   Build context which is used when referencing host
                        files. Files outside the build context cannot be
                        accessed by the build script.

optional arguments:
  -h, --help            show this help message and exit
  --clean               Remove all intermediate image tags after successful
                        build.
  --gc                  Run a final garbage collection on output image.
  --output OUTPUT       Path of OCI image to output to (if unspecified, a new
                        image is created in /tmp).
  --verbose             Output debugging information.
  --build-arg NAME=value
                        Build-time arguments used in conjunction with ARG.
  -t TAGS, --tag TAGS   Tag(s) of the output image (by default, randomly
                        generated).
```

Here's an example session of building a standard `Dockerfile`:

```
% orca-build -t some-tag .
orca-build[INFO] BUILD[1 of 2]: from ['opensuse/amd64:42.2'] [json=False]
orca-build[INFO] Created new image for build: /tmp/orca-build.r2xp0v8h
  ---> [skopeo]
Getting image source signatures
Copying blob sha256:ed6542b73fb1330e3eee8294a805b9a231e30b3efa71390f938ce89f210db860
 47.09 MB / 47.09 MB [=========================================================]
Copying config sha256:56fae18e2688b7d7caf2dd39960f0e6fda4383c174926e2ee47128f29de066cf
 0 B / 805 B [-----------------------------------------------------------------]
Writing manifest to image destination
Storing signatures
  <--- [skopeo]
orca-build[INFO] BUILD[2 of 2]: run ['echo', 'Hello orca-build!', '&&', 'cat', '/etc/os-release'] [json=False]
  ---> [umoci]
  <--- [umoci]
  ---> [runc]
Hello orca-build!
NAME="openSUSE Leap"
VERSION="42.2"
ID=opensuse
ID_LIKE="suse"
VERSION_ID="42.2"
PRETTY_NAME="openSUSE Leap 42.2"
ANSI_COLOR="0;32"
CPE_NAME="cpe:/o:opensuse:leap:42.2"
BUG_REPORT_URL="https://bugs.opensuse.org"
HOME_URL="https://www.opensuse.org/"
  <--- [runc]
  ---> [umoci]
  <--- [umoci]
orca-build[INFO] BUILD: finished
  ---> [umoci]
  <--- [umoci]
orca-build[INFO] BUILD: created tags ['some-tag']
```

### Installation ###

I don't know how to do the whole "installation" thing with Python, so here's
how you install `orca-build`. It only depends on the standard library (and having the
above tools in your `$PATH`):

```
% sudo install -m0755 -D orca-build /usr/bin/orca-build
```

I've only tested it with Python 3.6, but it should work with most modern Python
3 versions.

### License ###

`orca-build` is licensed under the terms of the GPLv3 (or later).

```
orca-build: container image builder
Copyright (C) 2017 SUSE LLC

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
```
