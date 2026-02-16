#!/usr/bin/env python3
"""
Knowledge Graph Builder for Codebase

Creates a queryable graph of all projects, their relationships, dependencies,
and shared code. Enables 'find similar code' across all tools.

Author: Nemo (AI Assistant)
Date: 2026-02-16
"""

import os
import json
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import hashlib


@dataclass
class CodeEntity:
    """Base class for code entities"""
    name: str
    file_path: str
    line_start: int
    line_end: int
    docstring: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)


@dataclass 
class Function(CodeEntity):
    """Represents a function/method"""
    args: List[str] = field(default_factory=list)
    returns: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    complexity: int = 1
    calls: List[str] = field(default_factory=list)


@dataclass
class Class(CodeEntity):
    """Represents a class"""
    bases: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)


@dataclass
class Module:
    """Represents a Python module"""
    path: str
    name: str
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    functions: List[Function] = field(default_factory=list)
    classes: List[Class] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    
    def to_dict(self):
        return {
            'path': self.path,
            'name': self.name,
            'imports': self.imports,
            'exports': self.exports,
            'functions': [f.to_dict() for f in self.functions],
            'classes': [c.to_dict() for c in self.classes],
            'dependencies': list(self.dependencies)
        }


@dataclass
class Project:
    """Represents a project/directory"""
    name: str
    path: str
    modules: List[Module] = field(default_factory=list)
    language: str = "python"
    description: Optional[str] = None
    
    def to_dict(self):
        return {
            'name': self.name,
            'path': self.path,
            'language': self.language,
            'description': self.description,
            'modules': [m.to_dict() for m in self.modules]
        }


