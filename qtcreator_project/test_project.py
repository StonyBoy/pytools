import os
import unittest
from qtcreator import Userfile
from qtcreator_lego_project import Options


class TestOptions(unittest.TestCase):
    def test_construction(self):
        os.environ['LEGO_ROOT'] = '~'
        options = Options('hello')
        self.assertEqual(options.projectname, 'hello')
        self.assertEqual(options.projectrootdir, os.path.abspath(os.path.expanduser('~')))
        self.assertEqual(options.curdir, os.path.abspath(os.path.curdir))

    def test_project_values(self):
        os.environ['LEGO_ROOT'] = '~'
        options = Options('one')
        self.assertEqual(options.environment_id, '{2caf13c9-7851-4076-bcb5-de515e38eaec}')
        self.assertEqual(options.profile_id, '{ae2ce6eb-36e0-445a-82df-63dfff863bdd}')

    @unittest.skip('Not correct - path problem')
    def test_environment(self):
        os.environ['LEGO_ROOT'] = '~'
        os.environ['LEGO_TEST'] = 'Alpha'
        os.environ['LEGO_HELP'] = 'Beta'
        options = Options('two')
        self.assertDictEqual(options.lego_environment, {'LEGO_ROOT': '~', 'LEGO_HELP': 'Beta', 'LEGO_TEST': 'Alpha'})
        self.assertListEqual(options.get_lego_environment_list(), ['LEGO_HELP=Beta', 'LEGO_ROOT=~', 'LEGO_TEST=Alpha'])


class TestUserFile(unittest.TestCase):
    def test_default_user(self):
        uf = Userfile('')
        self.assertEqual(uf.get('EnvironmentId'), '{}')
        self.assertEqual(uf.get('ProjectId'), '{}')
        self.assertEqual(uf.get('MakeArguments'), None)
        self.assertEqual(uf.get('BuildDirectory'), None)
        self.assertEqual(uf.get('BuildEnvironment'), None)
        self.assertEqual(uf.get('Executable'), None)
        self.assertEqual(uf.get('ExecutableDisplayName'), 'Custom Executable')
        self.assertEqual(uf.get('RunEnvironment'), None)

    def test_set_default_user(self):
        uf = Userfile('')
        uf.set('EnvironmentId', '{hello_world}')
        uf.set('ProjectId', '{pingo}')
        uf.set('MakeArguments', 'make my day')
        uf.set('BuildDirectory', '/usr/lib')
        uf.set('BuildEnvironment', ['USER=shegelund', 'GROUP=users'])
        uf.set('Executable', '~/bin/hello')
        uf.set('ExecutableDisplayName', 'Run ~/bin/hello')
        uf.set('RunEnvironment', ['GTEST=-d', 'HOME=/home/shegelund'])
        self.assertEqual(uf.get('EnvironmentId'), '{hello_world}')
        self.assertEqual(uf.get('ProjectId'), '{pingo}')
        self.assertEqual(uf.get('MakeArguments'), 'make my day')
        self.assertEqual(uf.get('BuildDirectory'), '/usr/lib')
        self.assertEqual(uf.get('BuildEnvironment'), ['USER=shegelund', 'GROUP=users'])
        self.assertEqual(uf.get('Executable'), '~/bin/hello')
        self.assertEqual(uf.get('ExecutableDisplayName'), 'Run ~/bin/hello')
        self.assertEqual(uf.get('RunEnvironment'), ['GTEST=-d', 'HOME=/home/shegelund'])



if __name__ == '__main__':
    unittest.main()

