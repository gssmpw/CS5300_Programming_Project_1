import sys

#Class to create a node for the query tree
class query_tree_node:
    def __init__(self, x):
        self.data = [x]
        self.children = []

#add a child to an existing parent in the query tree
def add_child(parent, child):
    parent.children.append(child)

def main():
    with open("input.txt", "r") as file:
        query = file.read().split()

        root = query_tree_node(query[0])
        node1 = query_tree_node(query[1])
        add_child(root, node1)
        
        print(root.data, root.children[0].data)

    return

if __name__ == "__main__":
    main()