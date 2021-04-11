import os
import cgitb ; cgitb.enable() 
import spidev 
import time
import busio
import digitalio
import board
import adafruit_pcd8544
import RPi.GPIO as GPIO
import requests
import threading
import sys
from adafruit_bus_device.spi_device import SPIDevice
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from mpd import MPDClient

print("Initializing")
url = "http://alexrans0808003.hub.ubeac.io/iotessalex"
uid = "iotessyour alex"
ipv4 = os.popen('ip addr show wlan0').read().split("inet ")[1].split("/")[0]

# MPD Setup
print("Setting up MPD")
client = MPDClient()
client.timeout = 10
client.idletimeout = None    
client.connect("localhost", 6600)
print(client.mpd_version)
client.clear()

# Adding to playlist from file
channel_file = open("channels", "r")
channel_list = channel_file.read().splitlines()
for i in channel_list:
    client.add(i)
print(client.playlist())

# IO cleanup and init
GPIO.setmode(GPIO.BCM)
print("Setting up GPIO")
pins = [2, 3, 4, 17]
pins_reverse = [17, 4, 3, 2]
for pin in pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, 0)


# Initialize SPI bus
print("Initializing SPI bus")
spi_screen = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Initialize display
print("Setting up display")
dc = digitalio.DigitalInOut(board.D23)  # data/command
cs1 = digitalio.DigitalInOut(board.CE1)  # chip select CE1 for display
reset = digitalio.DigitalInOut(board.D24)  # reset
display = adafruit_pcd8544.PCD8544(spi_screen, dc, cs1, reset, baudrate= 1000000)
display.bias = 4
display.contrast = 60
display.invert = True

#  Clear the display.  Always call show after changing pixels to make the display update visible!
display.fill(0)
display.show()

# Load default font.
font = ImageFont.load_default()
#font=ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", 10)

# Get drawing object to draw on image
image = Image.new('1', (display.width, display.height)) 
draw = ImageDraw.Draw(image)
 	
# Draw a white filled box to clear the image.
draw.rectangle((0, 0, display.width, display.height), outline=255, fill=255)


# Initialize SPI bus
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Initialize control pins for adc
cs0 = digitalio.DigitalInOut(board.CE0)  # chip select
adc = SPIDevice(spi, cs0, baudrate= 1000000)
 
# read SPI data 8 possible adc's (0 thru 7) 
def readadc(adcnum): 
    if ((adcnum > 7) or (adcnum < 0)): 
        return -1 
    with adc:
        r = bytearray(3)
        spi.write_readinto([1,(8+adcnum)<<4,0], r)
        time.sleep(0.000005)
        adcout = ((r[1]&3) << 8) + r[2] 
        return adcout

# Functions
# Stepper motor
seq = [ [1, 0, 0, 0],
        [1, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 1],
        [0, 0, 0, 1],
        [1, 0, 0, 1] ]
def rotate(direction):
    if direction == "Reverse":
        for i in range(64):
            for halfstep in range(8):
                for pin in range(4):
                    GPIO.output(pins_reverse[pin], seq[halfstep][pin])
                time.sleep(0.001)
    else:
        for i in range(64):
            for halfstep in range(8):
                for pin in range(4):
                    GPIO.output(pins[pin], seq[halfstep][pin])
                time.sleep(0.001)

def return_to_start():
    global chnl
    motorrange = 64*(chnl-1)
    for i in range(motorrange):
            for halfstep in range(8):
                for pin in range(4):
                    GPIO.output(pins[pin], seq[halfstep][pin])
                time.sleep(0.001)


#Prev. channel
def prev_channel():
    global chnl
    global chnl_list
    global chnl_switch
    chnl -= 1
    client.previous()
    chnl_switch = True
    rotate("")
    for i in chnl_list:
        if i == chnl:
            GPIO.output(chnl_list[i], 1)
        else:
            GPIO.output(chnl_list[i], 0)
    print(os.system("mpc current"))

