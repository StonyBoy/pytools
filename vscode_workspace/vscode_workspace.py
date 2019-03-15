#! /usr/bin/env python3
'''
Create a Visual Studio workspace and associated files using a source folder

It creates four files:

    <projectname>.code-workspace       : The workspace file
    .vscode/tasks.json                 : Build tasks
    .vscode/launch.json                : Debugging
    .vscode/c_cpp_properties.json      : C and C++ configuration

The c_cpp_properties file is created from makefile information.

'''
import os
import subprocess
import re
import collections
import json
import argparse
import sys
import glob

FileCreatedText = '''The file {} was created'''
FileExistsText = '''The file {} already exists.  Please delete the file first if you need to update it'''

def run(args, as_line_list=False):
    cp = subprocess.run(args.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode == 0:
        return cp.stdout.decode().split('\n') if as_line_list else cp.stdout.decode().strip('\n')
    raise RuntimeError('Error running "{}"\n{}'.format(args, cp.stderr.decode()))


def run_ignore(args, as_line_list=False):
    cp = subprocess.run(args.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return cp.stdout.decode().split('\n') if as_line_list else cp.stdout.decode().strip('\n')


def find(path, filter_list, dirs=False, maxdepth=None, mindepth=None):
    args = 'find {} -type {}'.format(path, 'd' if dirs else 'f')
    args += ' -maxdepth {}'.format(maxdepth) if maxdepth is not None else ''
    args += ' -mindepth {}'.format(mindepth) if mindepth is not None else ''
    args += ' -or '.join([" -iname {}".format(item) for item in filter_list])
    return run(args, as_line_list=True)


class Options:
    compile_commands = 'compile_commands.json'

    def __init__(self):
        try:
            self.top = run('git rev-parse --show-toplevel')
        except RuntimeError:
            self.top = os.getcwd()
        self.current_folder = None
        self.name = None
        self.source_folder = None
        self.settings_folder = None
        self.workspace_folder = None
        self.build_folder = None
        self.compile_commands_path = None
        self.is_webstax_folder = False
        self.defines = None
        self.includes = None
        self.selected_compiler = None
        self.tools = {}
        self._set_folders(self.top)
        self._find_compile_commands_json()
        self._find_compiler()

    def __str__(self):
        result = 'Options'
        result += self._value('current_folder')
        result += self._value('name')
        result += self._value('source_folder')
        result += self._value('settings_folder')
        result += self._value('workspace_folder')
        result += self._value('build_folder')
        result += self._value('compile_commands_path')
        result += self._value('cpp_include_path')
        result += self._value('is_webstax_folder')
        result += self._value('defines')
        result += self._value('tools')
        return result

    def set_name(self, name):
        self.name = name

    def set_current_folder(self, folder):
        self.current_folder = os.path.abspath(folder)

    def set_defines(self, args):
        self.defines = args

    def set_includes(self, args):
        self.includes = args

    def _set_folders(self, folder):
        self.source_folder = os.path.expanduser(folder)
        self.workspace_folder = os.path.expanduser(folder)
        self.settings_folder = os.path.join(self.source_folder, '.vscode')
        self.build_folder = os.path.join(self.source_folder, 'build')
        if os.path.exists(os.path.join(self.source_folder, 'vtss_appl')):
            self.is_webstax_folder = True

    def _find_compile_commands_json(self):
        compile_commands_path = os.path.join(self.source_folder, Options.compile_commands)
        if os.path.exists(compile_commands_path):
            self.compile_commands_path = compile_commands_path
        else:
            try:
                other_path = find(self.source_folder, [Options.compile_commands], mindepth=2)
                if len(other_path) >= 1 and len(other_path[0]):
                    try:
                        os.symlink(other_path[0], compile_commands_path)
                        self.compile_commands_path = compile_commands_path
                    except FileExistsError:
                        pass
            except RuntimeError:
                print('Could not find any {} file'.format(Options.compile_commands))

    def _find_compiler(self):
        for compiler in ['g++', 'clang++']:
            self.tools[compiler] = None
            try:
                self.tools[compiler] = run('which ' + compiler)
                self._find_compiler_includes(compiler)
                self.selected_compiler = compiler
            except RuntimeError:
                pass
        for compiler in ['gcc', 'clang']:
            self.tools[compiler] = None
            try:
                self.tools[compiler] = run('which ' + compiler)
            except RuntimeError:
                pass

    def _find_compiler_includes(self, compiler):
        testfile = os.path.join(self.source_folder, 'vtss_appl/main/main.cxx')
        found = False
        includes = []
        for line in run_ignore(self.tools[compiler] + ' -v -c ' + testfile, as_line_list=True):
            if line.startswith('End of search list.'):
                found = False
            if found:
                includes.append(os.path.abspath(line.strip()))
            if line.startswith('#include <...> search starts here:'):
                found = True
        self.tools[compiler + '_includes'] = includes


    def _value(self,arg):
        return ' {}={}'.format(arg, str(getattr(self, arg)))

class WorkspaceFile:
    def __init__(self, name):
        self.name = name
        self.value = {'folders': [], 'settings': {}}

    def add_folder(self, folder):
        self.value['folders'].append({'path': folder})

    def add_setting(self, key, value):
        self.value['settings'][key] = value

    def save(self):
        with open(self.name, 'wt') as obj:
            json.dump(self.value, obj, indent=4)


class CppPropertiesFile:
    def __init__(self, name : str):
        self.name = name
        self.value = {'configurations': [], 'version': 4}

    def add_linux_configuration(self, compiler_path, browse_paths, include_paths, defines, options : Options):
        conf = {'name': 'Linux',
            'includePath': include_paths,
            'browse': {'path': browse_paths, 'limitSymbolsToIncludedHeaders': True, 'databaseFilename': '' },
            'defines': defines,
            'compilerPath': compiler_path,
            'cStandard': 'c11',
            'cppStandard': 'c++17',
            "compileCommands": options.compile_commands_path,
            "intelliSenseMode": "clang-x64"
        }
        self.value['configurations'].append(conf)

    def save(self):
        with open(self.name, 'wt') as obj:
            json.dump(self.value, obj, indent=4)


def create_settings_folder(options : Options):
    if not os.path.exists(options.settings_folder):
        os.makedirs(options.settings_folder)


def create_workspace_file(options : Options):
    if not os.path.exists(options.workspace_folder):
        os.makedirs(options.workspace_folder)
    fullpath = os.path.join(options.workspace_folder, options.name + '.code-workspace')
    if os.path.exists(fullpath):
        print(FileExistsText.format(fullpath))
    else:
        ws = WorkspaceFile(fullpath)
        ws.add_folder(options.source_folder)
        ws.add_setting('cquery.cacheDirectory', options.settings_folder)
        ws.save()
        print(FileCreatedText.format(fullpath))


def create_c_cpp_properties_file(options : Options):
    fullpath = os.path.join(options.settings_folder, 'c_cpp_properties.json')
    if os.path.exists(fullpath):
        print(FileExistsText.format(fullpath))
    else:
        create_settings_folder(options)
        if options.selected_compiler:
            compiler_path = options.tools[options.selected_compiler]
            compiler_includes = options.tools[options.selected_compiler + '_includes']
        else:
            return
        defines = options.defines
        includes = compiler_includes
        for item in options.includes:
            includes.append(os.path.join(options.source_folder, item))
        if options.is_webstax_folder:
            vtss_folders = ' '.join(glob.glob(os.path.join(options.source_folder, 'vtss_*')))
            for item in find(vtss_folders, ['*.h', '*.hpp', '*.hxx']):
                includes.append(os.path.dirname(item))
        includes += find(options.source_folder, ['include'], dirs=True)
        unique_includes = list(set(includes))
        unique_includes.sort()
        cpp = CppPropertiesFile(fullpath)
        cpp.add_linux_configuration(
            compiler_path,
            unique_includes,
            unique_includes,
            defines,
            options)
        cpp.save()
        print(FileCreatedText.format(fullpath))


class TasksFile:
    def __init__(self, name : str):
        self.name = name
        self.value = {'tasks': [], 'version': '2.0.0'}

    def add_task(self, label, command, build_kind='build', matchers=['$gcc'], is_default=False):
        conf = {
            'label': label,
            'type': 'shell',
            'command': command,
            'group': {'kind': build_kind, 'isDefault': is_default} if is_default else build_kind,
            'problemMatcher': matchers
        }
        self.value['tasks'].append(conf)

    def save(self):
        with open(self.name, 'wt') as obj:
            json.dump(self.value, obj, indent=4)


def create_tasks_file(options: Options):
    fullpath = os.path.join(options.settings_folder, 'tasks.json')
    if os.path.exists(fullpath):
        print(FileExistsText.format(fullpath))
    else:
        create_settings_folder(options)
        tf = TasksFile(fullpath)
        if options.is_webstax_folder:
            matcher = {
                'owner': 'cpp',
                'fileLocation': ['relative', '${workspaceFolder}/build/obj'],
                'pattern': {
                    'regexp': r'^(.*):(\d+):(\d+):\s+(warning|error):\s+(.*)$',
                    'file': 1,
                    'line': 2,
                    'column': 3,
                    'severity': 4,
                    'message': 5
                }
            }
            tf.add_task('Build WebStaX firmware', 'cd  ${workspaceFolder}/build && make -j 8', 'build', matcher, True)
            if options.tools['clang++']:
                tf.add_task('Prepare VTSS Basics build (using CLANG)',
                    'cd  ${{workspaceFolder}}/vtss_basics && rm -rf build && mkdir build && cd build && CC={} CXX={} cmake ..'.format(options.tools['clang'], options.tools['clang++']),
                    'build',
                    matcher)
            if options.tools['g++']:
                tf.add_task('Prepare VTSS Basics build (using GCC)',
                    'cd  ${{workspaceFolder}}/vtss_basics && rm -rf build && mkdir build && cd build && CC={} CXX={} cmake ..'.format(options.tools['gcc'], options.tools['g++']),
                    'build',
                    matcher)
            tf.add_task('VTSS Basics build', 'cd  ${workspaceFolder}/vtss_basics/build && make -j 8', 'build', matcher)
            tf.add_task('FFR unittest build', 'cd  ${workspaceFolder}/vtss_basics/build && make -j 8 frr_tests', 'build', matcher)
            tf.save()
            print(FileCreatedText.format(fullpath))
        elif os.path.exists(os.path.join(options.source_folder, 'build')):
            tf.add_task('Build Project', 'cd  ${workspaceFolder}/build && make -j 8')
            tf.save()
            print(FileCreatedText.format(fullpath))
        elif os.path.exists(os.path.join(options.source_folder, 'Makefile')):
            tf.add_task('Build Project', 'cd  ${workspaceFolder} && make -j 8')
            tf.save()
            print(FileCreatedText.format(fullpath))


class LaunchFile:
    def __init__(self, name : str, options : Options):
        self.name = name
        self.options = options
        self.value = {'configurations': [], 'version': '0.2.0'}

    def add_configuration(self, name, program, args=[], depends=''):
        substitute_path = ''
        if self.options.selected_compiler:
            compiler_includes = self.options.tools[self.options.selected_compiler + '_includes']
            if len(compiler_includes) > 0:
                substitute_path = compiler_includes[0]
        conf = {
            'name': name,
            'type': 'cppdbg',
            'request': 'launch',
            'program': program,
            'args': args,
            'stopAtEntry': False,
            'cwd': os.path.dirname(program),
            'environment': [],
            'externalConsole': True,
            'MIMode': 'gdb',
            'setupCommands': [
                {
                    'description': 'Enable pretty-printing for gdb',
                    'text': '-enable-pretty-printing',
                    'ignoreFailures': True
                },
                {
                    'description': 'Substitute missing build path for ostream library',
                    'text': 'set substitute-path /build/gcc/src/gcc-build/x86_64-pc-linux-gnu/libstdc++-v3/include {}'.format(substitute_path)
                }
            ],
            'preLaunchTask': depends
        }
        self.value['configurations'].append(conf)

    def save(self):
        with open(self.name, 'wt') as obj:
            json.dump(self.value, obj, indent=4)


def create_launch_file(options: Options):
    fullpath = os.path.join(options.settings_folder, 'launch.json')
    if os.path.exists(fullpath):
        print(FileExistsText.format(fullpath))
    else:
        create_settings_folder(options)
        lf = LaunchFile(fullpath, options)
        if options.is_webstax_folder:
            lf.add_configuration('Debug FRR Unittest', '${workspaceFolder}/vtss_basics/build/frr/frr_tests', [], 'FFR unittest build')
            lf.save()
            print(FileCreatedText.format(fullpath))
        elif os.path.exists(os.path.join(options.source_folder, 'Makefile')) or os.path.exists(os.path.join(options.source_folder, 'Makefile')):
            lf.add_configuration('Debug Project', '${workspaceFolder}/executable', [], 'Build Project')
            lf.save()
            print(FileCreatedText.format(fullpath))


def parse_commandline(options : Options):
    name = os.path.basename(options.source_folder).lower()
    options.set_name(name)
    options.set_current_folder(os.path.dirname(sys.argv[0]))
    includes = []
    defines = []
    for setting in sys.argv[3:]:
        if setting.startswith('-I'):
            includes.append(os.path.abspath(os.path.join(options.current_folder, setting[2:])))
        if setting.startswith('-D'):
            defines.append(setting[2:])
    options.set_includes(includes)
    options.set_defines(defines)
    return True


if __name__ == '__main__':
    options = Options()
    if parse_commandline(options):
        create_workspace_file(options)
        create_c_cpp_properties_file(options)
        create_tasks_file(options)
        create_launch_file(options)
