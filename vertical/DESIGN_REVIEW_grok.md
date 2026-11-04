1) "4+ faces or screen-share -> full 16:9 letterboxed + enlarged guest column" will put the wrong person on screen whenever a 5-tile source has one silent host whose tile is still visible; the rule forces the entire grid instead of dropping the inactive column.

2) No. Stack-all-faces destroys retention on 2-up/3-up. Top news clip accounts (@bitcoinnews, @cryptodaily, @coinbureau shorts) almost always do active-speaker crop or 2/3-face max with the speaker dominant; they drop the silent tile.

3) Per-tile audio energy on the separate Riverside stems is fastest and sufficient (realistic 92-96 % on test set). Lip activity on MediaPipe is next but drops below 85 % under compression. TalkNet/Light-ASD are overkill and too slow; skip them.

4) "How many faces visible" and "is the composition one of the four allowed" miss everything. Replace with: "which exact tiles from the source grid are shown", "is any tile completely missing that was present in source", "are debug rectangles or text present", "is any face cut at the 9:16 edges".

5) Batched SCRFD (ONNX, TensorRT) at 1080p tiles: ~4-6 ms/frame on 4090. MediaPipe GPU delegate is 9-12 ms and less accurate on small tiles; YOLO-face is slower with no accuracy gain here.

6) Every seam measurement (persistence on rows 120-900, SEAM_STEP=18, MIN_TILE_FRAC=0.22) breaks when YouTube letterboxes, rescales, or burns lower-thirds that move the actual gutters; the hardcoded SEAM_ROWS and single-pass grey decode will also miss burned-in overlays.

7) a) Assert that every output frame contains exactly the faces listed in shot_map.json for that shot (catches wrong face, dropped column, 3-band from 5-tile). b) Assert no cv2.rectangle or ImageDraw calls reach the final render path (catches baked debug boxes). c) Assert layout ID is constant across every frame inside a shot boundary from shotmap (catches mid-clip layout switches).

8) The Grok vision critic loop and its cost-logging.