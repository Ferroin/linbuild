# linbuild #
linbuild is a Python script for automating Linux kernel builds.  It is
somewhat similar in nature to Gentoo's genkernel, but differs somewhat
in how it's designed to be used.

### Features ###
* Automatically runs the actual build in parallel with a reasonable
  number of CPU's (it uses the number of CPU's it's allowed to run on
  based on sched\_getaffinity() by default).
* Handling of independent build directories, including creation and setup
  of the build directory, and optionally even deletion afteer copying out
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

### Dependencies ###
* Python >= 3.5
* Pyyaml >= 3.12 (may work with earlier versions, but is untested).
* Dracut or initramfs-tools (if you want to generate initramfs images).

### Usage ###
100% of configuration is done through a YAML config file which is passed
to linbuild as the only command line argument.  Complete documentation
for the config file can be found in `config.yml` in the distribution.

### License ###
linbuild is licensed under a 3-clause BSD license.  Check out the LICENSE
file for more info.

### TODO ###
* Add support for using 'kernel-install' instead of doing the install
  ourself.
* Add support for other initramfs generation tools.
* Add the ability to copy arbitrary extra files (other than .config)
  into the build directory prior to the build (useful for external
  handling of module signing keys, etc).
* Possibly add some extra options for handling of build and output
  directory creation (BTRFS subvolumes, possibly others).
* Possibly add some extra logic to handle building of kernels with
  integrated initramfs.
