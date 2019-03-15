#!env python
'''
Create a Qt Creator project file from a lego source/product.

You should do a "set_lego_product product_name" or "lego product_name" first,
build the project, then run this script.

It creates four files:

    <projectname>.creator       : The main project file
    <projectname>.creator.user  : User configuration, used for building and debugging
    <projectname>.files         : The list of files and folders in the project
    <projectname>.includes      : The list of folders used to look for include files

'''

import os
import os.path
import lxml.etree
import configparser
import re
import argparse
import sys
import subprocess
import qtcreator

class Options:
    value_regex = re.compile(r'\@(\S+)\((\S+)\)')

    def __init__(self, projectname):
        self.projectname = projectname
        self.environment_id = None
        self.profile_id = None
        self.lego_environment = {}
        self.__get_project_values()
        self.__get_lego_environment()
        self.projectrootdir = os.path.abspath(os.path.expanduser(self.lego_environment['LEGO_ROOT']))
        self.curdir = os.path.abspath(os.path.curdir)

    def __get_project_values(self):
        config = configparser.ConfigParser()
        config.read(os.path.expanduser('~/.config/QtProject/QtCreator.ini'))
        type_and_value = config['ProjectExplorer']['Settings\\EnvironmentId']
        found = Options.value_regex.findall(type_and_value)
        if len(found):
            self.environment_id = found[0][1]
        profiles = lxml.etree.parse(os.path.expanduser('~/.config/QtProject/qtcreator/profiles.xml'))
        found = profiles.xpath('//data[variable="Profile.0"]/valuemap//value[@key="PE.Profile.Id"]/text()')
        if len(found) == 1:
            self.profile_id = found[0]

    def __get_lego_environment(self):
        for key, value in os.environ.items():
            if key.startswith('LEGO_') or key == 'PATH':
                self.lego_environment[key] = value

    def get_lego_environment_list(self):
        return sorted(['{}={}'.format(key, value) for key, value in self.lego_environment.items()])


def create_project_content(options):
    filepath = os.path.abspath('{}.files'.format(options.projectname))
    with open(filepath, 'w') as out:
        cmd = '''find proprietary opensource thirdparty cust_* bs tools {LEGO_BS_OUTPUT_DIR}/include -type f '''.format(**options.lego_environment)
        filter_list = ['*.cpp', '*.h', '*.c', '*.py', '*.sh', '*.pl', '*.java', '*.js', '*.json', '*.xml', '*.patch', '*.cfg', '.config', '*.menu', '.gitignore', 'defconfig', 'Kconfig', 'Makefile', '*.mk', '*.top', '*.bottom']
        qtcreator.findfiles(cmd, filter_list, out)

        cmd = 'find . -maxdepth 1 '
        filter_list = ['lego*', 'Makefile', '.gitignore']
        qtcreator.findfiles(cmd, filter_list, out)

        cmd = 'find {LEGO_PRODUCTS}/base_root -type f'.format(**options.lego_environment)
        filter_list = []
        qtcreator.findfiles(cmd, filter_list, out)

        cmd = 'find {LEGO_PRODUCT_DIR} -type f'.format(**options.lego_environment)
        filter_list = []
        qtcreator.findfiles(cmd, filter_list, out)

        otherprod = '{}/{}'.format(options.lego_environment['LEGO_PRODUCTS'], options.lego_environment['LEGO_PRODUCT'].strip('_dev'))
        if os.path.exists(otherprod):
            cmd = 'find {} -type f '.format(otherprod)
            filter_list = []
            qtcreator.findfiles(cmd, filter_list, out)
        print('Created {}'.format(filepath))

    filepath = os.path.abspath('{}.includes'.format(options.projectname))
    with open(filepath, 'w') as out:
        cmd = 'find proprietary opensource thirdparty {LEGO_BS_OUTPUT_DIR}/include {LEGO_BS_OUTPUT_DIR}/thirdparty-include -type d'.format(**options.lego_environment)
        filter_list = []
        qtcreator.findfiles(cmd, filter_list, out)
        print('Created {}'.format(filepath))

    filepath = os.path.abspath('{}.creator'.format(options.projectname))
    with open(filepath, 'w') as out:
        out.write('[General]\n')
        print('Created {}'.format(filepath))


def create_lego_userfile(options):
    filepath = os.path.join(options.projectrootdir, '{}.creator.user'.format(options.projectname))
    uf = qtcreator.Userfile(filepath)
    executable = os.path.join(options.curdir.replace(options.lego_environment['LEGO_ROOT'], options.lego_environment['LEGO_BS_OUTPUT_DIR']), 'gtest')
    uf.set('EnvironmentId', options.environment_id)
    uf.set('ProjectId', options.profile_id)
    uf.set('MakeArguments', '-j 7 gtest_no_run')
    uf.set('BuildDirectory', options.curdir)
    uf.set('BuildEnvironment', options.get_lego_environment_list() + ['IGNORE_GLOBAL_DEPS=0'])
    uf.set('Executable', executable)
    uf.set('ExecutableDisplayName', 'Run ' + executable)
    uf.set('RunEnvironment', ['GTEST=-d', 'GTEST_FILTER=*.*'])
    uf.save()
    print('Created {}'.format(filepath))


def create_other_projects(options):
    cmd = '''find {LEGO_BS_OUTPUT_ROOT_DIR}/{LEGO_PRODUCT} -maxdepth 1 -type d -regex '\S+[0-9]' '''.format(**options.lego_environment)
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    dir_list = [ item for item in result.stdout.decode('utf-8').split('\n') if len(item) > 0 ]
    filelistname = '{}.files'.format(options.projectname)
    with open(filelistname, 'a') as out:
        for item in dir_list:
            cmd = 'find {} -type f '.format(item)
            filter_list = ['*.cpp', '*.h', '*.py', '*.c', '*.java', '*.js', '*.json', '*.pl', '*.htm*', 'makefile', '*.mk', '*.sh', '*.cfg', '.config', 'configure']
            qtcreator.findfiles(cmd, filter_list, out)
    print('Updated {}'.format(filelistname))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-o', action='store_true', default=False, help='Add project information for opensource projects (under output/<product>).')
    parser.add_argument('projectname', help='The name to be used for the project files')
    args = parser.parse_args()
    if len(args.projectname):
        if 'LEGO_PRODUCT' in os.environ:
            options = Options('{}_{}'.format(args.projectname, os.environ['LEGO_PRODUCT']))
            os.chdir(options.projectrootdir)
            create_project_content(options)
            create_lego_userfile(options)
            if args.o:
                create_other_projects(options)
        else:
            print('LEGO_PRODUCT is not set')
            print(__doc__)
            sys.exit(-1)

