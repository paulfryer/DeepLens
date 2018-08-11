#
# Copyright Amazon AWS DeepLens, 2017
#

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

# Creating a greengrass core sdk client
client = greengrasssdk.client('iot-data')

# The information exchanged between IoT and clould has 
# a topic and a message body.
# This is the topic that this code uses to send messages to cloud
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


def extract_features(vector_size=32):
    try:
        # Using KAZE, cause SIFT, ORB and other was moved to additional module
        # which is adding addtional pain during install
        alg = cv2.KAZE_create()
        # Dinding image keypoints
        kps = alg.detect(jpeg)
        # Getting first 32 of them. 
        # Number of keypoints is varies depend on image size and color pallet
        # Sorting them based on keypoint response value(bigger is better)
        kps = sorted(kps, key=lambda x: -x.response)[:vector_size]
        # computing descriptors vector
        kps, dsc = alg.compute(jpeg, kps)
        # Flatten all of them in one big vector - our feature vector
        dsc = dsc.flatten()
        # Making descriptor of same size
        # Descriptor vector size is 64
        needed_size = (vector_size * 64)
        if dsc.size < needed_size:
            # if we have less the 32 descriptors then just adding zeros at the
            # end of our feature vector
            dsc = np.concatenate([dsc, np.zeros(needed_size - dsc.size)])
    except cv2.error as e:
        print('Error: ', e)
        return None
    return dsc

def index_features(account, camera, frame, boundingBox, features):
    
    
    csv = "{},{},{},{}".format(account, camera, frame, boundingBox)
    
    firehose = boto3.client("firehose", "us-east-1")
    response = firehose.put_record(
    DeliveryStreamName='face-features',
    Record={
            'Data': "{}\n".format(csv)
        }
    )
    

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
        bucket_name = "sky-cameras"

        timestamp = int(time.time())
        now = datetime.datetime.now()
        key = "faces/{}_{}/{}_{}/{}_{}.jpg".format(now.month, now.day,
                                                   now.hour, now.minute,
                                                   timestamp, index)

        s3 = boto3.client('s3')

        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        _, jpg_data = cv2.imencode('.jpg', img, encode_param)
        response = s3.put_object(Body=jpg_data.tostring(),
                                 Bucket=bucket_name,
                                 Key=key)

        client.publish(topic=iotTopic, payload="Response: {}".format(response))
        client.publish(topic=iotTopic, payload="Face pushed to S3")
    except Exception as e:
        msg = "Pushing to S3 failed: " + str(e)
        client.publish(topic=iotTopic, payload=msg)

def greengrass_infinite_infer_run():
    try:
        modelPath = "/opt/awscam/artifacts/mxnet_deploy_ssd_FP16_FUSED.xml"
        modelType = "ssd"
        input_width = 300
        input_height = 300
        prob_thresh = 0.15
        results_thread = FIFO_Thread()
        results_thread.start()

        # Send a starting message to IoT console
        client.publish(topic=iotTopic, payload="Face detection starts now")

        # Load model to GPU (use {"GPU": 0} for CPU)
        mcfg = {"GPU": 1}
        model = awscam.Model(modelPath, mcfg)
        client.publish(topic=iotTopic, payload="Model loaded")
        ret, frame = awscam.getLastFrame()
        if ret == False:
            raise Exception("Failed to get frame from the stream")
            
        yscale = float(frame.shape[0]/input_height)
        xscale = float(frame.shape[1]/input_width)

        # Use the boto session API to grab credentials  
        session = Session()  
        creds = session.get_credentials()  
        # Stream name and retention  
        stream_name = 'deeplens-stream'  
        retention = 2 #hours  
        region = "us-east-1"  
        # Create producer and stream.  
        producer = dkv.createProducer(creds.access_key, creds.secret_key, creds.token, region)  
        client.publish(topic=iotTopic, payload="Producer created")  
        my_stream = producer.createStream(stream_name, retention)  
        client.publish(topic=iotTopic, payload="Stream {} created".format(stream_name))  
        stopStreamingTime = datetime.datetime.now() - datetime.timedelta(minutes = 1)

        doInfer = True
        while doInfer:
            
            #stop streaming if the stop time is reached.
            if stopStreamingTime <= datetime.datetime.now():
                my_stream.stop()
            
            # Get a frame from the video stream
            ret, frame = awscam.getLastFrame()
            # Raise an exception if failing to get a frame
            if ret == False:
                raise Exception("Failed to get frame from the stream")

            # Resize frame to fit model input requirement
            frameResize = cv2.resize(frame, (input_width, input_height))

            # Run model inference on the resized frame
            inferOutput = model.doInference(frameResize)


            # Output inference result to the fifo file so it can be viewed with mplayer
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
                    ##crop_img = frame[ymin:ymax, xmin:xmax]
                    ##push_to_s3(crop_img, i)
                
                # make sure we start streaming before we index so timestamps exist in video stream.
                frameKey = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                index_faces("act-1234", frameKey); 
                #features = extract_features()
                #index_features("cam123", "8-4-6-2", features, frameKey, "act456")
                
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

    # Asynchronously schedule this function to be run again in 15 seconds
    Timer(15, greengrass_infinite_infer_run).start()


# Execute the function above
greengrass_infinite_infer_run()


# This is a dummy handler and will not be invoked
# Instead the code above will be executed in an infinite loop for our example
def function_handler(event, context):
    return
