## `orca` ##

`orca` allows you to build OCI images from a `Dockerfile` or `Orcafile`. It
doesn't require a daemon or root privileges to operate. It is a fairly small
Python wrapper around the following projects (which are obviously requirements
to use `orca`):

* [`umoci`](https://github.com/openSUSE/umoci)
* [`runC`](https://github.com/opencontainers/runc)
* [`skopeo`](https://github.com/projectatomic/skopeo)
