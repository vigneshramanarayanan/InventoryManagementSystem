import paho.mqtt.client as mqtt
import threading
import queue

MQTT_BROKER = '192.168.86.39'
MQTT_PORT = 1883
MQTT_TOPIC = 'inventory/updates'
MQTT_USERNAME = 'RFID'
MQTT_PASSWORD = 'rfid'

mqtt_message_queue = queue.Queue()

class MessageStore:
    MESSAGES = []

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Failed to connect, return code {reason_code}")

def on_message(client, userdata, msg):
    MessageStore.MESSAGES.append(msg.payload.decode())

def start_mqtt_thread():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="your_client_id")
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    thread = threading.Thread(target=client.loop_forever, daemon=True)
    thread.start()

# Export the queue for use in Dash
