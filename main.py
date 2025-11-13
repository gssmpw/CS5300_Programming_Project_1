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


# Used to find the projecitons for the canonical query tree 
def find_projection(expression):
    select_clauses = expression.find_all(exp.Select)
    projections = []

    # Iterate through the found Select expressions (there should typically be one for a single query)
    for select_clause in select_clauses:
        # You can access the expressions within the SELECT clause
        for projection in select_clause.expressions:
            projections.append(projection.sql())
    
    return projections


# Used to parse out all the tables needed to be joined in the query tree
def find_tables(expression):
    tables = []

    # Find all Table use in the original SQL query
    for table in expression.find_all(exp.Table):
        tables.append(table.sql())
    
    return tables


# Takes two arrays one containing the entire expresion minus the from clause
# and one containing the from clause. Then returns a canoncical query tree.
def build_canonical(expresion, from_clause):
    tree = []

    # handles the expression
    for i in expresion:
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
def print_tree(tree):
    for i in range(len(tree)):
        if i == 0:
            print(tree[0].data)
            print("   ", tree[0].children[0].data)
        elif i + 2 < len(tree):
            for j in range(len(tree[i].children)):
                print("   "*(i + 1), tree[i].children[j].data)
        else:
            for j in range(len(tree[i].children)):
                print("   "*(i + 1), tree[i].children[j].data)
    return



def main():
    with open("query.txt", "r") as file:
        query = file.read()
    
    expression = sqlglot.parse_one(query)
    starting_arr = [expression.find(exp.Order), find_projection(expression), expression.find(exp.Having), expression.find(exp.Group), expression.find(exp.Where)]
    tables = find_tables(expression)

    tree = build_canonical(starting_arr, tables)

    print_tree(tree)

    return

if __name__ == "__main__":
    main()