import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import os
from dash.dash_table import DataTable
from gather import gather, summarize

app = dash.Dash(__name__, suppress_callback_exceptions=True)

# Directory where the app outputs files
OUTPUT_DIR = "./sragent_output"

# Ensure the output directory exists
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Function to list files in the output directory
def list_files():
    return os.listdir(OUTPUT_DIR)

# Layout of the Dash app
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),  # Track URL changes

    # Sidebar
    html.Div([
        
        # Form to input project ID or upload a text file
        html.H3("Fetch Metadata"),
        dcc.Input(id='project-id', type='text', placeholder="BioProject ID", style={'margin-bottom': '10px', 'width': '100%'}),
        #dcc.Upload(
        #    id='upload-data',
        #    children=html.Div(['Drag and Drop or ', html.A('Select a Text File of Project IDs')]),
        #    style={
        #        'width': '100%', 'height': '60px', 'lineHeight': '60px',
        #        'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
        #        'textAlign': 'center', 'margin-bottom': '10px'
        #    },
        #    multiple=False
        #),
        html.Button("gather()", id='gather-button', n_clicks = 0, style={'margin-bottom': '10px'}),
        

        # Control for summarizing specific or all projects after gathering
        html.Hr(),
        html.H3("Summarize"),
        dcc.Dropdown(
            id='summary-type',
            options=[
                {'label': 'Summarize Specific Project(s)', 'value': 'specific'},
                {'label': 'Summarize All Projects', 'value': 'all'}
            ],
            value='specific',  # Default selection
            style={'margin-bottom': '10px'}
        ),
        html.Button("Summarize Metadata", id='summarize-button'),
        html.Div(id='summary-output'),

        html.Hr(),

        html.H3("Output Files"),
        html.Div(id='file-list'),  # This will display the list of files as links
        html.Button("Reload File List", id='reload-button', style={'margin-top': '20px'}),

    ], style={'width': '20%', 'float': 'left', 'padding': '20px', 'border-right': '1px solid lightgrey'}),

    # Main content area for viewing and editing files
    html.Div([
        html.Div(id='file-content', style={'whiteSpace': 'pre-wrap'}),
        html.Div(id='file-editor'),
        
#        html.Div(id = 'log-div', style=dict(height='300px',overlfow='auto')),

    ], style={'width': '75%', 'float': 'right', 'padding': '20px'}),

        # Store component to hold gathered data
    dcc.Store(id='gather_output')  # Add this line to store data
])

# Helper function to parse uploaded file
def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    return decoded.decode('utf-8').splitlines()

# Callback to reload the list of files and display them as clickable links
@app.callback(
    Output('file-list', 'children'),
    [Input('reload-button', 'n_clicks')]
)
def reload_file_list(n_clicks):
    files = list_files()
    return [
        html.A(file, href=f"/view/{file}", style={'display': 'block', 'margin-bottom': '10px'}) for file in files
    ]

# Callback to display the selected file content and provide editing options
@app.callback(
    [Output('file-content', 'children'),
     Output('file-editor', 'children')],
    [Input('url', 'pathname'), Input('gather_output','data')]
)
def display_file(pathname, gather_data):
    if gather_data:
        # If there's gathered data (a DataFrame), display it as a table
        df = pd.DataFrame(gather_data)

        table = DataTable(
            id='dataframe-table',
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
            editable=False,
            style_table={'height': '500px', 'width': '80%', 'margin': 'auto', 'overflowY': 'auto'},  # Set table height with vertical scroll
            style_cell={'textAlign': 'left', 'minWidth': '150px', 'width': '150px', 'maxWidth': '150px'},  # Adjust cell width
        )
        return "metadata", table

    if not pathname or not pathname.startswith("/view/"):
        return "Select a file to view its contents.", ""

    # Extract the file name from the URL
    file_name = pathname.split("/view/")[1]
    file_path = os.path.join(OUTPUT_DIR, file_name)

    # Handle CSV and Excel files by displaying them as interactive DataTables
    if file_name.endswith('.csv'):
        df = pd.read_csv(file_path)

        # Create a DataTable for the CSV file with scrollable content
        table = DataTable(
            id='dataframe-table',
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
            editable=False,
            style_table={'height': '500px','width':'80%','margin':'auto', 'overflowY': 'auto'},  # Set table height with vertical scroll
            style_cell={'textAlign': 'left', 'minWidth': '150px', 'width': '150px', 'maxWidth': '150px'},  # Adjust cell width
        )
        return f"{file_name}", table

    # Handle text files
    elif file_name.endswith('.txt'):
        with open(file_path, 'r') as file:
            content = file.read()
        editor = dcc.Textarea(
            id='text-editor',
            value=content,
            style={'width': '100%', 'height': '400px'}
        )
        return f"### {file_name}\n\n{content}", editor

    return "Unsupported file type.", ""

# Callback to gather metadata based on project ID, list, or uploaded file
@app.callback(
#    Output('app-log','children', allow_duplicate=True),
    Output('gather_output', 'data'),
#    [Input('gather-button', 'n_clicks'), Input('upload-data', 'contents')],
#    [State('project-id', 'value'), State('upload-data', 'filename')]
    [Input('gather-button', 'n_clicks')],
    [State('project-id', 'value')]
)
def gather_metadata(n_clicks, project_id):
    if not n_clicks:
        return ""

    # Gather metadata based on typed project IDs
    if project_id:
        project_ids = [p.strip() for p in project_id.split(',')]
    #elif contents:
    #    project_ids = parse_contents(contents, filename)
    else:
        return "Please provide project ID(s) or upload a file."

    try:
        gathered_data = ""
        for pid in project_ids:
            gather_output = gather(pid)

        return gather_output.to_dict('records')

    except Exception as e:
        return f"Error gathering metadata: {str(e)}"

## Callback to summarize the gathered metadata for specific or all projects
#@app.callback(
#    Output('summary-output', 'children'),
#    [Input('summarize-button', 'n_clicks')],
#    [State('summary-type', 'value'), State('project-id', 'value')]
#)
#$def summarize_metadata(n_clicks, summary_type, project_id):
#$    if not n_clicks:
#$        return ""

    #if summary_type == 'specific' and project_id:
    #    project_ids = [p.strip() for p in project_id.split(',')]
    #    all_summaries = ""
    #    for pid in project_ids:
    #        try:
    #            #metadata = gather(pid)
    #            summary = summarize(metadata)
    #            all_summaries += f"Summary of project {pid}:\n{summary}\n\n"
    #        except Exception as e:
    #            all_summaries += f"Error summarizing project {pid}: {str(e)}\n"
    #    return all_summaries

    #elif summary_type == 'all':
    #    try:
    #        all_summaries = ""
    #        for project_id in list_files():  # Assuming list_files() returns project IDs or files related to projects
    #            metadata = gather(project_id)
    #            summary = summarize(metadata)
    #            all_summaries += f"Summary of project {project_id}:\n{summary}\n\n"
    #        return all_summaries
    #    except Exception as e:
    #        return f"Error fetching metadata: {str(e)}"
    #else:
    #    return "Please provide project ID(s) or select a valid option."

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)
