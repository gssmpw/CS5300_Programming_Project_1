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
def find_common_cartesian(node1, node2):
    cart1 = node1
    cart2 = node2

    if cart1.data == "X" and cart2.data == "X":
        print('1', cart1.data, cart2.data)
        if cart1 == cart2:
            return cart1, cart2
    elif cart1.data == "X" or "SELECT" in str(cart1.data):
        print('2', cart1.data, cart2.data)
        cart1, cart2 = find_common_cartesian(cart1.parent, cart2)
    elif cart2.data == "X" or "SELECT" in str(cart2.data):
        print('3', cart1.data, cart2.data)
        cart1, cart2 = find_common_cartesian(cart1, cart2.parent)

    '''elif cart1.data == "X" and cart2.data != "X":
        cart1, cart2 = find_common_cartesian(cart1, cart2.parent)
    elif cart1.data != "X" and cart2.data == "X":
        cart1, cart2 = find_common_cartesian(cart1.parent, cart2)
    else:
        cart1, cart2 = find_common_cartesian(cart1.parent, cart2.parent)'''
    
    print('4', cart1.data, cart2.data)
    
    return cart1, cart2


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
            # IN PROGRESS
            if select[0][0].isupper and select[0][1] == '.' and select[2][0].isupper and select[2][1] == '.':
                table1 = leaf_nodes[1].parent
                table2 = leaf_nodes[2].parent
                cart_node = find_common_cartesian(table1, table2)[0]
                sel_node = Node("SELECT" + i)
                sel_node.insert_node(cart_node.parent, cart_node)

            # Handles selections involving a singele table
            else:
                for j in leaf_nodes:
                    if j.data[-1] == select[0][0]:
                        sel_node = Node("SELECT" + i)
                        sel_node.insert_node(j.parent, j)

    return


def main():
    with open("query.txt", "r") as file:
        query = file.read()
    
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
    print("--------HEURISTIC 2: PUSH SELECTIONS DOWN---------")
    print_tree(tree[0], 0)
    print("--------------------------------------------------\n")

    return

if __name__ == "__main__":
    main()