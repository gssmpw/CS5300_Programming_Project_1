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


    # Merge selections and cartesians into joins
    create_joins(tree[0])
    print("----HEURISTIC 4: Replace Cartesian + Selection----")
    print_tree(tree[0], 0)
    print("--------------------------------------------------\n")


    # Add projection throughout the query tree

    return

if __name__ == "__main__":
    main()