

from skimage.measure import compare_ssim
import argparse
import imutils
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

class BoundingBox:
    def __init__(self, x, y, w, h):
            self.x = x
            self.y = y
            self.w = w
            self.h = h
            self.s = w * h
    def contains(self, x, y, w, h):
    	if (x >= self.x):
    		return True
    	return False

class Record(object):
    def __init__(self, x, y, w, h):
        self.Data = "{},{},{},{}".format(x,y,w,h)
        
class Point(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

class Rect(object):
    def __init__(self, p1, p2):
        '''Store the top, bottom, left and right values for points 
               p1 and p2 are the (corners) in either order
        '''
        self.left   = min(p1.x, p2.x)
        self.right  = max(p1.x, p2.x)
        self.bottom = min(p1.y, p2.y)
        self.top    = max(p1.y, p2.y)

def overlap(r1, r2):
    '''Overlapping rectangles overlap both horizontally & vertically
    '''
    return range_overlap(r1.left, r1.right, r2.left, r2.right) and range_overlap(r1.bottom, r1.top, r2.bottom, r2.top)

def range_overlap(a_min, a_max, b_min, b_max):
    '''Neither range is completely greater than the other
    '''
    return (a_min <= b_max) and (b_min <= a_max)


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

        # Send a starting message to IoT console
        client.publish(topic=iotTopic, payload="Starting program now..")

        ret, imageA = awscam.getLastFrame()
        if ret == False:
            raise Exception("Failed to get frame from the stream")
        
        doInfer = True
        while doInfer:
            ret, imageB = awscam.getLastFrame()
            grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
            grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)
            (score, diff) = compare_ssim(grayA, grayB, full=True)
            diff = (diff * 255).astype("uint8")
            thresh = cv2.threshold(diff, 0, 255,
            	cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
            cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
            	cv2.CHAIN_APPROX_SIMPLE)
            cnts = cnts[0] if imutils.is_cv2() else cnts[1]
            boundingBoxes = []
            for c in cnts:
            	(x, y, w, h) = cv2.boundingRect(c)
            	if w > 20 and y > 20:
            		bb = BoundingBox(x,y,w,h)
            		boundingBoxes.append(bb)
            uniqueBoxes = []
            processedBoxes = []
            for bb in sorted(boundingBoxes, key=lambda bb: bb.s, reverse=True):
            	processedBoxes.append(bb)
            	pointA = Point(bb.x, bb.y)
            	pointB = Point(bb.x + bb.w, bb.y + bb.h)
            	rect = Rect(pointA, pointB)
            	count = 0
            	for i in processedBoxes:
            		if (overlap(rect, Rect(Point(i.x, i.y), Point(i.x + i.w, i.y + i.h)))):
            			count = count + 1
            	if (count == 1):
            		uniqueBoxes.append(bb)
            records = []
            i = 0
            for bb in sorted(uniqueBoxes, key=lambda bb: bb.s, reverse=True):
            	i = i + 1
            	part = imageB[bb.y:bb.y+bb.h,bb.x:bb.x+bb.w]
            	cv2.imwrite("Part{}.png".format(i), part)
            	retval, buff = cv2.imencode('.jpg', part)
            	jpg_as_text = base64.b64encode(buff)
            	records.append({'Data': '{},{},{},{},"{}"\n'.format(bb.x,bb.y,bb.w,bb.h,jpg_as_text)})
            response = firehose.put_record_batch(
                DeliveryStreamName='movement',
                Records=records
            )
            imageA = imageB
    except Exception as e:
        msg = "Test failed: " + str(e)
        client.publish(topic=iotTopic, payload=msg)

    # Asynchronously schedule this function to be run again in 15 seconds
    Timer(15, greengrass_infinite_infer_run).start()




# Execute the function above
greengrass_infinite_infer_run()



def lambda_handler(event, context):
    # TODO implement
    return ''
    
    
    
