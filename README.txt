Compilation & Execution Instructions
The only command needed to run the program is "python main.py".
For this project we used sqlglot for out parser. To install this tool,
run "pip install sqlglot" in your command line.

Input Requirements
Input for this program is accepted as a text file with the schema and SQL query.
The schema must be placed before the query, and both must include a header labled 
-- Schema Definitions -- and -- SQL Query --

Output Description
The output for this program will show in the console.
The output shows each node of the query tree printed on separate lines.
Each level of the tree is indicated by an indent. If two nodes are have the same
number of indents, this means that they are on the same level of the tree.
A nodes child/children will always be indented one more level than the parent.