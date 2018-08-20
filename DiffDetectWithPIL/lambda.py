from PIL import Image
#from PIL import ImageChops
#from PIL import ImageDraw
from threading import Thread, Event, Timer
import cv2
import os  
import json  
import awscam  
import greengrasssdk 
import time
import StringIO

client = greengrasssdk.client('iot-data')
iotTopic = '$aws/things/{}/infer'.format(os.environ['AWS_IOT_THING_NAME'])
client.publish(topic=iotTopic, payload="Starting program now..")

def getDifference(frame1, frame2):
    
    #client.publish(topic=iotTopic, payload='trying to encode image.')
    ret, image1 = cv2.imencode('.jpg', frame1)
    ret, image2 = cv2.imencode('.jpg', frame2)
    
    #client.publish(topic=iotTopic, payload='trying to convert image.')
    #converted1 = cv2.cvtColor(image1, cv2.COLOR_BGR2RGB)
    #converted2 = cv2.cvtColor(image2, cv2.COLOR_BGR2RGB)
    
        
    #client.publish(topic=iotTopic, payload='trying to save as string.')
    image1String = image1.tostring()
    image2String = image2.tostring()
        
    #client.publish(topic=iotTopic, payload='trying to open image as string.')
    i1 = Image.open(StringIO.StringIO(image1String))
    i2 = Image.open(StringIO.StringIO(image2String))

    #client.publish(topic=iotTopic, payload='checking mode and size')
    #assert i1.mode == i2.mode, "Different kinds of images."
    #assert i1.size == i2.size, "Different sizes."
    pairs = zip(i1.getdata(), i2.getdata())
    if len(i1.getbands()) == 1:
        # for gray-scale jpegs
        dif = sum(abs(p1-p2) for p1,p2 in pairs)
    else:
        dif = sum(abs(c1-c2) for p1,p2 in pairs for c1,c2 in zip(p1,p2))
    ncomponents = i1.size[0] * i1.size[1] * 3
    percentDiff = (dif / 255.0 * 100) / ncomponents
    return percentDiff

def greengrass_infinite_infer_run():
    try:
        client.publish(topic=iotTopic, payload="Trying main loop..")
        ret, frameA = awscam.getLastFrame()
        Stream = True
        while Stream:
            #time.sleep(1)
            ret, frameB = awscam.getLastFrame()
            difference = getDifference(frameA, frameB)
            client.publish(topic=iotTopic, payload="Difference: " + str(difference))
            frameA = frameB
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
