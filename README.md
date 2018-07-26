# DeepLens Lambda Functions
A repository of Lambda functions and ML models, specifically designed to run on DeepLens via Greengrass.

| Function        | Description           | Use with Model  |
| ------------- |:-------------:| -----:|
| [Stream Faces](/StreamFaces/)     | When a face is detected video will be streamed to Kinesis Video for saving in the cloud. Faces are also indexed with Rekognition for search. | Face Detection |
| [Diff Detect](/DiffDetect/)      | Captures bounding boxes of frame by frame changes in images. Changes are streamed to Kinesis Firehose for cloud based reconstruction.      |   No model used |
