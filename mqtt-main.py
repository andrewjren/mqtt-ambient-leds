import os
import threading
from threading import Thread, Event
import time
from datetime import datetime
import picamera
import ssl 
import json

from tvleds import *

import paho.mqtt.client as mqtt

# init AmbientLeds object
ambient_leds = AmbientLEDs()

# Threading Setup
threads = []
current_effect = 'Fill'

# use as signal to stop threads
stop_thread = Event() 

# report mqtt status 
def mqtt_status(client):
    global ambient_leds

    intensity = int(ambient_leds.set_intensity * 255)
    print(f"intensity: {intensity}")

    for idx in range(len(ambient_leds.light_on)):
        # On/Off 
        on_status = "ON" if ambient_leds.light_on[idx] else "OFF"
        client.publish(f"TVLeds/light_{idx+1}/status", on_status, qos=0)

        # RGB
        red, green, blue = ambient_leds.colors[idx].get_rgb()
        client.publish(f"TVLeds/light_{idx+1}/rgb/status", f"{red},{green},{blue}", qos=0)

        # Brightness
        client.publish(f"TVLeds/light_{idx+1}/brightness/status", f"{intensity}", qos=0)

# trigger thread stop
def trigger_thread_stop():
    global threads

    print('Stopping all Threads...')
    
    stop_thread.set()

    #for t in threads:
    #    t.join()
    while len(threads) > 0:
        t = threads.pop()
        t.join()

    stop_thread.clear()

# task_mood manages the calls to ambient_leds.mood()
def task_mood():
    global ambient_leds
    print('Beginning Mood Task...')
    
    # initialize mood mode
    ambient_leds.init_mood()

    # run task for mood
    while not stop_thread.is_set():
        # get current time
        start_time = datetime.now()

        # take step of mood
        ambient_leds.step_mood()

        # get time elapsed and sleep for remaining time to match period
        duration = datetime.now() - start_time
        remaining_time = ambient_leds.time_step_us - duration.microseconds

        time.sleep(remaining_time/1000000)
    
    print('Ending Mood Task...')

def task_pulse():
    global ambient_leds
    print('Beginning Pulse Task...')

    # initialize pulse mode
    ambient_leds.init_pulse()

    while not stop_thread.is_set():
        # get current time
        start_time = datetime.now()

        # take step of mood
        ambient_leds.step_pulse()

        # get time elapsed and sleep for remaining time to match period
        duration = datetime.now() - start_time
        remaining_time = ambient_leds.time_step_us - duration.microseconds

        time.sleep(remaining_time/1000000)

def task_ambient():
    global ambient_leds
    print('Beginning Ambient Task...')

    # initialize ambient mode
    #ambient_leds.init_ambient()

    with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
        camera.awb_mode='off'
        camera.awb_gains=(1.64,1.08)
        camera.start_recording(ambient_leds.camera_output, format='rgb')
        while not stop_thread.is_set():
            ambient_leds.step_ambient()

        camera.stop_recording()
        pass

def task_rainbow():
    global ambient_leds
    print('Beginning Rainbow Task...')

    while not stop_thread.is_set():
        # get current time
        start_time = datetime.now()

        # take step of mood
        ambient_leds.step_rainbow()

        # get time elapsed and sleep for remaining time to match period
        duration = datetime.now() - start_time
        remaining_time = ambient_leds.time_step_us - duration.microseconds

        time.sleep(0.001)
    

def begin_task(task):
    global threads, ambient_leds

    # Fill runs again in case another section of lights was activated
    if task == 'Fill':
        ambient_leds.fill()
        return

    print("here1")
    trigger_thread_stop()

    print("here2")
    if task == 'Off':
        ambient_leds.clear_leds()
    
    elif task == 'Mood':
        t = threading.Thread(name='Mood Thread', target=task_mood)
        t.start()
        threads.append(t)

    elif task == 'Pulse':
        t = threading.Thread(name='Pulse Thread', target=task_pulse)
        t.start()
        threads.append(t)

    elif task == 'Ambient':
        t = threading.Thread(name='Ambient Thread', target=task_ambient)
        t.start()
        threads.append(t)
    elif task == 'Rainbow':
        t = threading.Thread(name='Rainbow Thread', target=task_rainbow)
        t.start()
        threads.append(t)
    else:
        print('Task not defined!')

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    if reason_code == 0:
        print("Connection successful!")

    client.subscribe("TVLeds/light_1/switch")
    client.subscribe("TVLeds/light_2/switch")
    client.subscribe("TVLeds/light_3/switch")
    client.subscribe("TVLeds/light_4/switch")
    client.subscribe("TVLeds/light_1/brightness/set")
    client.subscribe("TVLeds/light_2/brightness/set")
    client.subscribe("TVLeds/light_3/brightness/set")
    client.subscribe("TVLeds/light_4/brightness/set")
    client.subscribe("TVLeds/light_1/rgb/set")
    client.subscribe("TVLeds/light_2/rgb/set")
    client.subscribe("TVLeds/light_3/rgb/set")
    client.subscribe("TVLeds/light_4/rgb/set")
    client.subscribe("TVLeds/light_1/effect/set")

