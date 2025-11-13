# parse_sql.py

from sqlglot import parse_one, exp
from sqlglot.errors import ParseError
import os
import typing as t

# --- New Function for Visualizing the AST ---

def print_ast_tree(node: exp.Expression, level: int = 0):
    """
    Recursively prints the AST structure in a human-readable, indented format.
    """
    indent = "  " * level
    
    # Get the node's type name (e.g., 'Select', 'Table', 'Column')
    node_type = node.__class__.__name__
    
    # Get a primary identifier for the node (e.g., the name of a column or table)
    # We use .alias_or_name for expressions that might have an alias, 
    # and fall back to the node's .name or 'N/A'
    identifier = getattr(node, "alias_or_name", None)
    if identifier is None:
        identifier = getattr(node, "name", "N/A")
    
    # Print the current node
    print(f"{indent}├── {node_type} [{identifier}]")

    # Get the children expressions to iterate over
    # We use node.args.values() because it's a reliable way to get all child expressions
    child_expressions = [
        val for val in node.args.values() 
        if isinstance(val, (exp.Expression, list))
    ]

    # Recursively call this function for all children
    for child in child_expressions:
        if isinstance(child, list):
            # If the child is a list of expressions (e.g., SELECT projections), iterate through the list
            print(f"{indent}│   └── (List of {node_type}'s Arguments)")
            for item in child:
                if isinstance(item, exp.Expression):
                    print_ast_tree(item, level + 2)
        else:
            print_ast_tree(child, level + 1)


# --- Existing Helper Functions ---

def read_sql_query(file_path: str) -> str:
    """Reads the SQL query from the specified file path."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Error: The file '{file_path}' was not found.")
    print(f"✅ Reading SQL from: {file_path}")
    with open(file_path, 'r') as f:
        return f.read()

def get_main_select_expression(ast: exp.Expression) -> t.Optional[exp.Select]:
    """Finds the main (outermost) SELECT statement in the AST."""
    all_selects = list(ast.find_all(exp.Select))
    return all_selects[-1] if all_selects else None


def parse_and_analyze_sql(sql_query: str):
    """Parses the SQL query and extracts key components."""
    print("--- Starting SQL Parsing ---")
    try:
        ast = parse_one(sql_query, read="postgres")
        
        # --- AST Visualization ---
        print("\n=== VISUAL AST STRUCTURE ===")
        # Call the new function to print the tree starting from the root node
        print_ast_tree(ast)
        print("============================\n")


        # --- Analysis Results (kept for reference) ---
        
        tables = set()
        for table in ast.find_all(exp.Table):
            full_table_name = f"{table.db}.{table.name}" if table.db else table.name
            tables.add(full_table_name)
        
        ctes = [cte.alias for cte in ast.find_all(exp.CTE)]

        main_select = get_main_select_expression(ast)
        columns = [
            projection.alias_or_name
            for projection in main_select.expressions
        ] if main_select else ["N/A"]


        print("--- Analysis Results ---")
        print(f"Root AST Type: {type(ast)}")
        print(f"Source Tables Used: {tables}")
        print(f"CTEs Defined: {ctes}")
        print(f"Final Projected Columns: {columns}")
        
        # ... rest of the code remains the same ...
        print("\n--- Generated SQL (Formatted) ---")
        print(ast.sql(pretty=True))

    except ParseError as e:
        print(f"\n❌ SQL PARSE ERROR:")
        print(e)
        print("Suggestion: Check the syntax in your 'query.txt' file, especially near the highlighted area.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")


# --- Main Execution ---

if __name__ == "__main__":
    SQL_FILE = "query.txt"
    
    try:
        sql_content = read_sql_query(SQL_FILE)
        parse_and_analyze_sql(sql_content)
        
    except FileNotFoundError as e:
        print(e)