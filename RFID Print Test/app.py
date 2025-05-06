from dash import Dash, html, dcc, Input, Output, State, ctx
import socket
import MqttSubscribe
import json
import pandas as pd
import base64
import dash
from dash import dash_table, html

MqttSubscribe.start_mqtt_thread()
# Initialize the app
app = Dash(__name__)

PRINTER_IP = 'Vignesh-cs437'
PORT = 9100
ZPL_LABEL = "^XA^FO100,100^A0N,30,30^FDHello, ZPL!^FS^XZ"

file_path = './assets/ZPL.txt'
# Function to decode EPC
def decode_epc(epc_base64):
    decoded_bytes = base64.b64decode(epc_base64)
    return decoded_bytes.decode('utf-8')

def extract_json_objects(string_array):
    mqtt_lines = []
    for s in string_array:
        try:
            obj = json.loads(s)
            mqtt_lines.append(obj)
        except (ValueError, TypeError):
            continue
    return mqtt_lines


def getDF_From_MQTT(mqtt_lines):
    epc_table = {}
    for line in mqtt_lines:
        data = line
        tag_event = data["tagInventoryEvent"]
        epc_base64 = tag_event["epc"]
        epc_actual = decode_epc(epc_base64)
        timestamp = data["timestamp"]
        # If EPC already exists, update timestamp; else add new
        if epc_actual in epc_table:
            epc_table[epc_actual]["timestamp"] = timestamp
        else:
            # Copy all relevant fields and add the decoded EPC
            entry = tag_event.copy()
            entry["timestamp"] = timestamp
            entry["epc_actual"] = epc_actual            
            parts = epc_actual.split('&&')
            if len(parts) == 2:
                entry["part"]=parts[0]
                entry["qty"] = parts[1]
            epc_table[epc_actual] = entry

    # Convert to DataFrame for a table view
    df = pd.DataFrame(epc_table.values())
    return df


try:
    with open(file_path, 'r') as file:
        ZPL_LABEL = file.read()
except FileNotFoundError:
    ZPL_LABEL = None

