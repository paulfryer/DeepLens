
var AWS = require('aws-sdk');
var kinesisvideo = new AWS.KinesisVideo();
var s3 = new AWS.S3();


exports.handler = async (event, context) => {
  
      var nowEpoc = new Date(); // Math.floor(new Date() / 1000);
    
    var MS_PER_MINUTE = 60000;
    var start = new Date(nowEpoc - 1 * MS_PER_MINUTE);
    
  console.log(Date.parse('2018-07-06 3:18:27'));
  
 var params = {
      APIName: 'GET_HLS_STREAMING_SESSION_URL', //PUT_MEDIA | GET_MEDIA | LIST_FRAGMENTS | GET_MEDIA_FOR_FRAGMENT_LIST, /* required */
      //StreamARN: 'STRING_VALUE',
      StreamName: 'deeplens-stream'
    };
    var dataResult = await kinesisvideo.getDataEndpoint(params).promise();
    
    console.log(dataResult.DataEndpoint);

    var kinesisvideoarchivedmedia = new AWS.KinesisVideoArchivedMedia({
      endpoint: dataResult.DataEndpoint
    });
    
  var params = {
   
  //DiscontinuityMode: ALWAYS | NEVER,
 // Expires: 0,
  HLSFragmentSelector: {
    FragmentSelectorType: 'PRODUCER_TIMESTAMP', // | SERVER_TIMESTAMP,
    TimestampRange: {
          EndTimestamp: Date.parse('2018-07-05 20:18:27') / 1000,
          StartTimestamp: Date.parse('2018-07-05 18:18:27') / 1000
         }
    
  },
  //MaxMediaPlaylistFragmentResults: 0,
  PlaybackMode: 'ON_DEMAND',
 // StreamARN: 'STRING_VALUE',
  
  StreamName: 'deeplens-stream'
};

console.log(params);
var r = await kinesisvideoarchivedmedia.getHLSStreamingSessionURL(params).promise();
  
  console.log("Got streaming result", r.HLSStreamingSessionURL);

    return event;
};
