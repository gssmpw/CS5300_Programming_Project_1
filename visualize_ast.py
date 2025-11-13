# visualize_ast.py

from sqlglot import parse_one, exp
from sqlglot.errors import ParseError
import pydot_ng as pydot
import os
import typing as t

# --- New Function for Building the Graphviz DOT structure ---

def build_dot_graph(node: exp.Expression, graph: pydot.Dot, parent_id: str) -> str:
    """
    Recursively builds a pydot graph from a sqlglot AST node.
    
    Args:
        node: The current AST node (sqlglot.expressions.Expression).
        graph: The main pydot.Dot object.
        parent_id: The unique ID of the parent node in the graph.
        
    Returns:
        The unique ID of the current node.
    """
    # 1. Create a unique ID for the current node
    node_id = f"node_{id(node)}"

    # 2. Determine the label and style for the node
    node_type = node.__class__.__name__
    identifier = getattr(node, "alias_or_name", None) or getattr(node, "name", "")
    
    # Create a descriptive label (Type: Identifier)
    label = f"{node_type}\n[{identifier}]"
    
    # Use different colors/shapes for main clauses vs. simple leaves
    shape = 'box' if node_type in ('Select', 'From', 'Where', 'With') else 'ellipse'
    
    # 3. Add the node to the graph
    pydot_node = pydot.Node(
        name=node_id, 
        label=label, 
        shape=shape, 
        style="filled", 
        fillcolor="#ADD8E6" if shape == 'box' else "white"
    )
    graph.add_node(pydot_node)
    
    # 4. Connect the current node to its parent
    if parent_id:
        graph.add_edge(pydot.Edge(parent_id, node_id))

    # 5. Recursively process children
    for key, value in node.args.items():
        if isinstance(value, exp.Expression):
            # Single expression child (e.g., From has one Table)
            build_dot_graph(value, graph, node_id)
        elif isinstance(value, list):
            # List of expression children (e.g., Select has a list of projections)
            for i, item in enumerate(value):
                if isinstance(item, exp.Expression):
                    build_dot_graph(item, graph, node_id)
        
    return node_id

# --- Existing Helper Functions (Simplified) ---

def read_sql_query(file_path: str) -> str:
    """Reads the SQL query from the specified file path."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Error: The file '{file_path}' was not found.")
    print(f"✅ Reading SQL from: {file_path}")
    with open(file_path, 'r') as f:
        return f.read()

# --- Main Parsing and Visualization Function ---

def visualize_ast(sql_query: str, output_path: str = "sql_ast.png"):
    """Parses SQL and generates a visual AST diagram."""
    print("--- Starting AST Visualization Process ---")
    try:
        # Parse the SQL
        ast = parse_one(sql_query, read="postgres")
        
        # Initialize the pydot graph
        graph = pydot.Dot(graph_type='digraph', rankdir='TB')
        
        # Recursively build the graph starting from the root AST node
        build_dot_graph(ast, graph, parent_id=None)
        
        # Save the graph to a file
        graph.write_png(output_path)
        
        print(f"✅ Successfully generated visual AST diagram: {output_path}")

    except ParseError as e:
        print(f"\n❌ SQL PARSE ERROR: {e}")
    except FileNotFoundError:
        print("\n❌ ERROR: Graphviz not found!")
        print("Please ensure Graphviz is installed and in your system's PATH.")
    except Exception as e:
        print(f"\nAn unexpected error occurred during visualization: {e}")


if __name__ == "__main__":
    SQL_FILE = "query.txt"
    OUTPUT_FILE = "sql_query_ast.png"
    
    try:
        sql_content = read_sql_query(SQL_FILE)
        visualize_ast(sql_content, OUTPUT_FILE)
        
    except FileNotFoundError as e:
        print(e)