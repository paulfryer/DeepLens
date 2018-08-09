var AWS = require('aws-sdk');
var rekognition = new AWS.Rekognition();
var s3 = new AWS.S3();

exports.handler = async (event, context) => {
var obj = await s3.getObject({Bucket: event.ReferenceImageBucket, Key: event.ReferenceImageKey}).promise();
var params = {
      CollectionId: 'act-1234',
      Image: { 
        Bytes: obj.Body
      },
      FaceMatchThreshold: 95,
      MaxFaces: 100
    };
   var matches = await rekognition.searchFacesByImage(params).promise();
    matches.FaceMatches.forEach(match => {
       console.log(match.Similarity, match.Face); 
    });
    return event;
};