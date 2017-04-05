#!/usr/bin/env python3
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

import os
import re
import shlex
import hashlib
import argparse
import tempfile
import subprocess

class attrdict(object):
	"Dumb implementation of attrdict."
	def __init__(self, *args, **kwargs):
		self.__dict__ = dict(*args, **kwargs)


def os_path_clean(orig_path):
	"""
	os_path_clean is a reimplementation of Go's path/filepath.Clean. This logic
	originally comes from Plan 9, and it returns a lexically identical path to
	the provided path (note that it might not agree with what you would get if
	you actually evaluted the filesystem).

	  >>> os_path_clean("abc")
	  'abc'
	  >>> os_path_clean("abc/def")
	  'abc/def'
	  >>> os_path_clean("a/b/c")
	  'a/b/c'
	  >>> os_path_clean(".")
	  '.'
	  >>> os_path_clean("..")
	  '..'
	  >>> os_path_clean("../..")
	  '../..'
	  >>> os_path_clean("../../abc")
	  '../../abc'
	  >>> os_path_clean("/abc")
	  '/abc'
	  >>> os_path_clean("/")
	  '/'
	  >>> os_path_clean("")
	  '.'
	  >>> os_path_clean("abc/")
	  'abc'
	  >>> os_path_clean("abc/def/")
	  'abc/def'
	  >>> os_path_clean("a/b/c/")
	  'a/b/c'
	  >>> os_path_clean("./")
	  '.'
	  >>> os_path_clean("../")
	  '..'
	  >>> os_path_clean("../../")
	  '../..'
	  >>> os_path_clean("/abc/")
	  '/abc'
	  >>> os_path_clean("abc//def//ghi")
	  'abc/def/ghi'
	  >>> os_path_clean("//abc")
	  '/abc'
	  >>> os_path_clean("///abc")
	  '/abc'
	  >>> os_path_clean("//abc//")
	  '/abc'
	  >>> os_path_clean("abc//")
	  'abc'
	  >>> os_path_clean("abc/./def")
	  'abc/def'
	  >>> os_path_clean("/./abc/def")
	  '/abc/def'
	  >>> os_path_clean("abc/.")
	  'abc'
	  >>> os_path_clean("abc/def/ghi/../jkl")
	  'abc/def/jkl'
	  >>> os_path_clean("abc/def/../ghi/../jkl")
	  'abc/jkl'
	  >>> os_path_clean("abc/def/..")
	  'abc'
	  >>> os_path_clean("abc/def/../..")
	  '.'
	  >>> os_path_clean("/abc/def/../..")
	  '/'
	  >>> os_path_clean("abc/def/../../..")
	  '..'
	  >>> os_path_clean("/abc/def/../../..")
	  '/'
	  >>> os_path_clean("abc/def/../../../ghi/jkl/../../../mno")
	  '../../mno'
	  >>> os_path_clean("/../abc")
	  '/abc'
	  >>> os_path_clean("abc/./../def")
	  'def'
	  >>> os_path_clean("abc//./../def")
	  'def'
	  >>> os_path_clean("abc/../../././../def")
	  '../../def'
	"""

	prev = None
	path = orig_path

	# We apply the same algorithm iteratively until it stops changing the input.
	while prev != path:
		parts = path.split(os.path.sep)

		# 1. Replace multiple Separator elements with a single one.
		parts = [part for part in parts if part != ""]

		# 2. Eliminate each . path name element (the current directory).
		parts = [part for part in parts if part != "."]

		# 3. Eliminate each inner .. path name element (the parent directory)
		#    along with the non-.. element that precedes it.
		new_parts = []
		for part in parts:
			if part != ".." or len(new_parts) == 0 or new_parts[-1] == "..":
				new_parts.append(part)
				continue
			new_parts = new_parts[:-1]
		parts = new_parts

		# 4. Eliminate .. elements that begin a rooted path;
		#    that is, replace "/.." by "/" at the beginning of a path,
		#    assuming Separator is '/'.
		if os.path.isabs(orig_path):
			while len(parts) > 0 and parts[0] == "..":
				parts = parts[1:]

		prev = path
		path = "."
		if parts:
			path = os.path.join(*parts)

	# The "multiple separator" code above silently converts absolute paths to
	# be relative to the root. So we have to fix that here.
	if os.path.isabs(orig_path):
		path = os.path.sep + path
	if path == "/.":
		path = "/"

	return path

def os_system(*args):
	"""
	Execute a command in the foreground, waiting until the command exits.
	Standard I/O is inherited from this process.
	"""
	print("[*]     --> Executing %s." % (args,))
	ret = subprocess.call(args, stdin=subprocess.DEVNULL)
	if ret != 0:
		print("[!]     --> %s failed with error code %d" % (args, ret))
		raise RuntimeError("%s failed with error code %d" % (args, ret))

def hash_digest(algo, contents):
	h = hashlib.new(algo)
	h.update(contents.encode("utf-8"))
	return h.hexdigest()


