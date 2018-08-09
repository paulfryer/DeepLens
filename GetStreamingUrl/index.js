
var AWS = require('aws-sdk');
var kinesisvideo = new AWS.KinesisVideo();
var s3 = new AWS.S3();

exports.handler = async (event, context) => {
    var params = {
      APIName: 'GET_HLS_STREAMING_SESSION_URL',
      StreamName: event.StreamName
    };
    var dataResult = await kinesisvideo.getDataEndpoint(params).promise();
    var kinesisvideoarchivedmedia = new AWS.KinesisVideoArchivedMedia({
      endpoint: dataResult.DataEndpoint
    });
    // TODO: pass start and stop times as event parameters.
  var d = new Date();
  d.setMinutes(d.getMinutes() - 10);
  var params = {
    HLSFragmentSelector: {
      FragmentSelectorType: 'SERVER_TIMESTAMP',
      TimestampRange: {
            EndTimestamp: new Date(),
            StartTimestamp: d
           }
      
    },
    PlaybackMode: 'ON_DEMAND',
    StreamName: 'deeplens-stream'
  };
  event.StartTimestamp = params.HLSFragmentSelector.TimestampRange.StartTimestamp;
  event.EndTimestamp = params.HLSFragmentSelector.TimestampRange.EndTimestamp;
  var r = await kinesisvideoarchivedmedia.getHLSStreamingSessionURL(params).promise();
  event.HLSStreamingSessionUrl = r.HLSStreamingSessionURL;
  return event;
};
