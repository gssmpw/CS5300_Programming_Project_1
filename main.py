import sqlglot
import sqlglot.expressions as exp


# Tree node logic
class Node:
    # Create tree node
    def __init__(self, data):
        self.data = data
        self.parent = None
        self.children = []
        return

    # Append a child node to a parent node
    def add_child(self, child_node):
        if child_node not in self.children:
            self.children.append(child_node)
            child_node.parent = self
        return

    # Removes a child from the parent's child array
    def remove_child(self, child_node):
        if child_node in self.children:
            self.children.remove(child_node)
            child_node.parent = None
        return
    
    # Inserts the node into the tree
    def insert_node(self, parent_node, child_node):
        parent_node.remove_child(child_node)
        parent_node.add_child(self)
        self.add_child(child_node)
        return


# Used to find the projecitons for the canonical query tree 
def find_projection(expression):
    select_clauses = expression.find_all(exp.Select)
    projections = []

    projections.append("PROJECTION")

    # Iterate through the found Select expressions (there should typically be one for a single query)
    for select_clause in select_clauses:
        # You can access the expressions within the SELECT clause
        for projection in select_clause.expressions:
            projections.append(projection.sql())
    
    projections = " ".join(projections)

    return projections


# Used to parse out all the tables needed to be joined in the query tree
def find_tables(expression):
    tables = []

    # Find all Table use in the original SQL query
    for table in expression.find_all(exp.Table):
        tables.append(table.sql())
    
    return tables


# Takes two arrays one containing the entire expression minus the from clause
# and one containing the from clause. Then returns a canonicical query tree.
def build_canonical(expression, from_clause):
    tree = []

    # handles the expression
    for i in expression:
        if "WHERE" in str(i):
            i = str(i).replace("WHERE", "SELECT")
        if i != None:
            new_node = Node(i)
            tree.append(new_node)
            
    # add cartesian
    tree.append(Node("X"))

    # handles the from clause
    for i in range(len(from_clause)):
        new_node = Node(from_clause[i])
        tree.append(new_node)

        if i + 2 < len(from_clause):
            tree.append(Node(f"X"))

    # Append the children into the tree
    i = 0
    while i < len(tree) - 2:
        if tree[i].data != "X":
            tree[i].add_child(tree[i+1])
            i += 1
        else:
            tree[i].add_child(tree[i+1])
            tree[i].add_child(tree[i+2])
            i += 2

    return tree


# Function for printing trees
def print_tree(tree_node, depth):
    if tree_node is not None:
        print("    " * depth, tree_node.data)
        if tree_node.children != []:
            for child_node in tree_node.children:
                print_tree(child_node, depth + 1)
    return


# Take in a tree and separate the conjunctive selection conditions
def cascade_selection(tree_node):
    if "SELECT" in str(tree_node.children[0].data):
        tree_node.children[0].data = str(tree_node.children[0].data).split("AND")
        tree_node.children[0].data = "SELECT".join(tree_node.children[0].data)
        return
    elif tree_node.children == []:
        return
    else:
        cascade_selection(tree_node.children[0])

    return


# Function for finding all leafs in our tree
def find_leaves(tree_node, leaf_nodes):
    if tree_node is not None:
        if tree_node.children == []:
            leaf_nodes.append(tree_node)
        else:
            for child_node in tree_node.children:
                find_leaves(child_node, leaf_nodes)
    
    return


# Takes 2 nodes and returns the cartesian product node that joins them
# IN PROGRESS
def find_common_cartesian(start, target):

    if start == target:
        return target
    elif start.data == "X" or "SELECT" in str(start.data):
        check = find_common_cartesian(start.parent, target)
        if check:
            return check
    
    return


