import subprocess
import os
import os.path
import lxml.etree
import inspect


def get_common_filter():
    return ['*.cpp', '*.cxx', '*.hxx', '*.h', '*.c', '*.rb', '*.py',
            '*.sh', '*.pl', '*.java', '*.js', '*.json', '*.patch', '*.cfg',
            '.config', '*.htm*', 'Makefile', '*.mk', '*.in', 'CMakeLists.txt', '*.adoc', '*.yaml']


def get_script_path():
    return os.path.dirname(os.path.abspath(inspect.stack()[0][1]))


def findfiles(cmd, filter_list, out):
    cmd += ' -or '.join(["-iname '{}'".format(item) for item in filter_list])
    # print(cmd)
    subprocess.run(cmd, shell=True, stdout=out)


def find_git_toplevel():
    cp = subprocess.run(['git', 'rev-parse', '--show-toplevel'], stdout=subprocess.PIPE)
    if cp.returncode == 0:
        return cp.stdout.decode().strip('\n')
    return None


class Userfile:
    def __init__(self, filepath):
        self.filepath = filepath
        if os.path.exists(filepath):
            self.tree = lxml.etree.parse(self.filepath)
        else:
            # print(get_script_path())
            self.tree = lxml.etree.parse(os.path.join(get_script_path(), 'default.user'))

    def get(self, key):
        if key == 'EnvironmentId':
            found = self.tree.xpath('//data[variable="EnvironmentId"]/value/text()')
            if len(found) == 1:
                return found[0]

        elif key == 'ProjectId':
            found = self.tree.xpath('//data/valuemap/value[@key="ProjectExplorer.ProjectConfiguration.Id"]/text()')
            if len(found) == 1:
                return found[0]

        elif key == 'MakeArguments':
            found = self.tree.xpath('//valuemap[@key="ProjectExplorer.Target.BuildConfiguration.0"]//valuemap[@key="ProjectExplorer.BuildConfiguration.BuildStepList.0"]//value[@key="GenericProjectManager.GenericMakeStep.MakeArguments"]/text()')
            if len(found) == 1:
                return found[0]

        elif key == 'BuildDirectory':
            found = self.tree.xpath('//valuemap[@key="ProjectExplorer.Target.BuildConfiguration.0"]//value[@key="ProjectExplorer.BuildConfiguration.BuildDirectory"]/text()')
            if len(found) == 1:
                return found[0]

        elif key == 'BuildEnvironment':
            found = self.tree.xpath('//valuelist[@key="ProjectExplorer.BuildConfiguration.UserEnvironmentChanges"]/value')
            if len(found):
                return [item.text for item in found ]

        elif key == 'Executable':
            found = self.tree.xpath('//valuemap[@key="ProjectExplorer.Target.RunConfiguration.0"]//value[@key="ProjectExplorer.CustomExecutableRunConfiguration.Executable"]/text()')
            if len(found) == 1:
                return found[0]

        elif key == 'ExecutableDisplayName':
            found = self.tree.xpath('//valuemap[@key="ProjectExplorer.Target.RunConfiguration.0"]//value[@key="ProjectExplorer.ProjectConfiguration.DefaultDisplayName"]/text()')
            if len(found) == 1:
                return found[0]

        elif key == 'RunEnvironment':
            found = self.tree.xpath('//valuelist[@key="PE.EnvironmentAspect.Changes"]/value')
            if len(found):
                return [item.text for item in found ]

        return None

    def set(self, key, value):
        if key == 'EnvironmentId':
            found = self.tree.xpath('//data[variable="EnvironmentId"]/value')
            if len(found) == 1:
                found[0].text = value

        elif key == 'ProjectId':
            found = self.tree.xpath('//data/valuemap/value[@key="ProjectExplorer.ProjectConfiguration.Id"]')
            if len(found) == 1:
                found[0].text = value

        elif key == 'MakeArguments':
            found = self.tree.xpath('//valuemap[@key="ProjectExplorer.Target.BuildConfiguration.0"]//valuemap[@key="ProjectExplorer.BuildConfiguration.BuildStepList.0"]//value[@key="GenericProjectManager.GenericMakeStep.MakeArguments"]')
            if len(found) == 1:
                found[0].text = value

        elif key == 'BuildDirectory':
            found = self.tree.xpath('//valuemap[@key="ProjectExplorer.Target.BuildConfiguration.0"]//value[@key="ProjectExplorer.BuildConfiguration.BuildDirectory"]')
            if len(found) == 1:
                found[0].text = value

        elif key == 'BuildEnvironment':
            found = self.tree.xpath('//valuelist[@key="ProjectExplorer.BuildConfiguration.UserEnvironmentChanges"]')
            if len(found) == 1:
                # Remove existing values first
                for child in found[0].getchildren():
                    found[0].remove(child)
                # Add the new values
                for item in value:
                    child = lxml.etree.SubElement(found[0], 'value', type='QString')
                    child.text = item

        elif key == 'Executable':
            found = self.tree.xpath('//valuemap[@key="ProjectExplorer.Target.RunConfiguration.0"]//value[@key="ProjectExplorer.CustomExecutableRunConfiguration.Executable"]')
            if len(found) == 1:
                found[0].text = value

        elif key == 'ExecutableDisplayName':
            found = self.tree.xpath('//valuemap[@key="ProjectExplorer.Target.RunConfiguration.0"]//value[@key="ProjectExplorer.ProjectConfiguration.DefaultDisplayName"]')
            if len(found) == 1:
                found[0].text = value

        elif key == 'RunEnvironment':
            found = self.tree.xpath('//valuelist[@key="PE.EnvironmentAspect.Changes"]')
            if len(found) == 1:
                # Remove existing values first
                for child in found[0].getchildren():
                    found[0].remove(child)
                # Add the new values
                for item in value:
                    child = lxml.etree.SubElement(found[0], 'value', type='QString')
                    child.text = item

        def show(self):
            blob = lxml.etree.tostring(self.tree, pretty_print=True, xml_declaration=True, encoding='utf-8')
            print(blob.decode('utf-8'))

    def save(self):
        self.tree.write(self.filepath, pretty_print=True, xml_declaration=True, encoding='utf-8')

