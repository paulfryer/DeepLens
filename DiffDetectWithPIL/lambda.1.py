#from PIL import Image
#from PIL import ImageChops
#from PIL import ImageDraw
from threading import Thread, Event, Timer
import cv2
import os  
import json  
import awscam  
import greengrasssdk 



#def getDifference(i1, i2):
##    assert i1.mode == i2.mode, "Different kinds of images."
 #   assert i1.size == i2.size, "Different sizes."
 #   pairs = zip(i1.getdata(), i2.getdata())
 #   if len(i1.getbands()) == 1:
 #       # for gray-scale jpegs
 #       dif = sum(abs(p1-p2) for p1,p2 in pairs)
 #   else:
 #       dif = sum(abs(c1-c2) for p1,p2 in pairs for c1,c2 in zip(p1,p2))
 #   ncomponents = i1.size[0] * i1.size[1] * 3
 #   percentDiff = (dif / 255.0 * 100) / ncomponents
 #   return percentDiff

def getDifference(i1, i2):
    return '0.022'


client = greengrasssdk.client('iot-data')
iotTopic = '$aws/things/{}/infer'.format(os.environ['AWS_IOT_THING_NAME'])
client.publish(topic=iotTopic, payload="Starting program now..")

ret, frame = awscam.getLastFrame()
ret, jpeg = cv2.imencode('.jpg', frame) 

def greengrass_infinite_infer_run():
    try:
        client.publish(topic=iotTopic, payload="Trying main loop..")
        imageA = jpeg
        Stream = True
        while Stream:
            imageB = jpeg
            difference = getDifference(imageA, imageB)
            client.publish(topic=iotTopic, payload="Difference: " + difference)
            imageA = imageB
    except Exception as e:
        msg = "Test failed: " + str(e)
        client.publish(topic=iotTopic, payload=msg)
    Timer(15, greengrass_infinite_infer_run).start()
greengrass_infinite_infer_run()

def lambda_handler(event, context):
    #i1 = Image.open("TestImages/Lenna100.jpg")
    #i2 = Image.open("TestImages/Lenna50.jpg")
    difference = getDifference(1, 2)
    print("Difference: " + difference)
    return
