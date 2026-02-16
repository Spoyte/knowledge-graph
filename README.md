# Knowledge Graph Builder

Creates a queryable graph of all projects, their relationships, dependencies, and shared code. Enables 'find similar code' across all tools.

## Features

- 🔍 **Automatic Code Scanning** - Parses Python files to extract functions, classes, imports
- 🕸️ **Relationship Mapping** - Identifies shared dependencies and similar code across projects
- 🔎 **Semantic Search** - Find similar code by name or description
- 📊 **Project Analytics** - Statistics on code complexity, dependencies, and structure
- 📈 **Visual Diagrams** - Generate Mermaid diagrams of project relationships

## Installation

No dependencies required - uses only Python standard library.

## Usage

### Scan a codebase
```bash
python knowledge_graph.py /path/to/codebase
```

### Search for similar code
```bash
python knowledge_graph.py /path/to/codebase -q "database"
```

### Get project summary
```bash
python knowledge_graph.py /path/to/codebase -p "my-project"
```

### Generate relationship diagram
```bash
python knowledge_graph.py /path/to/codebase --diagram
```

## Output

- `knowledge_graph.json` - Full graph data with all entities and relationships
- `knowledge_graph.mmd` - Mermaid diagram (if --diagram flag used)

## JSON Structure

```json
{
  "metadata": {
    "root_path": "/path/to/codebase",
    "project_count": 10,
    "total_files": 150,
    "total_functions": 500,
    "total_classes": 100,
    "total_lines": 25000
  },
  "projects": { ... },
  "global_entities": {
    "functions": [ ... ],
    "classes": [ ... ]
  },
  "relationships": [ ... ]
}
```

## API Usage

```python
from knowledge_graph import KnowledgeGraph

# Build the graph
graph = KnowledgeGraph('/path/to/codebase')
graph.scan()

# Search for code
results = graph.find_similar_code('database', top_k=5)

# Get project info
summary = graph.get_project_summary('my-project')

# Export
graph.export('output.json')
```
