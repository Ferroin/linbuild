#!/usr/bin/env python3
'''linbuild.py: A script to automate Linux kernel builds.

   Usage:
   linbuild.py <config-file>

   Copyright (c) 2017, Austin S. Hemmelgarn
   All rights reserved.

   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.
   2. Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
   3. Neither the name of linbuild nor the names of its contributors may be
      used to endorse or promote products derived from this software without
      specific prior written permission.

   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
   AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
   IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
   ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
   LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
   CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
   SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
   INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
   CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
   ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
   POSSIBILITY OF SUCH DAMAGE.'''

import logging
import os
import shutil
import subprocess
import sys
import yaml

_INITRD_GEN_TYPES = [
    'dracut',
    'mkinitramfs'
]

def get_config(path):
    '''Load the configuration.

       This also generates the in-memory-only 'internal' section (used for
       some computed values) and ensures that required keys are present
       (pre-loading with defaults if possible).'''
    with open(path) as conf:
        config = yaml.safe_load(conf)
    config['internal'] = dict()
    if 'splitbuild' in config.keys() and config['splitbuild']:
        if 'builddir' in config.keys():
            config['internal']['targetdir'] = config['builddir']
        else:
            config['internal']['targetdir'] = os.getcwd()
    else:
        config['internal']['targetdir'] = config['srcdir']
    if not 'srcdir' in config.keys():
        logging.error('The config must specify a source directory.')
        return False
    else:
        if not os.access(config['srcdir'], os.R_OK | os.X_OK, effective_ids=True):
            logging.error('Cannot access kernel sources at %s.', config['srcdir'])
            return False
    if not 'image-type' in config.keys():
        config['image-type'] = 'bzImage'
    if 'output' in config.keys():
        if not 'directory' in config['output'].keys():
            logging.error('The \'output\' section must have a \'directory\' key.')
            return False
        if not 'image-prefix' in config['output'].keys():
            config['output']['image-prefix'] = 'kernel'
        if not 'clean' in config['output'].keys():
            config['output']['clean'] = False
    if 'install' in config.keys():
        if not 'boot' in config['install'].keys():
            config['install']['boot'] = '/boot'
        if not 'symlink' in config['install'].keys():
            config['install']['symlink'] = True
        if not 'keep-old' in config['install'].keys():
            config['install']['keep-old'] = True
        if not 'modules' in config['install'].keys():
            config['install']['modules'] = True
        if not 'image-prefix' in config['install'].keys():
            config['install']['image-prefix'] = 'kernel'
        if 'initrd-gen' in config['install'].keys() and config['install']['initrd-gen'] not in _INITRD_GEN_TYPES:
            logging.error('The \'%s\' initrd generator is not supported.', config['install']['initrd-gen'])
            return False
        if 'initrd-gen' in config['install'].keys() and not config['install']['modules']:
            logging.error('Generating an initramfs requires the kernel modules to be installed.')
            return False
    if not 'make' in config.keys():
        config['make'] = dict()
    if not 'command' in config['make'].keys():
        config['make']['command'] = 'make'
    if not 'jobs' in config['make'].keys():
        config['make']['jobs'] = len(os.sched_getaffinity(0))
    if not 'verbose' in config.keys():
        config['verbose'] = False
    if not 'clean' in config.keys():
        config['clean'] = False
    if not 'postclean' in config.keys():
        config['postclean'] = False
    if not 'postnuke' in config.keys():
        config['postnuke'] = False
    if not 'tmpdir' in config.keys9):
        if 'TMPDIR' in os.environ:
            config['tmpdir'] = os.environ['TMPDIR']
        else:
            config['tmpdir'] = '/tmp'
    os.environ['TMPDIR'] = config['tmpdir']
    return config

def call(command, verbose):
    '''Call a command and provide proper error handling.'''
    try:
        if verbose:
            subprocess.run(command, shell=True, check=True, stdout=sys.stdout, stderr=subprocess.STDOUT)
        else:
            subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as err:
        logging.error('Command \'%s\' failed, returned %s', command, str(err.returncode))
        try:
            logging.error('Full content of stderr:\n%s', err.stderr)
        except AttributeError:
            pass
        raise err
    return True

def copy(src, dest, keep_old=False):
    '''Copy src to dest, optionally creating a backup if dest already exists.'''
    if keep_old and os.access(dest, os.F_OK):
        os.unlink(dest + '.old')
        shutil.copy2(dest, dest + '.old')
    shutil.copy2(src, dest + '.tmp')
    return os.replace(dest + '.tmp', dest)