#Next channel
def next_channel():
    global chnl
    global chnl_list
    global chnl_switch
    chnl += 1
    client.next()
    chnl_switch = True
    rotate("Reverse")
    for i in chnl_list:
        if i == chnl:
            GPIO.output(chnl_list[i], 1)
        else:
            GPIO.output(chnl_list[i], 0)
    print(os.system("mpc current"))
    

tmp0 = 0
chnl = 1
change = True
print("Starting program")
client.play()
# Main thread
def thread_main():
    # Variables
    global chnl
    global chnl_list
    global chnl_switch
    chnl = 1
    chnl_switch = False
    # Channel number to GPIO pin 
    chnl_list = {
        1: 2,
        2: 3,
        3: 4,
        4: 17
    }
    # Channel number to corresponding name
    chnl_name = {
        1: "Studio Brussel",
        2: "Radio 1",
        3: "MNM",
        4: "Klara"
    }
    # Channel number to corresponding image
    chnl_img = {
        1: "stubru.png",
        2: "radio1.png",
        3: "mnm.png",
        4: "klara.png"
    }
    while True:
        
        # tmp0 to % for volume
        global tmp0
        tmp0 = readadc(0)
        tmp0 = (tmp0/1023)*100
        tmp0 = int(tmp0)
        client.setvol(tmp0)

        #tmp1 for channel select
        tmp1 = readadc(1)
        tmp1 = int(tmp1)

        # channel switcher and indicator
        if tmp1 >= 50 and tmp1 <= 973:
            chnl_switch = False
        elif tmp1 < 50 and chnl_switch == False and chnl != 1:
            prev_channel()
        elif tmp1 > 973 and chnl_switch == False and chnl != 4:
            next_channel()
        
        # Drawing LCD
        draw.rectangle((0, 0, display.width, display.height), outline=255, fill=255)
        draw.text((1,1), (chnl_name[chnl]), font=font)
        draw.text((1,8), ("Vol: " + str(tmp0)) + "%", font=font)
        draw.text((1,16), ipv4, font=font)
        draw.bitmap((1,24), Image.open(chnl_img[chnl]).convert("1"))
        display.image(image)
        display.show()
        # running at 30fps for optimization
        time.sleep(1/30)

# Ubeac thread
def thread_ubeac():
    global tmp0
    global chnl
    # COmpiling and sending data
    while True:
        data1= {
            "id": uid,
            "sensors": [{
                "id": "vol",
                "data": tmp0
            }]
        }
        data2= {
            "id": uid,
            "sensors": [{
                "id": "chnl",
                "data": chnl
            }]
        }
        requests.post(url, verify=False, json=data1)
        print("sending data 1:", tmp0)
        time.sleep(1)
        requests.post(url, verify=False, json=data2)
        print("sending data 2:", chnl)
        time.sleep(10)

# Thread for terminal controls
def thread_usrinput():
    global chnl
    while True:
        print("commands: NEXT | PREV | PAUSE | START | SHUTDOWN")
        usrinput = input("enter command: ")
        if usrinput.upper() == "NEXT":
            if chnl != 4:
                next_channel()
        elif usrinput.upper() == "PREV":
            if chnl != 1:
                prev_channel()
        elif usrinput.upper() == "PAUSE":
            os.system("mpc pause")
        elif usrinput.upper() == "START":
            os.system("mpc play")
        # Shutdown command
        elif usrinput.upper() == "SHUTDOWN":
            print("Terminating program")
            os.system("mpc stop")
            os.system("mpc clear")
            draw.rectangle((0, 0, display.width, display.height), outline=255, fill=255)
            display.image(image)
            display.show()
            return_to_start()
            for i in pins:
                GPIO.output(i, 0)
            GPIO.cleanup()
            os._exit(1)
        else:
            print("ERROR")


# Multi threading
t1 = threading.Thread(target=thread_main)
t2 = threading.Thread(target=thread_ubeac)
t3 = threading.Thread(target=thread_usrinput)
t1.start()
t2.start()
t3.start()
t1.join()
t2.join()
t3.join()
