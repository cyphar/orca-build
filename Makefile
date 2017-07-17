# Copyright (C) 2017 SUSE LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

.DEFAULT: orca-build

PREFIX ?= /usr
BINDIR ?= $(PREFIX)/bin

.PHONY: orca-build
orca-build:
	@echo ' +---------------------------------------------------------------------+'
	@echo ' | orca-build is a single-file Python 3 script with no dependencies,   |'
	@echo ' | so there is no build step or setup.py to deal with. If you want to  |'
	@echo ' | install orca-build, you can use "make install" or just copy the     |'
	@echo ' | script to your PATH.                                                |'
	@echo ' +---------------------------------------------------------------------+'

.PHONY: install
install:
	install -D -m0755 orca-build $(BINDIR)/orca-build

.PHONY: uninstall
uninstall:
	rm -f $(BINDIR)/orca-build

# TODO: Add a test suite.
.PHONY: test
test:

# Make sure that the current umoci, skopeo, and runc installs work together,
# and that rootless containers operate correctly. If this fails, then you'll
# need to make sure you have compatible versions of all three tools.
.PHONY: check
check:
	[ ! -e .tmp-check ] || ( chmod -Rf 777 .tmp-check && rm -rf .tmp-check ) ; mkdir -p .tmp-check
	skopeo copy docker://alpine oci:.tmp-check/alpine:latest
	umoci config --config.cmd={echo,Hello,world.} --image .tmp-check/alpine:latest
	umoci unpack --rootless --image .tmp-check/alpine:latest .tmp-check/bundle
	runc --root .tmp-check/runc-root run -b .tmp-check/bundle ctr
	[ ! -e .tmp-check ] || ( chmod -Rf 777 .tmp-check && rm -rf .tmp-check )
