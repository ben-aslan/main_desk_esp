import machine
import network
import time
from machine import Pin
from umqtt.simple import MQTTClient

from config import load_config, save_config

config = load_config()

SSID = config['ssid']
PASSWORD = config['password']

MQTT_BROKER = config["host"]
MQTT_PORT = config["port"]
MQTT_USERNAME = config["mqtt_username"]
MQTT_PASSWORD = config["mqtt_password"]
MQTT_CLIENT_ID = config["client_id"]
MQTT_TOPIC_SUB = b"s"

led = Pin(2, Pin.OUT)

led.value(1)

chandelier = Pin(16, Pin.OUT)

chandelier.value(0)

chandelier_state = False

button = Pin(5, Pin.PULL_UP)

last_press = 0


def button_irq(pin):
    global chandelier_state, last_press
    now = time.ticks_ms()
    if time.ticks_diff(now, last_press) > 500:
        chandelier_state = not chandelier_state
        chandelier.value(chandelier_state)
        print("chandelier toggled:", chandelier_state)
        last_press = now


button.irq(trigger=Pin.IRQ_FALLING, handler=button_irq)

error_led = Pin(0, Pin.OUT)

error_led.value(0)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)


def connect_wifi():
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(SSID, PASSWORD)
        retries = 0
        while not wlan.isconnected():
            time.sleep(0.5)
            retries += 1
            if retries > 20:
                error_led.value(1)
                print("Retrying Wi-Fi...")
                wlan.disconnect()
                wlan.connect(SSID, PASSWORD)
                retries = 0
        error_led.value(0)
    print("Wi-Fi connected:", wlan.ifconfig())


def handle_lamp(msg):
    if msg == b"1":
        chandelier.value(1)
    else:
        chandelier.value(0)
    print("lamp:", msg.decode())


topic_handlers = {
    b"chandelier": handle_lamp,
}


def mqtt_callback(topic, msg):
    led.value(0)
    print(f"Received: {msg.decode()} on topic {topic.decode()}")
    handler = topic_handlers.get(topic)
    if handler:
        handler(msg)
    led.value(1)


connect_wifi()
client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, MQTT_PORT,
                    MQTT_USERNAME, MQTT_PASSWORD)
client.set_callback(mqtt_callback)


def connect_mqtt():
    error_led.value(1)
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, MQTT_PORT,
                        MQTT_USERNAME, MQTT_PASSWORD)
    client.set_callback(mqtt_callback)
    while True:
        try:
            client.connect()
            print("✅ Connected to MQTT broker")
            error_led.value(0)
            break
        except Exception as e:
            print("❌ Failed to connect. Retrying in 10s...", e)
            time.sleep(10)
    for tp in topic_handlers:
        client.subscribe(tp)
        print(f"Subscribed to {tp.decode()}")
    return client


while True:
    try:
        client.connect()
        print("✅ Connected to MQTT broker")
        break
    except Exception as e:
        print("❌ Failed to connect. Retrying in 10s...", e)
        time.sleep(10)

for tp in topic_handlers:
    client.subscribe(tp)
    print(f"Subscribed to {tp.decode()}")

while True:
    if not wlan.isconnected():
        print("Wi-Fi disconnected. Reconnecting...")
        connect_wifi()
        try:
            client.disconnect()
        except:
            pass
        client = connect_mqtt()

    try:
        client.check_msg()
    except Exception as e:
        print("MQTT error, reconnecting...", e)
        try:
            client.disconnect()
        except:
            pass
        client = connect_mqtt()

    time.sleep(0.1)