def link(src, dest, keep_old=True):
    '''Create a symlink at dest pointing to src.'''
    if keep_old and os.access(dest, os.F_OK, follow_symlinks=False):
        if os.path.islink(dest):
            target = os.readlink(dest)
            os.unlink(dest + '.old')
            os.symlink(target, dest + '.old')
        else:
            os.unlink(dest + '.old')
            shutil.copy2(dest, dest + '.old')
    os.unlink(dest)
    return os.symlink(src, dest)

def run_sequence(seq, args):
    '''Run a sequence of callables with a given set of arguments.

       This bails at the first itme to return False.

       seq is an iterable of callables.
       args is an iterable of arguments, all of which are passed to
            each callable.'''
    for item in seq:
        if not item(*args):
            return False
    return True

def clean(config):
    '''Clean the target directory.'''
    command = config['make']['command']
    command += ' -C {0} clean'.format(config['internal']['targetdir'])
    return call(command, config['verbose'])

def get_kernel_version(config):
    '''Return the kernel version string.

      This is it's own function because we need to read the output
      ourselves and it shouldn't go to stdout regardless of whether
      config['verbose'] is True or not.'''
    command = config['make']['command']
    command += ' -C {0} kernelrelease'.format(config['internal']['targetdir'])
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
    except subprocess.CalledProcessError as err:
        logging.error('Failed to determine kernel version.')
        raise err
    result = result.splitlines()
    return result[-2].decode()

def get_kernel_image(config):
    '''Return the path to the kernel image.'''
    from glob import glob
    image = glob(os.path.join(config['internal']['targetdir'], 'arch/*/boot', config['image-type']))
    if len(image) == 0:
        logging.error('Unable to find kernel image.')
        return False
    return image[0]

def prepare(config):
    '''Prepare the build location.

       This sets up the build directory, prepares the final output
       directory (if one is to be used), copies in the configuration,
       etc.'''
    try:
        os.makedirs(config['internal']['targetdir'], exist_ok=True)
    except OSError as err:
        logging.error('Build directory does not exist and we can not create it.')
        raise err
    if not os.access(config['internal']['targetdir'], os.R_OK | os.W_OK | os.X_OK, effective_ids=True):
        logging.error('Unable to access build directory.')
        return False
    if 'config' in config.keys():
        logging.info('Copying configuration from %s.', config['config'])
        try:
            copy(config['config'], os.path.join(config['internal']['targetdir'], '.config'))
        except (OSError, IOError) as err:
            logging.error('Unable to copy configuration to build directory.')
            raise err
    command = config['make']['command']
    command += ' -C {0}'.format(config['srcdir'])
    command += ' {0} silentoldconfig'.format(config['make']['opts'])
    if config['internal']['targetdir'] != config['srcdir']:
        command += ' O={0}'.format(config['internal']['targetdir'])
    logging.info('Initializing build directory.')
    call(command, config['verbose'])
    if config['clean']:
        logging.info('Cleaning build directory.')
        clean(config)
    return True

def build(config):
    '''Actually compile the kernel.'''
    command = config['make']['command']
    command += ' -j{0}'.format(config['make']['jobs'])
    command += ' -C {0}'.format(config['internal']['targetdir'])
    command += ' {0}'.format(config['make']['opts'])
    logging.info('Building kernel and modules.')
    return call(command, config['verbose'])

def gen_output(config):
    '''Prepare the output directory.'''
    version = get_kernel_version(config)
    image = get_kernel_image(config)
    outpath = os.path.join(config['output']['directory'], version)
    try:
        os.makedirs(outpath, exist_ok=True)
    except OSError as err:
        logging.error('Unable to create output directory.')
        raise err
    if not os.access(outpath, os.R_OK | os.W_OK | os.X_OK, effective_ids=True):
        logging.error('Unable to access output directory.')
        return False
    if not (image and version):
        return False
    logging.info('Copying kernel image to output directory.')
    try:
        copy(image, os.path.join(outpath, '{0}-{1}'.format(config['output']['image-prefix'], version)))
    except (OSError, IOError) as err:
        logging.error('Unable to copy kernel image to output directory.')
        raise err
    if 'modules' in config['output'].keys() and config['output']['modules']:
        logging.info('Copying modules to output directory.')
        modpath = os.path.join(outpath, 'lib', 'modules', version)
        command = config['make']['command']
        command += ' -j{0}'.format(config['make']['jobs'])
        command += ' -C {0}'.format(config['internal']['targetdir'])
        command += ' modules_install INSTALL_MOD_PATH={0}'.format(outpath)
        try:
            shutil.rmtree(modpath + '.old')
            os.rename(modpath, modpath + '.old')
        except (OSError, IOError):
            pass
        call(command, config['verbose'])
    if 'headers' in config['output'].keys() and config['output']['headers']:
        logging.info('Copying headers to output directory')
        command = config['make']['command']
        command += ' -j{0}'.format(config['make']['jobs'])
        command += ' -C {0}'.format(config['internal']['targetdir'])
        command += ' headers_install INSTALL_HDR_PATH={0}'.format(outpath)
        call(command, config['verbose'])
    return True

