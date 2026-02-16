import unittest
import tempfile
import os
from pathlib import Path
from knowledge_graph import KnowledgeGraph, PythonParser, Module, Function, Class


class TestPythonParser(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_parse_simple_function(self):
        code = '''
def hello_world():
    """Say hello to the world."""
    print("Hello, World!")
'''
        test_file = Path(self.temp_dir) / 'test.py'
        test_file.write_text(code)
        
        module = PythonParser.parse_file(str(test_file))
        
        self.assertIsNotNone(module)
        self.assertEqual(len(module.functions), 1)
        self.assertEqual(module.functions[0].name, 'hello_world')
        self.assertEqual(module.functions[0].docstring, 'Say hello to the world.')
    
    def test_parse_class(self):
        code = '''
class Person:
    """Represents a person."""
    
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}"
'''
        test_file = Path(self.temp_dir) / 'test.py'
        test_file.write_text(code)
        
        module = PythonParser.parse_file(str(test_file))
        
        self.assertIsNotNone(module)
        self.assertEqual(len(module.classes), 1)
        self.assertEqual(module.classes[0].name, 'Person')
        self.assertIn('__init__', module.classes[0].methods)
        self.assertIn('greet', module.classes[0].methods)
    
    def test_parse_imports(self):
        code = '''
import os
import sys
from pathlib import Path
from typing import List, Dict
'''
        test_file = Path(self.temp_dir) / 'test.py'
        test_file.write_text(code)
        
        module = PythonParser.parse_file(str(test_file))
        
        self.assertIsNotNone(module)
        self.assertIn('os', module.imports)
        self.assertIn('sys', module.imports)
        self.assertIn('pathlib', module.imports)
        self.assertIn('typing', module.imports)
        self.assertIn('os', module.dependencies)
        self.assertIn('sys', module.dependencies)


class TestKnowledgeGraph(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test project structure
        proj_dir = Path(self.temp_dir) / 'test_project'
        proj_dir.mkdir()
        
        # Create test files
        (proj_dir / 'module1.py').write_text('''
def helper_func():
    pass

class MyClass:
    def method(self):
        pass
''')
        
        (proj_dir / 'module2.py').write_text('''
from module1 import helper_func

def another_func():
    helper_func()
''')
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_scan(self):
        graph = KnowledgeGraph(self.temp_dir)
        graph.scan()
        
        self.assertGreater(len(graph.projects), 0)
        self.assertGreater(graph.stats['total_files'], 0)
    
    def test_find_similar_code(self):
        graph = KnowledgeGraph(self.temp_dir)
        graph.scan()
        
        results = graph.find_similar_code('helper')
        self.assertGreater(len(results), 0)
    
    def test_export(self):
        graph = KnowledgeGraph(self.temp_dir)
        graph.scan()
        
        output_file = Path(self.temp_dir) / 'output.json'
        graph.export(str(output_file))
        
        self.assertTrue(output_file.exists())
        
        import json
        with open(output_file) as f:
            data = json.load(f)
        
        self.assertIn('metadata', data)
        self.assertIn('projects', data)


if __name__ == '__main__':
    unittest.main()
