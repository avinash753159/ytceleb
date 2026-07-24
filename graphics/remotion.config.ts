import {Config} from '@remotion/cli/config';

// Alpha-channel overlay defaults: PNG frames (jpeg has no alpha), VP8 webm
// with yuva420p. Verified pipeline: composite with
//   ffmpeg -i base.mp4 -c:v libvpx -i overlay.webm \
//     -filter_complex "[0:v][1:v]overlay=0:0:eof_action=pass" ...
Config.setVideoImageFormat('png');
Config.setPixelFormat('yuva420p');
Config.setCodec('vp8');
Config.setOverwriteOutput(true);