class PythonParser:
    """Parse Python files to extract code structure"""
    
    @staticmethod
    def parse_file(file_path: str) -> Optional[Module]:
        """Parse a Python file and extract its structure"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            module_name = Path(file_path).stem
            
            module = Module(
                path=file_path,
                name=module_name
            )
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module.imports.append(alias.name)
                        module.dependencies.add(alias.name.split('.')[0])
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module.imports.append(node.module)
                        module.dependencies.add(node.module.split('.')[0])
                
                elif isinstance(node, ast.FunctionDef):
                    func = PythonParser._parse_function(node, file_path, source)
                    module.functions.append(func)
                    module.exports.append(func.name)
                
                elif isinstance(node, ast.ClassDef):
                    cls = PythonParser._parse_class(node, file_path, source)
                    module.classes.append(cls)
                    module.exports.append(cls.name)
            
            return module
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    @staticmethod
    def _parse_function(node: ast.FunctionDef, file_path: str, source: str) -> Function:
        """Extract function information"""
        docstring = ast.get_docstring(node)
        
        # Get arguments
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)
        
        # Get decorators
        decorators = [ast.unparse(d) for d in node.decorator_list]
        
        # Get return type
        returns = ast.unparse(node.returns) if node.returns else None
        
        # Calculate complexity (simple: count of branches)
        complexity = 1
        calls = []
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)
        
        return Function(
            name=node.name,
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=docstring,
            args=args,
            returns=returns,
            decorators=decorators,
            complexity=complexity,
            calls=calls
        )
    
    @staticmethod
    def _parse_class(node: ast.ClassDef, file_path: str, source: str) -> Class:
        """Extract class information"""
        docstring = ast.get_docstring(node)
        
        bases = [ast.unparse(base) for base in node.bases]
        methods = []
        attributes = []
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attributes.append(target.id)
        
        return Class(
            name=node.name,
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=docstring,
            bases=bases,
            methods=methods,
            attributes=attributes
        )


class KnowledgeGraph:
    """Main knowledge graph for the codebase"""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.projects: Dict[str, Project] = {}
        self.global_entities: Dict[str, List[Dict]] = defaultdict(list)
        self.relationships: List[Dict] = []
        self.stats = {
            'total_files': 0,
            'total_functions': 0,
            'total_classes': 0,
            'total_lines': 0
        }
    
    def scan(self, exclude_patterns: List[str] = None):
        """Scan the codebase and build the knowledge graph"""
        exclude_patterns = exclude_patterns or ['__pycache__', '.git', 'node_modules', '.venv', 'venv']
        
        # Find all Python projects
        for project_path in self.root_path.rglob('*.py'):
            # Check if excluded
            if any(pat in str(project_path) for pat in exclude_patterns):
                continue
            
            # Determine project root (directory containing the file)
            proj_dir = project_path.parent
            while proj_dir != self.root_path and not (proj_dir / '__init__.py').exists():
                proj_dir = proj_dir.parent
            
            project_name = proj_dir.name or 'root'
            
            if project_name not in self.projects:
                self.projects[project_name] = Project(
                    name=project_name,
                    path=str(proj_dir)
                )
            
            # Parse the file
            module = PythonParser.parse_file(str(project_path))
            if module:
                self.projects[project_name].modules.append(module)
                self._update_stats(module)
                self._index_entities(project_name, module)
        
        self._build_relationships()
    
    def _update_stats(self, module: Module):
        """Update global statistics"""
        self.stats['total_files'] += 1
        self.stats['total_functions'] += len(module.functions)
        self.stats['total_classes'] += len(module.classes)
        
        try:
            with open(module.path, 'r') as f:
                self.stats['total_lines'] += len(f.readlines())
        except:
            pass
    
    def _index_entities(self, project_name: str, module: Module):
        """Index entities for global search"""
        for func in module.functions:
            self.global_entities['functions'].append({
                'name': func.name,
                'project': project_name,
                'module': module.name,
                'path': module.path,
                'line': func.line_start,
                'docstring': func.docstring,
                'complexity': func.complexity
            })
        
        for cls in module.classes:
            self.global_entities['classes'].append({
                'name': cls.name,
                'project': project_name,
                'module': module.name,
                'path': module.path,
                'line': cls.line_start,
                'docstring': cls.docstring,
                'methods': cls.methods
            })
    
    def _build_relationships(self):
        """Build cross-project relationships"""
        # Find shared dependencies
        dep_projects = defaultdict(set)
        for proj_name, project in self.projects.items():
            for module in project.modules:
                for dep in module.dependencies:
                    dep_projects[dep].add(proj_name)
        
        for dep, projects in dep_projects.items():
            if len(projects) > 1:
                self.relationships.append({
                    'type': 'shared_dependency',
                    'dependency': dep,
                    'projects': list(projects)
                })
        
        # Find similar function names across projects
        func_names = defaultdict(list)
        for proj_name, project in self.projects.items():
            for module in project.modules:
                for func in module.functions:
                    func_names[func.name].append({
                        'project': proj_name,
                        'module': module.name,
                        'path': module.path
                    })
        
        for func_name, locations in func_names.items():
            if len(locations) > 1:
                self.relationships.append({
                    'type': 'similar_function',
                    'name': func_name,
                    'locations': locations
                })
    
    def find_similar_code(self, query: str, top_k: int = 5) -> List[Dict]:
        """Find similar code across all projects"""
        query_lower = query.lower()
        results = []
        
        # Search in function names
        for func in self.global_entities['functions']:
            score = 0
            if query_lower in func['name'].lower():
                score += 10
            if func['docstring'] and query_lower in func['docstring'].lower():
                score += 5
            
            if score > 0:
                results.append({
                    'type': 'function',
                    'score': score,
                    **func
                })
        
        # Search in class names
        for cls in self.global_entities['classes']:
            score = 0
            if query_lower in cls['name'].lower():
                score += 10
            if cls['docstring'] and query_lower in cls['docstring'].lower():
                score += 5
            
            if score > 0:
                results.append({
                    'type': 'class',
                    'score': score,
                    **cls
                })
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
    
    def get_project_summary(self, project_name: str) -> Optional[Dict]:
        """Get summary of a specific project"""
        if project_name not in self.projects:
            return None
        
        project = self.projects[project_name]
        return {
            'name': project.name,
            'path': project.path,
            'module_count': len(project.modules),
            'function_count': sum(len(m.functions) for m in project.modules),
            'class_count': sum(len(m.classes) for m in project.modules),
            'dependencies': list(set().union(*[m.dependencies for m in project.modules]))
        }
    
    def export(self, output_path: str):
        """Export the knowledge graph to JSON"""
        graph_data = {
            'metadata': {
                'root_path': str(self.root_path),
                'project_count': len(self.projects),
                **self.stats
            },
            'projects': {name: proj.to_dict() for name, proj in self.projects.items()},
            'global_entities': dict(self.global_entities),
            'relationships': self.relationships
        }
        
        with open(output_path, 'w') as f:
            json.dump(graph_data, f, indent=2)
        
        return output_path
    
    def generate_mermaid_diagram(self) -> str:
        """Generate a Mermaid diagram of project relationships"""
        lines = ['graph TD']
        
        # Add project nodes
        for proj_name in self.projects:
            safe_name = re.sub(r'[^a-zA-Z0-9]', '_', proj_name)
            lines.append(f'    {safe_name}["{proj_name}"]')
        
        # Add relationships
        for rel in self.relationships:
            if rel['type'] == 'shared_dependency':
                projects = rel['projects']
                for i in range(len(projects)):
                    for j in range(i + 1, len(projects)):
                        p1 = re.sub(r'[^a-zA-Z0-9]', '_', projects[i])
                        p2 = re.sub(r'[^a-zA-Z0-9]', '_', projects[j])
                        lines.append(f'    {p1} -->|"uses {rel["dependency"]}"| {p2}')
        
        return '\n'.join(lines)


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Knowledge Graph Builder for Codebase')
    parser.add_argument('path', nargs='?', default='.', help='Root path to scan')
    parser.add_argument('-o', '--output', default='knowledge_graph.json', help='Output JSON file')
    parser.add_argument('-q', '--query', help='Search query for similar code')
    parser.add_argument('-d', '--diagram', action='store_true', help='Generate Mermaid diagram')
    parser.add_argument('-p', '--project', help='Get summary for specific project')
    
    args = parser.parse_args()
    
    print(f"🔍 Scanning codebase at: {args.path}")
    graph = KnowledgeGraph(args.path)
    graph.scan()
    
    print(f"📊 Found {len(graph.projects)} projects")
    print(f"   - {graph.stats['total_files']} files")
    print(f"   - {graph.stats['total_functions']} functions")
    print(f"   - {graph.stats['total_classes']} classes")
    print(f"   - {graph.stats['total_lines']} lines of code")
    
    # Export to JSON
    output_file = graph.export(args.output)
    print(f"\n💾 Knowledge graph exported to: {output_file}")
    
    # Query mode
    if args.query:
        print(f"\n🔎 Searching for: '{args.query}'")
        results = graph.find_similar_code(args.query)
        for r in results:
            print(f"  [{r['score']}] {r['type']} {r['name']} in {r['project']}/{r['module']}")
    
    # Project summary
    if args.project:
        print(f"\n📁 Project: {args.project}")
        summary = graph.get_project_summary(args.project)
        if summary:
            print(f"  Path: {summary['path']}")
            print(f"  Modules: {summary['module_count']}")
            print(f"  Functions: {summary['function_count']}")
            print(f"  Classes: {summary['class_count']}")
            print(f"  Dependencies: {', '.join(summary['dependencies'][:10])}")
        else:
            print(f"  Project not found!")
    
    # Generate diagram
    if args.diagram:
        diagram = graph.generate_mermaid_diagram()
        diagram_file = args.output.replace('.json', '.mmd')
        with open(diagram_file, 'w') as f:
            f.write(diagram)
        print(f"\n📈 Mermaid diagram saved to: {diagram_file}")


if __name__ == '__main__':
    main()