# App layout
app.layout = html.Div([
    html.H1("Inventory Management System", style={'textAlign': 'center'}),
    
    # Container for icons
    html.Div([
        # Print Labels Icon
        html.Div([
            html.Img(src='/assets/Label_Print.png', style={'width': '100px', 'height': '100px'}),
            html.P("Print Labels")
        ], className="container", id='print-icon'),
        
        # View Inventory Icon
        html.Div([
            html.Img(src='/assets/view_inventory.png', style={'width': '100px', 'height': '100px'}),
            html.P("View Inventory", style={'textAlign': 'center'})
        ], className="container", id='View-icon')
    ], style={'textAlign': 'center'}),
    
    # Modal structure (hidden by default)
   html.Div(
    id='modal',
    children=[
        html.Div(
            children=[
                html.H2("Enter Details", style={'textAlign': 'center', 'marginBottom': '20px'}),
                html.Div([
                    html.Label("Part Number:", style={'text-align': 'left','width':'150px','marginRight': '10px', 'fontWeight': 'bold'}),
                    dcc.Input(
                        id='part-number', 
                        type='text', 
                        placeholder='Enter Part Number', 
                        style={                            
                            'padding': '2px', 
                            'marginBottom': '5px'
                            ,'width':'200px'
                        }
                    ),
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px'}),
                
                html.Div([
                    html.Label("Quantity:", style={'text-align': 'left','width':'150px','marginRight': '10px', 'fontWeight': 'bold'}),
                    dcc.Input(
                        id='quantity', 
                        type='number', 
                        placeholder='Enter Quantity', 
                        style={
                            'width':'200px', 
                            'padding': '5px', 
                            'marginBottom': '20px'
                        }
                    ),
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px'}),
                
                html.Div([
                    html.Button("Submit", id='submit-button', className="button"),
                    html.Button("Close", id='close-button', className="button")
                ], style={'textAlign': 'center'})
            ],
            style={
                'backgroundColor': '#fff',
                'padding': '20px',
                'borderRadius': '10px',
                'width': '450px',
                'boxShadow': '0 4px 8px rgba(0, 0, 0, 0.2)',
                'textAlign': 'center'
            }
        )
    ],
    style={
        'display': 'none',  # Hidden by default
        'position': 'fixed',
        'top': 0,
        'left': 0,
        'width': '100%',
        'height': '100%',
        'backgroundColor': 'rgba(0, 0, 0, 0.5)',
        'justifyContent': 'center',
        'alignItems': 'center',
        'zIndex': 1000
    }
),

    
    # Status message
    html.Div(id='status-message', style={'textAlign': 'center', 'marginTop': '20px'})
])

app.layout.children.append(
    dcc.Interval(id='interval-component', interval=800, n_intervals=0)
)

app.layout.children.append(
    html.Div([
    html.Div(id="header",children=[html.H1("Live Inventory")
                                   ,html.Button("Clear", id='clear-button', className="button")
                                   ], style={'textAlign': 'center', 'marginTop': '20px','display':'none'}),
    html.Div(id='inventory-display', style={'textAlign': 'center', 'marginTop': '20px','display':'none','justify-content': 'center'})]
    ,style={'textAlign': 'center', 'marginTop': '20px'})
)

@app.callback(
    Output('inventory-display', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_inventory_display(n):
    #messages = []   
    mqtt_lines = extract_json_objects(MqttSubscribe.MessageStore.MESSAGES)
    df = getDF_From_MQTT(mqtt_lines)
    return html.Div([
    dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in df.columns]
    )])

@app.callback(
    Output('inventory-display', 'children',allow_duplicate=True),
    Input('clear-button', 'n_clicks'),
    prevent_initial_call=True
)
def Clear(n):
    MqttSubscribe.MessageStore.MESSAGES.clear()
    return html.Pre('Loading....')
    
    
@app.callback(
    [Output('inventory-display', 'style'),
     Output('header', 'style')],
    [Input('View-icon', 'n_clicks')
     ,Input('inventory-display', 'style')
     ,Input('header', 'style')]
)
def DisplayTagsRead(n,current_style,h_style):
    #messages = []
    if not n :
        return current_style,h_style
    return {**current_style,"display":"inline"},{**h_style,"display":"inline"}

# Callback to toggle modal visibility
@app.callback(
    Output('modal', 'style'),
    [Input('print-icon', 'n_clicks'), Input('close-button', 'n_clicks')],
    [State('modal', 'style')]
)
def toggle_modal(print_clicks, close_clicks, current_style):
    if not print_clicks and not close_clicks:
        return current_style
    
    if ctx.triggered_id == "print-icon":
        return {**current_style, "display": "flex"}  # Show modal
    
    if ctx.triggered_id == "close-button":
        return {**current_style, "display": "none"}  # Hide modal
    
    return current_style

# Callback to handle submission
@app.callback(
    [Output('modal', 'style',allow_duplicate=True), Output('status-message', 'children')],
    Input('submit-button', 'n_clicks'),
    [State('part-number', 'value'), State('quantity', 'value'),State('modal', 'style')],
    prevent_initial_call=True
)
def handle_submit(n_clicks, part_number, quantity,current_style):
    if n_clicks:
        try:
        # Create TCP socket connection
            new_ZPL_LABEL = ZPL_LABEL.replace("#Part#",part_number)
            new_ZPL_LABEL = new_ZPL_LABEL.replace("#Qty#",str(quantity))
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((PRINTER_IP, PORT))
                sock.sendall(new_ZPL_LABEL.encode('ASCII'))
            
            return {**current_style, "display": "none"},html.Div("Label sent successfully to printer!", 
                       style={'color': 'green', 'textAlign': 'center'})
    
        except Exception as e:
            return {**current_style, "display": "none"},html.Div(f"Print error: {str(e)}", 
                       style={'color': 'red', 'textAlign': 'center'})
    return ""

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
