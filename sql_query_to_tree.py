import sqlglot
from sqlglot.expressions import Select, From, Where, Column, Literal, Binary, Join

# --- 2. CORE LOGIC: Parsing and Tree Generation ---

def read_sql_file(file_path):
    """Reads the SQL query from the text file."""
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"❌ Error: File not found at {file_path}")
        return None

def parse_sql_to_ast(sql_query):
    """Parses the SQL query using sqlglot and returns the AST."""
    try:
        expression = sqlglot.parse_one(sql_query)
        return expression
    except sqlglot.errors.ParseError as e:
        print(f"❌ SQL Parsing Error: {e}")
        return None

def output_relational_tree(expression, indent=0):
    """
    Recursively traverses the AST and prints a Relational Algebra-style Query Tree.
    This demonstrates the logical sequence of operations (bottom-up: FROM -> JOIN -> WHERE -> SELECT).
    """
    indent_str = "    " * indent
    
    if isinstance(expression, Select):
        # 1. Start with the FROM clause (The base relation(s))
        from_clause = expression.find(From)
        
        # This function is written to handle the top-level SELECT only
        if not from_clause:
            print(f"{indent_str}**[ERROR]** Could not find FROM clause.")
            return

        # 2. Extract and recursively process the source relations (including JOINs)
        source = from_clause.this
        
        # The base of the tree is the result of the JOIN/FROM operation
        print(f"{indent_str}**[Source]**")
        process_join_or_table(source, indent + 1)
        
        # 3. Find the Selection Operation (WHERE clause)
        where_clause = expression.find(Where)
        if where_clause:
            print(f"{indent_str}    |")
            # sigma (Selection)
            print(f"{indent_str}    └─ **[Selection: \u03C3]** Condition: {where_clause.this.sql()}") 
            indent += 1 # Push indent for the next operation
            
        # 4. Find the Projection Operation (SELECT list)
        projection = expression.expressions
        projection_list = ", ".join(e.sql() for e in projection)
        print(f"{indent_str}    |")
        # pi (Projection)
        print(f"{indent_str}    └─ **[Projection: \u03C0]** Columns: {projection_list}")
        
        # 5. Handle ORDER BY
        if expression.args.get('order'):
             order_by = ", ".join(e.sql() for e in expression.args['order'])
             print(f"{indent_str}        |")
             # tau (Sort)
             print(f"{indent_str}        └─ **[Sort: \u03C4]** By: {order_by}")

def process_join_or_table(expression, indent):
    """Handles the recursive display of JOINS and base tables."""
    indent_str = "    " * indent
    
    if isinstance(expression, Join):
        # Process the right side of the JOIN first
        process_join_or_table(expression.this, indent + 1)

        # Print the Join operator (bowtie symbol)
        join_type = expression.args.get("kind", "").upper()
        join_condition = expression.args.get("on").sql() if expression.args.get("on") else "TRUE"
        print(f"{indent_str}**[Join: \u22C8]** Type: {join_type} | On: {join_condition}")
        
        # Process the left side of the JOIN
        process_join_or_table(expression.args["on"].this if expression.args.get("on") else expression.this, indent + 1)

    elif isinstance(expression, Select):
        # Handle Subqueries (nested Selects)
        print(f"{indent_str}**[Subquery]** (See nested tree)")
        output_relational_tree(expression, indent + 1)

    elif hasattr(expression, 'this') and expression.this:
        # This is a base Table/Identifier
        alias = expression.alias_or_name or expression.this.name
        print(f"{indent_str}**[Relation]** {expression.this.name} AS {alias}")
    else:
        # Fallback for unexpected relation type
        print(f"{indent_str}**[Relation]** Unknown Source Type: {expression.sql()}")


# --- 3. EXECUTION ---

if __name__ == "__main__":
    file_path = "query.txt"

    # Read the query
    sql_to_parse = read_sql_file(file_path)

    if sql_to_parse:
        # Parse the query
        ast_root = parse_sql_to_ast(sql_to_parse)
        
        if ast_root:
            print("\n" * 2)
            print("--- Relational Algebra Query Tree (Execution Order: Bottom-Up) ---")
            output_relational_tree(ast_root)
            print("\n" * 2)