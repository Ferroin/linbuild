# linbuild #
linbuild is a Python script for automating Linux kernel builds.  It is
somewhat similar in nature to Gentoo's genkernel, but differs somewhat
in how it's designed to be used.

linbuild originated when I got tired of the dealing with the limitations
of the shell script I had been using to do essentially the same thing.
It started as a simple copy of the script itself rewritten in Python
with some extra configurability, and has evolved from there.

### Features ###
* Automatically runs the actual build in parallel with a reasonable
  number of CPU's (including properly honoring CPU affinity).
* Handling of independent build directories, including creation and setup
  of the build directory, and optionally even deletion after copying out
  the parts that you want.
* Let's the user manage their own config files.  By default, linbuild
  assumes that your build tree already has a config file in it that you
  created yourself.  It also gives the option to copy in an arbitrary file
  for configuration.  It specifically does not try to handle composing
  config files for you.
* Provides the ability to place the kernel image, modules, headers,
  and even arbitrary files from the build directory in a separate output
  directory.
* Allows direct installation of the kernel and modules to the local
  system, with the option to save backups of previous versions.
* Includes the ability to automatically generate and install an initramfs
  (requires dracut or initramfs-tools).
* When installing, has the option to create symlinks to the new kernel
  and initramfs (like Gentoo's genkernel tool can), simplifying boot
  loader configuration management.
* Supports automatically rebuilding out-of-tree kernel modules that are
  installed with either emerge or DKMS.  This uses `emerge --oneshot
  @module-rebuild` or `dkms autoinstall` respectively, and does not work
  with the output directory support.

### Dependencies ###
* Python >= 3.5
* Pyyaml >= 3.12 (may work with earlier versions, but is untested).
* Dracut or initramfs-tools (if you want to generate initramfs images).

### Usage ###
100% of configuration is done through a YAML config file which is passed
to linbuild as the only command line argument.  Complete documentation
for the config file can be found in `config.yml` in the distribution.

You can run individual steps of the build process by listing the name
of the step at the end of the command-line.  The steps are:
* **prepare**: Sets up the needed directories and copies in the kernel
  config.  After running this, you can run make from the build directory
  to do any thing you normally could from the kernel source directory.
* **build**: This actually builds the kernel.  It assumes that the build
  directory is already set up correctly.
* **generate-output**: This copies the build results to the output
  directory.
* **install**: This installs the kernel on the local system, optionally
  also installing modules.
* **initramfs**: This builds the initramfs.
* **cleanup**: This handles cleanup of the build directory and other
  temporary directories.

### License ###
linbuild is licensed under a 3-clause BSD license.  Check out the LICENSE
file for more info.

### TODO ###
* Add support for using 'kernel-install' instead of doing the install
  ourself.
* Add the ability to fetch and update the contents of srcdir from a
  tarball or git tree.
* Add support for other initramfs generation tools.
* Add the ability to copy arbitrary extra files (other than .config)
  into the build directory prior to the build (useful for external
  handling of module signing keys, etc).
* Possibly add some extra options for handling of build and output
  directory creation (BTRFS subvolumes, possibly others).
* Possibly add some extra logic to handle building of kernels with
  integrated initramfs.
* Make the out-of-tree module support work with the output directory
  support.