# Take in a tree node and push down the selections to an appropiate spot
def selection_down(tree_node):
    select_statements = []
    leaf_nodes = []
    find_leaves(tree_node, leaf_nodes)

    # Find all selections that need to be pushed down
    if "SELECT" in str(tree_node.children[0].data):
        select_statements = str(tree_node.children[0].data).strip().split("SELECT")
    elif tree_node.children == []:
        return
    else:
        selection_down(tree_node.children[0])

    # Select one selection from the list of selections to be moved
    for i in select_statements:
        select = i.strip().split()
        if i != '':

            # Handles selections involving more than one table
            if select[0][0].isupper and select[0][1] == '.' and select[2][0].isupper and select[2][1] == '.':

                # Finds the two tables being joined
                node1 = leaf_nodes[0]
                node2 = leaf_nodes[0]
                for k in leaf_nodes:
                    if str(k.data)[-1] == select[0][0]:
                        node1 = k
                    elif str(k.data)[-1] == select[2][0]:
                        node2 = k

                # Find the first cartesion that is a parent of each node
                while node1.data != "X":
                    node1 = node1.parent
                while node2.data != "X":
                    node2 = node2.parent

                # Run the find common cartesian to find the place where the select should be inserted
                result1 = find_common_cartesian(node1, node2)
                result2 = find_common_cartesian(node2, node1)
                if result1:
                    sel_node = Node("SELECT" + str(i))
                    sel_node.insert_node(result1.parent, result1)
                elif result2:
                    sel_node = Node("SELECT" + str(i))
                    sel_node.insert_node(result2.parent, result2)

            # Handles selections involving a singele table
            else:
                for j in leaf_nodes:
                    if j.data[-1] == select[0][0]:
                        sel_node = Node("SELECT" + i)
                        sel_node.insert_node(j.parent, j)

    return


# Checks the tree for any cartesian and selects that need to be switched into joins and returns an updated tree
def create_joins(tree_node):
    # Check for a select condition with a cartesian child
    if tree_node is not None and "SELECT" in str(tree_node.data) and tree_node.children[0].data == "X":
        # Update the selct to a join
        tree_node.data = str(tree_node.data).replace("SELECT", "JOIN")
        cart_node = tree_node.children[0]

        # Handles removing of the cartesian node from the tree
        for i in range(len(cart_node.children)):
            tree_node.add_child(cart_node.children[i])
        tree_node.remove_child(cart_node)

        if tree_node.children != []:
            for child_node in tree_node.children:
                create_joins(child_node)

    if tree_node.children != []:
        for child_node in tree_node.children:
            create_joins(child_node)
    return

