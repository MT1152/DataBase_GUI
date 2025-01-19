import tkinter as tk
from tkinter import messagebox, scrolledtext
from tkinter import ttk
from ttkthemes import ThemedTk
import pyodbc
import networkx as nx
import matplotlib.pyplot as plt
from PIL import Image, ImageTk


# Database connection setup
def connect_to_database():
    try:
        conn = pyodbc.connect(
            "Driver={ODBC Driver 17 for SQL Server};"
            "Server=DESKTOP-0FC6DM3\SQLEXPRESS;"   #change the name of the server 
            "Database=universty;" # change the name of the database 
            "Trusted_Connection=yes;"
        )
        return conn
    except pyodbc.Error as e:
        messagebox.showerror("Database Error", f"Error connecting to database: {e}")
        return None


def get_schema_and_relationships():
    conn = connect_to_database()
    if conn is None:
        return None, None
    
    schema = {}
    foreign_keys = []
    
    try:
        cursor = conn.cursor()

        # Fetch table names
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE'")
        tables = cursor.fetchall()
        
        # Get columns for each table
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}'")
            columns = cursor.fetchall()
            schema[table_name] = [col[0] for col in columns]

        # Get foreign key relationships
        cursor.execute("""
            SELECT 
                fk.name AS fk_name,
                tp.name AS primary_table,
                ref.name AS referenced_table
            FROM 
                sys.foreign_keys AS fk
                INNER JOIN sys.tables AS tp ON fk.referenced_object_id = tp.object_id
                INNER JOIN sys.tables AS ref ON fk.parent_object_id = ref.object_id
        """)
        foreign_keys = cursor.fetchall()

    except pyodbc.Error as e:
        messagebox.showerror("Error", f"Error fetching schema: {e}")
    
    finally:
        cursor.close()
        conn.close()
    
    return schema, foreign_keys

# Generate ERD using NetworkX with node types
def generate_erd(schema, foreign_keys):
    G = nx.DiGraph()  

    # Add nodes (tables)
    for table in schema:
        G.add_node(table, label=f"{table}\n({len(schema[table])} columns)", color="skyblue", size=1000)

    # Add edges (foreign key relationships)
    for fk in foreign_keys:
        G.add_edge(fk[1], fk[2], label=fk[0], color="gray", width=2)  # Add relationship labels to edges

    return G
def plot_erd(G):
    # Layout for nodes
    pos = nx.spring_layout(G, seed=42, k=1)  # Adjusting 'k' for better spacing

    # Create the figure and axis
    fig, ax = plt.subplots(figsize=(10, 7))

    # Draw nodes with labels
    node_colors = [G.nodes[node].get('color', 'skyblue') for node in G.nodes]
    node_sizes = [G.nodes[node].get('size', 1000) for node in G.nodes]

    nx.draw(
        G,
        pos,
        with_labels=True,
        node_size=node_sizes,
        node_color=node_colors,
        font_size=7 ,
        font_weight="bold",
        edge_color=[G[u][v].get('color', 'gray') for u, v in G.edges],
        width=[G[u][v].get('width', 4) for u, v in G.edges],
        arrows=True,
        ax=ax,
    )

    # Add edge labels (foreign key relationships)
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=5, font_color='red')

    # Set title and remove axis
    plt.title("Entity-Relationship Diagram", fontsize=16)
    plt.axis('off')
    plt.tight_layout()

    # Save the diagram to an image file
    plt.savefig("erd_diagram.png", format="PNG")
    plt.close(fig)

# Function to execute SQL queries
def execute_sql():
    queries = query_text.get("1.0", tk.END).strip()

    if not queries:
        messagebox.showerror("Error", "Query cannot be empty!")
        return

    # Split queries by semicolon, ignore empty queries
    query_list = [q.strip() for q in queries.split(';') if q.strip()]

    if not query_list:
        messagebox.showerror("Error", "No valid queries found!")
        return

    conn = connect_to_database()
    if conn is None:
        return

    try:
        cursor = conn.cursor()

        # Execute each query
        for query in query_list:
            try:
                cursor.execute(query)

                # If the query is SELECT, fetch and display results
                if query.lower().startswith("select"):
                    results = cursor.fetchall()
                    columns = [column[0] for column in cursor.description]  # Get column names

                    # Display column headers and results
                    output_text.insert(tk.END, f"\n{' | '.join(columns)}\n")
                    output_text.insert(tk.END, "-" * 50 + "\n")

                    for row in results:
                        output_text.insert(tk.END, f"{' | '.join(map(str, row))}\n")
                else:
                    conn.commit()  # For non-SELECT queries
                    output_text.insert(tk.END, f"\nQuery executed successfully.\n")

            except pyodbc.Error as e:
                output_text.insert(tk.END, f"Error in query: {query}\n{e}\n")
                continue  # Continue to the next query even if the current one fails

    except pyodbc.Error as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
    finally:
        cursor.close()
        conn.close()


# Function to display ERD in the GUI
def display_erd_in_gui():
    schema, foreign_keys = get_schema_and_relationships()
    
    if not schema:
        messagebox.showerror("Error", "Failed to fetch schema information.")
        return

    # Generate the ERD
    G = generate_erd(schema, foreign_keys)

    # Plot and save the diagram as an image
    plot_erd(G)

    # Open the image using PIL and display it in Tkinter
    img = Image.open("erd_diagram.png")
    img = ImageTk.PhotoImage(img)

    # Create a Tkinter window to display the ERD
    erd_window = tk.Toplevel(root)
    erd_window.title("Entity-Relationship Diagram")

    # Display the image in the new window
    label = ttk.Label(erd_window, image=img)
    label.image = img  # Keep a reference to the image
    label.pack(padx=10, pady=10)


## GUI Setup
root = ThemedTk()  # Use ThemedTk instead of tk.Tk
root.title("SQL Executor and ERD Generator")
root.geometry("700x700")

# Set the theme
root.set_theme("radiance")  # Ensure the theme name is valid

# Frame for the query input area
input_frame = ttk.Frame(root)
input_frame.pack(pady=10, padx=20, fill=tk.X)
style = ttk.Style()
style.configure("Custom.TLabel", font=("Arial", 14), foreground="black")
ttk.Label(input_frame, text="Enter SQL Query:", style="Custom.TLabel").pack(pady=5)

# Scrollable text widget for SQL input
query_text = scrolledtext.ScrolledText(input_frame, width=70, height=8, font=("Arial", 12))
query_text.pack(pady=5)

# Frame for the execute button
button_frame = ttk.Frame(root)
button_frame.pack(pady=10)

# Execute button with custom styling
style.configure("Custom.TButton", font=("Arial", 14), foreground="dark blue", background="lightgray")
execute_button = ttk.Button(button_frame, text="Execute", command=execute_sql, 
                             style="Custom.TButton", width=20)
execute_button.pack()

# Frame for output display area
style = ttk.Style()
style.configure("Output.TLabel", font=("Arial", 14), foreground="black")  

output_frame = ttk.Frame(root)
output_frame.pack(pady=20, padx=20, fill=tk.X)


ttk.Label(output_frame, text="Output:", style="Output.TLabel").pack(pady=5)


output_text = scrolledtext.ScrolledText(output_frame, width=70, height=10, font=("Arial", 12))
output_text.pack(pady=5)

# Button to generate ERD
display_erd_button = ttk.Button(root, text="Show ERD", command=display_erd_in_gui, style="Custom.TButton", width=20)
display_erd_button.pack(pady=20)

# Run the application
root.mainloop()