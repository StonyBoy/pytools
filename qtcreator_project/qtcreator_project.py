#!env python
'''
Create a Qt Creator project file from a source folder

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
import qtcreator

class Options:
    value_regex = re.compile(r'\@(\S+)\((\S+)\)')

    def __init__(self, projectname, sourcefolder, projectfolder):
        self.projectname = projectname
        self.environment_id = None
        self.profile_id = None
        self.__get_project_values()
        self.sourcedir = os.path.abspath(os.path.expanduser(sourcefolder))
        self.projectrootdir = os.path.abspath(os.path.expanduser(projectfolder))
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


def create_project_content(options):
    filepath = os.path.abspath('{}.files'.format(options.projectname))
    with open(filepath, 'w') as out:
        cmd = '''find {} -type f '''.format(options.sourcedir)
        filter_list = qtcreator.get_common_filter()
        qtcreator.findfiles(cmd, filter_list, out)
        print('Created {}'.format(filepath))

    filepath = os.path.abspath('{}.includes'.format(options.projectname))
    with open(filepath, 'w') as out:
        cmd = '''find {} -type d '''.format(options.sourcedir)
        filter_list = []
        qtcreator.findfiles(cmd, filter_list, out)
        print('Created {}'.format(filepath))

    filepath = os.path.abspath('{}.creator'.format(options.projectname))
    with open(filepath, 'w') as out:
        out.write('[General]\n')
        print('Created {}'.format(filepath))


def create_userfile(options):
    filepath = os.path.join(options.projectrootdir, '{}.creator.user'.format(options.projectname))
    uf = qtcreator.Userfile(filepath)
    uf.set('EnvironmentId', options.environment_id)
    uf.set('ProjectId', options.profile_id)
    uf.save()
    print('Created {}'.format(filepath))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('projectname', help='The name to be used for the project files')
    parser.add_argument('--sourcefolder', '-s', help=' This is the folder that contains the source code.  Defaults to CWD', default=os.getcwd())
    parser.add_argument('--projectfolder', '-p', help='This is the folder that will contain the QT Creator project files.  Defaults to CWD', default=os.getcwd())
    args = parser.parse_args()
    if len(args.projectname):
        options = Options(args.projectname, args.sourcefolder, args.projectfolder)
        os.chdir(options.projectrootdir)
        create_project_content(options)
        create_userfile(options)