# Adds projections to the query tree in the correct places
def add_projections(tree_node, dict):
    if "PROJECTION" in str(tree_node.data):
        # 1. Start a new dictionary for projections below this node
        dict = {} 
        
        # 2. Extract projection attributes from the current PROJECTION node
        proj = str(tree_node.data).strip().split()[1:]
        
        # 3. Populate the dictionary (key=table_alias, value=attributes_to_project)
        for i in proj:
            temp = i.split('.')
            # Append the attribute to the existing string, initializing if necessary
            dict[temp[0]] = dict.setdefault(temp[0], "").strip() + " " + i 
            
        # 4. Recursively call with the new dict for the child
        # Strip to ensure the value in the dict is clean
        add_projections(tree_node.children[0], {k: v.strip() for k, v in dict.items()})
        
    elif "JOIN" in str(tree_node.data):
        # 1. Parse the JOIN condition
        join = str(tree_node.data).strip().split()
        
        att1 = join[1].split('.') 
        att2 = join[3].split('.') 
        
        table1_alias = att1[0] 
        table2_alias = att2[0] 
        
        # 2. Initialize projection dictionaries for the two children, inheriting required attributes from above (`dict`)
        proj_dict1 = {k: v for k, v in dict.items()}
        proj_dict2 = {k: v for k, v in dict.items()}

        # 3. Add the join attributes themselves to the required projections for the respective children
        # Ensure only the attribute (e.g., 'E.Essn') is added to the correct alias entry (e.g., 'E')
        # We only add the attribute if it's not already present from the parent
        if join[1] not in proj_dict1.setdefault(table1_alias, ""):
            proj_dict1[table1_alias] = proj_dict1.setdefault(table1_alias, "") + " " + join[1]
        
        if join[3] not in proj_dict2.setdefault(table2_alias, ""):
            proj_dict2[table2_alias] = proj_dict2.setdefault(table2_alias, "") + " " + join[3]


        # 4. Process children in reverse order (to avoid index issues during insertion)
        for child_node in reversed(tree_node.children):
            table_alias = None
            current_proj_dict = None
            
            # --- Logic to find the leaf table alias under the current child's subtree ---
            temp_node = child_node
            # Traverse down until a leaf (table) node is reached
            while temp_node.children:
                # If a SELECT is immediately above the table, jump over it
                if "SELECT" in str(temp_node.data) and temp_node.children:
                    temp_node = temp_node.children[0]
                else:
                    # In a JOIN/PROJECTION tree, the leftmost child often leads to the base
                    temp_node = temp_node.children[0] 
            
            # Extract the alias from the leaf node's data (e.g., 'EMPLOYEE AS E' -> 'E')
            node_data = str(temp_node.data).strip()
            if ' AS ' in node_data:
                table_alias = node_data.split(' AS ')[1].strip()
            # This is a fallback based on your original logic (e.g., last character is the alias)
            elif node_data and node_data[-1].isalpha(): 
                table_alias = node_data[-1] 

            # 5. Assign the correct projection dictionary based on the table alias
            if table_alias == table1_alias:
                current_proj_dict = proj_dict1
            elif table_alias == table2_alias:
                current_proj_dict = proj_dict2
            
            # **FIX:** Ensure current_proj_dict is not None for safety, although it should be set here
            if current_proj_dict is None:
                current_proj_dict = {} 


            # 6. Build and insert the PROJECTION node
            if table_alias in current_proj_dict:
                # Remove extra spaces and split into unique attributes
                attributes_list = current_proj_dict[table_alias].strip().split()
                # Use set to handle duplicates from the parent/join attribute
                attributes = " ".join(sorted(list(set(attributes_list))))
                
                # Check if there are attributes to project for this branch
                if attributes:
                    new_node = Node("PROJECTION " + attributes)
                    
                    # Insert the new projection node
                    new_node.insert_node(tree_node, child_node)

            # 7. Continue recursion down the tree for complex children (JOIN/PROJECTION)
            if "JOIN" in str(child_node.data) or "PROJECTION" in str(child_node.data):
                # Pass down the projection dictionary determined for this branch
                add_projections(child_node, current_proj_dict) 
    
    # 8. Base case for non-JOIN, non-PROJECTION inner nodes (like SELECT, GROUP BY, ORDER BY)
    else:
        if tree_node.children != []:
            # Pass down the projection dict for the child
            add_projections(tree_node.children[0], dict)
        
    return


def main():
    with open("input1.txt", "r") as file:
        input = file.read()
        schema, query = input.split("-- SQL Query --")
    
    expression = sqlglot.parse_one(query)
    starting_arr = [expression.find(exp.Order), find_projection(expression), expression.find(exp.Having), expression.find(exp.Group), expression.find(exp.Where)]
    tables = find_tables(expression)

    tree = build_canonical(starting_arr, tables)

    # Print the canonical query tree
    print("---------------CANONICAL QUERY TREE---------------")
    print_tree(tree[0], 0)
    print("--------------------------------------------------\n")

    # Perform the cascade of selections and print out the result
    cascade_selection(tree[0])
    print("--------HEURISTIC 1: CASCADE OF SELECTIONS--------")
    print_tree(tree[0], 0)
    print("--------------------------------------------------\n")

    # Perform the moving down of selections as low as possible
    selection_down(tree[0])
    for i in tree:
        if "SELECT" in str(i.data):
            parent = i.parent
            parent.remove_child(i)
            parent.add_child(i.children[0])
            break            
    print("--------HEURISTIC 2: PUSH SELECTIONS DOWN---------")
    print_tree(tree[0], 0)
    print("--------------------------------------------------\n")

    # SELECTIVITY
    print("-----HEURISTIC 3: Smallest Selectivity First------")
    print_tree(tree[0], 0)
    print("--------------------------------------------------\n")

    # Merge selections and cartesians into joins
    create_joins(tree[0])
    print("----HEURISTIC 4: Replace Cartesian + Selection----")
    print_tree(tree[0], 0)
    print("--------------------------------------------------\n")

    # Add projection throughout the query tree
    if "PROJECTION" not in str(tree[0].data):
        add_projections(tree[0].children[0], {})
    else:
        add_projections(tree[0], {})
    print("--------HEURISTIC 5: Push Projections Down--------")
    print_tree(tree[0], 0)
    print("--------------------------------------------------\n")

    return

if __name__ == "__main__":
    main()