class DockerfileParser(object):
	"""
	DockerfileParser returns the parsed output
	"""

	def __init__(self, data):
		self.data = data

	def parse(self):
		# TODO: This is really dodgy at the moment (we should figure out how to
		#       parse JSON properly). First clean up the comments and line
		#       continuations and then split up the arguments and commands.
		self.data = re.sub(r"^#.*$", r"", self.data, flags=re.MULTILINE)
		self.data = re.sub(r"\\\n", r" ", self.data, flags=re.MULTILINE)

		# Split up the arguments and commands.
		steps = []
		for line in self.data.split('\n'):
			if not line.strip():
				continue

			cmd, args = line.split(" ", maxsplit=1)
			args = shlex.split(args)

			steps.append(attrdict({
				"cmd": cmd,
				"args": args,
			}))

		# Make sure there's at least one step.
		if len(steps) == 0:
			print("[-] Dockerfile contained no instructions.")
			raise ValueError("Dockerfile contained no instructions.")

		# The first step must be FROM.
		if steps[0].cmd.lower() != "from":
			print("[-] Dockerfiles must start with FROM.")
			raise ValueError("Dockerfiles must start with FROM.")

		# Return the steps.
		return steps


class Builder(object):
	"""
	Builder represents a builder instance.
	"""

	def safepath(self, path):
		"Returns a safe version of the given path."
		path = os_path_clean(path)
		path = os.path.join(self.root, path)
		path = os_path_clean(path)
		return path

	def __init__(self, root, script="Dockerfile"):
		self.root = root
		self.image_path = None
		self.our_tags = []
		self.source_tag = None
		self.destination_tag = None

		with open(self.safepath(script)) as f:
			contents = f.read()
			self.script = DockerfileParser(contents).parse()
			self.script_hash = hash_digest("sha256", contents) + "-dest"

		# TODO: Make these configurable and absolute paths.
		self.skopeo = "skopeo"
		self.umoci = "umoci"
		self.runc = "runc"

	def _dispatch_from(self, *args):
		if len(args) != 1:
			print("[*]     --> Invalid FROM format, can only have one argument -- FROM %r" % (args,))
		docker_source = "docker://%s" % (args[0],)

		if self.image_path is None:
			self.image_path = tempfile.mkdtemp(prefix="orca-build.")
			print("[+]     --> Created new image for build: %s" % (self.image_path,))

		if self.source_tag is None:
			self.source_tag = hash_digest("sha256", docker_source) + "-src"
			self.our_tags.append(self.source_tag)

		if self.destination_tag is None:
			self.destination_tag = hash_digest("sha256", self.script_hash)
			self.our_tags.append(self.destination_tag)

		if docker_source != "docker://scratch":
			# TODO: At the moment we only really support importing from a Docker
			#       registry. We need to extend the Dockerfile syntax to enable
			#       sourcing OCI images from the local filesystem.
			oci_destination = "oci:%s:%s" % (self.image_path, self.source_tag)
			os_system(self.skopeo, "copy", docker_source, oci_destination)
		else:
			os.rmdir(self.image_path)
			os_system(self.umoci, "init", "--layout="+self.image_path)
			os_system(self.umoci, "new", "--image=%s:%s" % (self.image_path, self.source_tag))

	def _dispatch_run(self, *args):
		print("[*]     --> TODO. NOT IMPLEMENTED.")

	def _dispatch_cmd(self, *args):
		# Decide whether we need to clear or change the cmd.
		if len(args) == 0:
			cmd_args = ["--clear=config.cmd"]
		else:
			cmd_args = ["--config.cmd="+arg for arg in args]

		# Update the configuration.
		oci_source = "%s:%s" % (self.image_path, self.source_tag)
		oci_dest = self.destination_tag
		os_system(self.umoci, "config", "--image="+oci_source, "--tag="+oci_dest, *cmd_args)

		# The destination has become the ma^H^Hsource.
		self.source_tag = self.destination_tag

	def _dispatch_label(self, *args):
		# Generate args.
		label_args = ["--config.label="+arg for arg in args]

		# Update the configuration.
		oci_source = "%s:%s" % (self.image_path, self.source_tag)
		oci_dest = self.destination_tag
		os_system(self.umoci, "config", "--image="+oci_source, "--tag="+oci_dest, *label_args)

		# The destination has become the ma^H^Hsource.
		self.source_tag = self.destination_tag

	def _dispatch_maintainer(self, *args):
		# Generate args.
		author = " ".join(args)
		maintainer_args = ["--author="+author, "--config.label=maintainer="+author]

		# Update the configuration.
		oci_source = "%s:%s" % (self.image_path, self.source_tag)
		oci_dest = self.destination_tag
		os_system(self.umoci, "config", "--image="+oci_source, "--tag="+oci_dest, *maintainer_args)

		# The destination has become the ma^H^Hsource.
		self.source_tag = self.destination_tag

	def _dispatch_expose(self, *args):
		# Generate args.
		# NOTE: There's no way AFAIK of clearing exposedports from a Dockerfile.
		expose_args = ["--config.exposedports="+arg for arg in args]

		# Update the configuration.
		oci_source = "%s:%s" % (self.image_path, self.source_tag)
		oci_dest = self.destination_tag
		os_system(self.umoci, "config", "--image="+oci_source, "--tag="+oci_dest, *expose_args)

		# The destination has become the ma^H^Hsource.
		self.source_tag = self.destination_tag

	def _dispatch_copy(self, *args):
		print("[*]     --> TODO. NOT IMPLEMENTED.")

	def _dispatch_add(self, *args):
		print("[!]     --> ADD implementation doesn't implement decompression, remote downloads or chown root:root at the moment.")
		return self._dispatch_copy(self, *args)

	def _dispatch_entrypoint(self, *args):
		# Decide whether we need to clear or change the entrypoint.
		if len(args) == 0:
			entrypoint_args = ["--clear=config.entrypoint"]
		else:
			entrypoint_args = ["--config.entrypoint="+arg for arg in args]

		# Update the configuration.
		oci_source = "%s:%s" % (self.image_path, self.source_tag)
		oci_dest = self.destination_tag
		os_system(self.umoci, "config", "--image="+oci_source, "--tag="+oci_dest, *entrypoint_args)

		# The destination has become the ma^H^Hsource.
		self.source_tag = self.destination_tag

	def _dispatch_volume(self, *args):
		# Generate args.
		# NOTE: There's no way AFAIK of clearing volumes from a Dockerfile.
		volume_args = ["--config.volume="+arg for arg in args]

		# Update the configuration.
		oci_source = "%s:%s" % (self.image_path, self.source_tag)
		oci_dest = self.destination_tag
		os_system(self.umoci, "config", "--image="+oci_source, "--tag="+oci_dest, *volume_args)

		# The destination has become the ma^H^Hsource.
		self.source_tag = self.destination_tag

	def _dispatch_user(self, *args):
		if len(args) != 1:
			print("[*]     --> Invalid USER format, can only have one argument -- USER %r" % (args,))
			raise RuntimeError("Invalid USER format, can only have one argument -- USER %r" % (args,))

		# Generate args.
		user_args = ["--config.user="+args[0]]

		# Update the configuration.
		oci_source = "%s:%s" % (self.image_path, self.source_tag)
		oci_dest = self.destination_tag
		os_system(self.umoci, "config", "--image="+oci_source, "--tag="+oci_dest, *user_args)

		# The destination has become the ma^H^Hsource.
		self.source_tag = self.destination_tag

	def _dispatch_workdir(self, *args):
		if len(args) != 1:
			print("[*]     --> Invalid WORKDIR format, can only have one argument -- WORKDIR %r" % (args,))
			raise RuntimeError("Invalid WORKDIR format, can only have one argument -- WORKDIR %r" % (args,))

		# Generate args.
		workdir_args = ["--config.workdir="+args[0]]

		# Update the configuration.
		oci_source = "%s:%s" % (self.image_path, self.source_tag)
		oci_dest = self.destination_tag
		os_system(self.umoci, "config", "--image="+oci_source, "--tag="+oci_dest, *workdir_args)

		# The destination has become the ma^H^Hsource.
		self.source_tag = self.destination_tag

	def _dispatch_env(self, *args):
		print("[*]     --> TODO. NOT IMPLEMENTED.")

	def _dispatch_arg(self, *args):
		print("[*]     --> TODO. NOT IMPLEMENTED.")

	def _dispatch_stopsignal(self, *args):
		print("[*]     --> TODO. NOT IMPLEMENTED. REQUIRES NEWER OCI IMAGESPEC SUPPORT.")

	def _dispatch_onbuild(self, *args):
		print("[-]     --> ONBUILD is not supported by OCI.")

	def _dispatch_shell(self, *args):
		print("[-]     --> SHELL is not supported by OCI.")

	def _dispatch_healthcheck(self, *args):
		print("[-]     --> HEALTHCHECK is not supported by OCI.")

	def build(self):
		for step in self.script:
			cmd = step.cmd.lower()
			args = step.args

			print("[+] Build step: %s %r" % (cmd, args))

			# Dispatch to method.
			fn = "_dispatch_%s" % (cmd,)
			if hasattr(self, fn):
				getattr(self, fn)(*args)
			else:
				print("[-] unknown build command %s" % (cmd,))
				raise RuntimeError("unknown build command %s" % (cmd,))

		print("[+] Build finished.")


def main(ctx, config):
	if not os.path.exists(ctx):
		print("[-] Context %s doesn't exist." % (ctx,))

	builder = Builder(ctx)
	builder.build()

if __name__ == "__main__":
	def __wrapped_main__():
		parser = argparse.ArgumentParser(description="Build an OCI image from a Dockerfile context. Rootless containers are also supported out-of-the-box.")
		parser.add_argument("ctx", nargs=1, help="Build context which is used when referencing host files. Files outside the build context cannot be accessed by the build script.")

		config = parser.parse_args()
		ctx = config.ctx[0]

		main(ctx, config)

	__wrapped_main__()
