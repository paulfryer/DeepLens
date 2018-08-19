from PIL import Image
from PIL import ImageChops
from PIL import ImageDraw

import cv2
import base64
import boto3

from threading import Thread, Event, Timer
import os  
import json  
import awscam  
import time  
import greengrasssdk 
import datetime

firehose = boto3.client('firehose')

def getDifference(i1, i2):
    assert i1.mode == i2.mode, "Different kinds of images."
    assert i1.size == i2.size, "Different sizes."
    pairs = zip(i1.getdata(), i2.getdata())
    if len(i1.getbands()) == 1:
        # for gray-scale jpegs
        dif = sum(abs(p1-p2) for p1,p2 in pairs)
    else:
        dif = sum(abs(c1-c2) for p1,p2 in pairs for c1,c2 in zip(p1,p2))
    ncomponents = i1.size[0] * i1.size[1] * 3
    percentDiff = (dif / 255.0 * 100) / ncomponents
    return percentDiff



client = greengrasssdk.client('iot-data')
iotTopic = '$aws/things/{}/infer'.format(os.environ['AWS_IOT_THING_NAME'])

ret, frame = awscam.getLastFrame()
ret,jpeg = cv2.imencode('.jpg', frame) 
Write_To_FIFO = True
class FIFO_Thread(Thread):
    def __init__(self):
        ''' Constructor. '''
        Thread.__init__(self)
 
    def run(self):
        fifo_path = "/tmp/results.mjpeg"
        if not os.path.exists(fifo_path):
            os.mkfifo(fifo_path)
        f = open(fifo_path,'w')
        client.publish(topic=iotTopic, payload="Opened Pipe")
        while Write_To_FIFO:
            try:
                f.write(jpeg.tobytes())
            except IOError as e:
                continue  

def greengrass_infinite_infer_run():
    try:
        results_thread = FIFO_Thread()
        results_thread.start()
        client.publish(topic=iotTopic, payload="Starting program now..")
        ret, imageA = awscam.getLastFrame()
        while True:
            ret, imageB = awscam.getLastFrame()
            difference = getDifference(imageA, imageB)
            client.publish(topic=iotTopic, payload="Difference: " + difference)
            imageA = imageB
    except Exception as e:
        msg = "Test failed: " + str(e)
        client.publish(topic=iotTopic, payload=msg)
    Timer(15, greengrass_infinite_infer_run).start()
greengrass_infinite_infer_run()

def lambda_handler(event, context):
    i1 = Image.open("TestImages/Lenna100.jpg")
    i2 = Image.open("TestImages/Lenna50.jpg")
    difference = getDifference(i1, i2)
    print("Difference: " + difference)
    return