def install(config):
    '''Install the kernel.'''
    version = get_kernel_version(config)
    image = get_kernel_image(config)
    if not (image and version):
        return False
    imagedest = os.path.join(config['install']['bootdir'], '{0}-{1}'.format(config['install']['image-prefix'], version))
    linkdest = os.path.join(config['install']['bootdir'], config['install']['image-prefix'])
    logging.info('Installing kernel image.')
    try:
        copy(image, imagedest, config['install']['keep-old'])
    except (OSError, IOError) as err:
        logging.error('Unable to install kernel image.')
        raise err
    if config['install']['symlink']:
        try:
            link(imagedest, linkdest, config['install']['keep-old'])
        except (OSError, IOError) as err:
            logging.error('Unable to create symbolic link pointing to new kernel.')
            raise err
    if config['install']['modules']:
        logging.info('Installing modules.')
        modpath = os.path.join(' ', 'lib', 'modules', version).lstrip()
        command = config['make']['command']
        command += ' -j{0}'.format(config['make']['jobs'])
        command += ' -C {0}'.format(config['internal']['targetdir'])
        command += ' modules_install'
        try:
            shutil.rmtree(modpath + '.old')
            os.rename(modpath, modpath + '.old')
        except (OSError, IOError):
            pass
        call(command, config['verbose'])
    return True

def install_initrd(config):
    '''Install the initramfs.'''
    from tempfile import mkstemp
    tmpfile = mkstemp(prefix='linbuild', dir=config['tmpdir'])
    os.close(tmpfile[0])
    tmpfile = tmpfile[1]
    version = get_kernel_version(config)
    if config['install']['initrd-gen'] == 'dracut':
        logging.info('Generating initramfs using dracut.')
        command = 'dracut --force '
        command += config['install']['initrd-opts']
        command += ' {0}'.format(tmpfile)
        command += ' {0}'.format(version)
    elif config['install']['initrd-gen'] == 'mkinitramfs':
        logging.info('Generating initramfs using mkinitramfs.')
        command = 'mkinitramfs '
        command += config['install']['initrd-opts']
        command += ' -o {0}'.format(tmpfile)
        command += ' {0}'.format(version)
    call(command, config['verbose'])
    logging.info('Installing initramfs.')
    initrddest = os.path.join(config['install']['bootdir'], '{0}-{1}'.format(config['install']['initrd-prefix'], version))
    linkdest = os.path.join(config['install']['bootdir'], config['install']['initrd-prefix'])
    try:
        copy(tmpfile, initrddest, keep_old=True)
    except (OSError, IOError) as err:
        logging.error('Unable to install initramfs.')
        raise err
    if config['install']['symlink']:
        try:
            link(initrddest, linkdest, config['install']['keep-old'])
        except (OSError, IOError) as err:
            logging.error('Unable to create symbolic link pointing to new initramfs.')
            raise err
    os.unlink(tmpfile)
    return True

def final_cleanup(config):
    '''Perform any final cleanup.'''
    if 'postclean' in config.keys() and config['postclean']:
        if 'postnuke' in config.keys() and config['postnuke'] and 'builddir' in config.keys() and 'splitbuild' in config.keys():
            logging.info('Removing build directory.')
            try:
                shutil.rmtree(config['internal']['targetdir'])
            except (OSError, IOError):
                logging.warning('Unable to delete build directory.')
        else:
            try:
                clean(config)
            except subprocess.CalledProcessError:
                logging.warning('Cleaning build directory failed.')
    return True

def main():
    '''Main program logic.'''
    config = get_config(sys.argv[1])
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    if not config:
        return 2
    sequence = list()
    sequence.append(prepare)
    sequence.append(build)
    if 'output' in config.keys():
        sequence.append(gen_output)
    if 'install'in config.keys():
        sequence.append(install)
        if 'initrd-gen' in config['install'].keys():
            sequence.append(install_initrd)
    sequence.append(final_cleanup)
    status = run_sequence(sequence, [config])
    if not status:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
