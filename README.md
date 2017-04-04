## `orca` ##

`orca` allows you to build OCI images from a `Dockerfile` or `Orcafile`. It
doesn't require a daemon or root privileges to operate. It is a fairly small
Python wrapper around the following projects (which are obviously requirements
to use `orca`):

* [`umoci`](https://github.com/openSUSE/umoci)
* [`runC`](https://github.com/opencontainers/runc)
* [`skopeo`](https://github.com/projectatomic/skopeo)

### License ###

`orca` is licensed under the terms of the GPLv3 (or later).

```
orca: container image builder
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
