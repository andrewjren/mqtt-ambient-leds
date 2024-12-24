import os
import threading
from threading import Thread, Event
import time
from datetime import datetime
import picamera

from tvleds import *

import paho.mqtt.client as mqtt

# init AmbientLeds object
ambient_leds = AmbientLEDs()

# Threading Setup
threads = []
current_effect = 'fill'

# use as signal to stop threads
stop_thread = Event() 

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
    trigger_thread_stop()

    if task == 'off':
        ambient_leds.clear_leds()

    if task == 'fill':
        ambient_leds.fill_num(1)

    elif task == 'mood':
        t = threading.Thread(name='Mood Thread', target=task_mood)
        t.start()
        threads.append(t)

    elif task == 'pulse':
        t = threading.Thread(name='Pulse Thread', target=task_pulse)
        t.start()
        threads.append(t)

    elif task == 'ambient':
        t = threading.Thread(name='Ambient Thread', target=task_ambient)
        t.start()
        threads.append(t)
    elif task == 'rainbow':
        t = threading.Thread(name='Rainbow Thread', target=task_rainbow)
        t.start()
        threads.append(t)
    else:
        print('Task not defined!')

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")

    client.subscribe("TVLeds/light_1/switch")
    client.subscribe("TVLeds/light_1/brightness/set")
    client.subscribe("TVLeds/light_1/rgb/set")
    client.subscribe("TVLeds/light_1/effect/set")

    client.publish("TVLeds/light_1/status", "OFF", qos=0)

def on_message(client, userdata, msg):
    global ambient_leds, current_effect
    print(msg.topic+" "+str(msg.payload))

    if msg.topic == "TVLeds/light_1/switch":
        light_switch = msg.payload
        if light_switch == "OFF":
            begin_task('off')
            client.publish("TVLeds/light_1/status", "OFF", qos=0)
        elif light_switch == "ON":
            begin_task(current_effect)
            client.publish("TVLeds/light_1/status", "ON", qos=0)

    elif msg.topic == "TVLeds/light_1/brightness/set":
        light_brightness = msg.payload
        H, S, I = ambient_leds.rgb2hsi(ambient_leds.colors[0].red, ambient_leds.colors[0].green, ambient_leds.colors[0].blue)
        R, G, B = ambient_leds.hsi2rgb(H, S, light_brightness)

        ambient_leds.colors[0].set(R,G,B)
        begin_task(current_effect)
        client.publish("TVLeds/light_1/brightness/status", f"{light_brightness}", qos=0)

    elif msg.topic == "TVLeds/light_1/rgb/set":
        light_rgb = msg.payload

        red, green, blue = light_rgb.split(',')
        ambient_leds.colors[0].set(red, green, blue)
        client.publish("TVLeds/light_1/rgb/status", f"{red},{green},{blue}", qos=0)

    elif msg.topic == "TVLeds/light_1/effect/set":
        light_effect = msg.payload
        
        if current_effect != light_effect:
            current_effect = light_effect 
            trigger_thread_stop()
            begin_task(current_effect)
        
    


# Create MQTT Client 
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message 

mqttc.connect("homeassistant", 1883, 60)

mqttc.loop_forever()