def on_message(client, userdata, msg):
    global ambient_leds, current_effect
    print(msg.topic+" "+str(msg.payload))
    payload_str = msg.payload.decode("utf-8")

    skip_task = False

    if msg.topic == "TVLeds/light_1/switch":
        light_switch = payload_str
        if light_switch == "OFF":
            begin_task('Off')
            skip_task = True
            ambient_leds.set_light(0,False)
        elif light_switch == "ON":
            ambient_leds.set_light(0,True)

    elif msg.topic == "TVLeds/light_2/switch":
        light_switch = payload_str
        if light_switch == "OFF":
            ambient_leds.set_light(1,False)
        elif light_switch == "ON":
            ambient_leds.set_light(1,True)

    elif msg.topic == "TVLeds/light_3/switch":
        light_switch = payload_str
        if light_switch == "OFF":
            ambient_leds.set_light(2,False)
        elif light_switch == "ON":
            ambient_leds.set_light(2,True)

    elif msg.topic == "TVLeds/light_4/switch":
        light_switch = payload_str
        if light_switch == "OFF":
            ambient_leds.set_light(3,False)
        elif light_switch == "ON":
            ambient_leds.set_light(3,True)
        
        client.publish("TVLeds/light_4/status", light_switch, qos=0)

    elif (msg.topic == "TVLeds/light_1/brightness/set" or msg.topic == "TVLeds/light_2/brightness/set" or 
          msg.topic == "TVLeds/light_3/brightness/set" or msg.topic == "TVLeds/light_4/brightness/set"):
        light_brightness = int(payload_str) / 255.0 
        print(f"set brightness to {light_brightness}")
        ambient_leds.set_intensity = light_brightness

    elif msg.topic == "TVLeds/light_1/rgb/set":
        light_rgb = payload_str

        red, green, blue = [int(x) for x in light_rgb.split(',')]
        
        ambient_leds.colors[0].set(red, green, blue)

    elif msg.topic == "TVLeds/light_2/rgb/set":
        light_rgb = payload_str

        red, green, blue = [int(x) for x in light_rgb.split(',')]
        ambient_leds.colors[1].set(red, green, blue)

    elif msg.topic == "TVLeds/light_3/rgb/set":
        light_rgb = payload_str

        red, green, blue = [int(x) for x in light_rgb.split(',')]
        ambient_leds.colors[2].set(red, green, blue)

    elif msg.topic == "TVLeds/light_4/rgb/set":
        light_rgb = payload_str

        red, green, blue = [int(x) for x in light_rgb.split(',')]
        ambient_leds.colors[3].set(red, green, blue)

    elif msg.topic == "TVLeds/light_1/effect/set":
        current_effect = payload_str

    else:
        print("Unhandled Message!")
    
    # start current task
    if not skip_task:
        begin_task(current_effect)

    mqtt_status(client)


# Create MQTT Client 
with open('discovery.json') as f:
    discovery = json.load(f)
    #print(discovery)

mqtt_client_id = "tvled_client"
mqtt_transport = "tcp"
mqtt_server_host = "homeassistant.local"
mqtt_server_port = 1883 
mqtt_keepalive = 60
mqttc = mqtt.Client(client_id=mqtt_client_id, protocol = mqtt.MQTTv5, transport = mqtt_transport)

mqttc.username_pw_set("pitv","pitvledlogin")
mqttc.connect(host = mqtt_server_host,
              port = mqtt_server_port,
              keepalive = mqtt_keepalive,
              properties = None)

mqttc.on_connect = on_connect
mqttc.on_message = on_message 

# publish discovery message 
mqttc.publish("homeassistant/device/TVLeds/config", json.dumps(discovery), qos=0)

# set availibility
mqttc.publish("TVLeds/light_1/availability","online",qos=0)
mqttc.publish("TVLeds/light_2/availability","online",qos=0)
mqttc.publish("TVLeds/light_3/availability","online",qos=0)
mqttc.publish("TVLeds/light_4/availability","online",qos=0)

# init status
mqtt_status(mqttc)

try:
    mqttc.loop_forever()

except KeyboardInterrupt:
    print('ending')
    mqttc.publish("TVLeds/light_1/availability","offline",qos=0)
    mqttc.publish("TVLeds/light_2/availability","offline",qos=0)
    mqttc.publish("TVLeds/light_3/availability","offline",qos=0)
    mqttc.publish("TVLeds/light_4/availability","offline",qos=0)
    ambient_leds.clear_leds()
    exit(0) 
