from threading import Thread, Event, Timer
import os  
import json  
import DeepLens_Kinesis_Video as dkv  
from botocore.session import Session  
import numpy as np  
import awscam  
import cv2  
import time  
import greengrasssdk 
import datetime

import boto3

client = greengrasssdk.client('iot-data')
iotTopic = '$aws/things/{}/infer'.format(os.environ['AWS_IOT_THING_NAME'])

thingName = os.environ['AWS_IOT_THING_NAME'];

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

def index_faces(collection_id, external_image_id, region="us-east-1"):
	rekognition = boto3.client("rekognition", region)
	response = rekognition.index_faces(
		Image={
			"Bytes": jpeg.tobytes()
		},
		ExternalImageId=external_image_id,
		CollectionId=collection_id
	)

def push_to_s3(img, index):
    try:
        bucket_name = thingName.replace('_', '-').lower()
        timestamp = int(time.time())
        now = datetime.datetime.now()
        key = "faces/{}-{}.jpg".format(timestamp, index)
        s3 = boto3.client('s3')
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        _, jpg_data = cv2.imencode('.jpg', img, encode_param)
        response = s3.put_object(Body=jpg_data.tostring(),
                                 Bucket=bucket_name,
                                 Key=key)
    except Exception as e:
        msg = "Pushing to S3 failed: " + str(e)
        client.publish(topic=iotTopic, payload=msg)

def iso_format(dt):
    try:
        utc = dt + dt.utcoffset()
    except TypeError as e:
        utc = dt
    isostring = datetime.datetime.strftime(utc, '%Y-%m-%dT%H:%M:%S.{0}Z')
    return isostring.format(int(round(utc.microsecond/1000.0)))

def greengrass_infinite_infer_run():
    try:
        modelPath = "/opt/awscam/artifacts/mxnet_deploy_ssd_FP16_FUSED.xml"
        modelType = "ssd"
        input_width = 300
        input_height = 300
        prob_thresh = 0.15
        results_thread = FIFO_Thread()
        results_thread.start()
        client.publish(topic=iotTopic, payload="Face detection starts now")
        mcfg = {"GPU": 1}
        model = awscam.Model(modelPath, mcfg)
        client.publish(topic=iotTopic, payload="Model loaded")
        ret, frame = awscam.getLastFrame()
        if ret == False:
            raise Exception("Failed to get frame from the stream")
            
        yscale = float(frame.shape[0]/input_height)
        xscale = float(frame.shape[1]/input_width)
        session = Session()  
        creds = session.get_credentials()  
        stream_name = thingName
        retention = 2
        region = "us-east-1"   
        producer = dkv.createProducer(creds.access_key, creds.secret_key, creds.token, region)  
        client.publish(topic=iotTopic, payload="Producer created")  
        my_stream = producer.createStream(stream_name, retention)  
        client.publish(topic=iotTopic, payload="Stream {} created".format(stream_name))  
        stopStreamingTime = datetime.datetime.now() - datetime.timedelta(minutes = 1)
        doInfer = True
        while doInfer:
            if stopStreamingTime <= datetime.datetime.now():
                my_stream.stop()
            ret, frame = awscam.getLastFrame()
            if ret == False:
                raise Exception("Failed to get frame from the stream")
            frameResize = cv2.resize(frame, (input_width, input_height))
            inferOutput = model.doInference(frameResize)
            parsed_results = model.parseResult(modelType, inferOutput)['ssd']
            label = '{'
            for i, obj in enumerate(parsed_results):
                if obj['prob'] < prob_thresh:
                    break
                xmin = int( xscale * obj['xmin'] ) + int((obj['xmin'] - input_width/2) + input_width/2)
                ymin = int( yscale * obj['ymin'] )
                xmax = int( xscale * obj['xmax'] ) + int((obj['xmax'] - input_width/2) + input_width/2)
                ymax = int( yscale * obj['ymax'] )
                if stopStreamingTime <= datetime.datetime.now():
                    my_stream.start()
                client.publish(topic=iotTopic, payload="About to save face to S3")
                crop_img = frame[ymin:ymax, xmin:xmax]
                push_to_s3(crop_img, i)
                frameKey = iso_format(datetime.datetime.utcnow())
                index_faces(thingName, frameKey)
                stopStreamingTime = datetime.datetime.now() + datetime.timedelta(seconds = 10)
                cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (255, 165, 20), 4)
                label += '"{}": {:.2f},'.format(str(obj['label']), obj['prob'] )
                label_show = '{}: {:.2f}'.format(str(obj['label']), obj['prob'] )
                cv2.putText(frame, label_show, (xmin, ymin-15),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 165, 20), 4)
            label += '"null": 0.0'
            label += '}'  
            global jpeg
            ret,jpeg = cv2.imencode('.jpg', frame)
    except Exception as e:
        msg = "Test failed: " + str(e)
        client.publish(topic=iotTopic, payload=msg)
        
    Timer(15, greengrass_infinite_infer_run).start()

greengrass_infinite_infer_run()

def function_handler(event, context):
    return
