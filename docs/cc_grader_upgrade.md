Read ~/protocol_pulse/video_pipeline_v3/gemini_grade.py FULLY.
Read ~/protocol_pulse/PIPELINE_LAWS.md.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TWO-PASS GRADER UPGRADE
Current: Gemini grades from ffprobe + render log only (blind).
Target: Gemini watches the actual video + has ffprobe data.
Expected: content dims jump from assumed 7-8s to real scores.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NO CROSS-LLM AUDIT NEEDED — this is a single-file change with
no architectural risk. The Gemini Files API is well-documented.

WHAT TO CHANGE in gemini_grade.py:

STEP 1 — Upload video to Gemini Files API before grading:

Add this function after the existing imports:

def upload_video_to_gemini(video_path, gemini_key):
    """Upload video file to Gemini Files API. Returns file URI or None."""
    import mimetypes
    file_size = os.path.getsize(video_path)
    log(f"Uploading {file_size/1048576:.1f}MB video to Gemini Files API...")

    # Resumable upload initiation
    init_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={gemini_key}"
    mime = "video/mp4"
    init_headers = {
        "Content-Type": "application/json",
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Type": mime,
        "X-Goog-Upload-Header-Content-Length": str(file_size),
    }
    init_body = json.dumps({"file": {"display_name": os.path.basename(video_path)}}).encode()

    try:
        init_req = urllib.request.Request(init_url, data=init_body, headers=init_headers, method="POST")
        with urllib.request.urlopen(init_req, timeout=30) as r:
            upload_url = r.headers.get("X-Goog-Upload-URL")
        if not upload_url:
            log("Upload init failed — no upload URL returned")
            return None

        # Upload file bytes
        with open(video_path, "rb") as f:
            video_bytes = f.read()

        upload_headers = {
            "Content-Length": str(file_size),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        }
        upload_req = urllib.request.Request(upload_url, data=video_bytes, headers=upload_headers, method="PUT")
        with urllib.request.urlopen(upload_req, timeout=120) as r:
            result = json.loads(r.read())
            file_uri = result.get("file", {}).get("uri")
            log(f"Video uploaded: {file_uri}")
            return file_uri
    except Exception as e:
        log(f"Video upload failed: {e} — falling back to text-only grading")
        return None

STEP 2 — Call upload before building prompt:

After the ffprobe section and before "Build Gemini prompt", add:
    file_uri = upload_video_to_gemini(LATEST, GEMINI_KEY)
    if file_uri:
        log("Video upload successful — two-pass grading enabled")
    else:
        log("Video upload skipped — text-only grading (fallback)")

STEP 3 — Include video in the Gemini API call:

Current payload:
    payload = {
        'contents': [{'parts': [{'text': PROMPT}]}],
        ...
    }

Replace with:
    if file_uri:
        parts_list = [
            {"file_data": {"mime_type": "video/mp4", "file_uri": file_uri}},
            {"text": PROMPT}
        ]
    else:
        parts_list = [{"text": PROMPT}]

    payload = {
        'contents': [{'parts': parts_list}],
        'generationConfig': {'maxOutputTokens': 8000, 'temperature': 0.05}
    }

STEP 4 — Update the prompt to reflect video is available:

When file_uri is set, prepend to PROMPT:
    "You have been provided the actual video file to watch.
    Score ALL dimensions based on what you actually see and hear.
    Do NOT write 'Assumed' for any dimension — watch the video.
    For host_authenticity: watch for lip sync quality, natural pacing,
    eye blinks, head movement. Score based on actual observation.
    For no_artifacts: watch for freeze frames, stuttering, compression
    artifacts, black flashes. Score based on actual observation.
    For visual_polish: observe the lower thirds, transitions, cyberpunk
    aesthetic. Score based on actual observation."

STEP 5 — Delete uploaded file after grading (cleanup):

After getting the grade result, delete the uploaded file:
    if file_uri:
        file_id = file_uri.split("/files/")[-1]
        del_url = f"https://generativelanguage.googleapis.com/v1beta/files/{file_id}?key={GEMINI_KEY}"
        try:
            del_req = urllib.request.Request(del_url, method="DELETE")
            urllib.request.urlopen(del_req, timeout=15)
            log(f"Cleaned up uploaded file: {file_id}")
        except Exception as e:
            log(f"File cleanup failed (non-fatal): {e}")

VERIFICATION — Test on existing output:
python3 ~/protocol_pulse/video_pipeline_v3/gemini_grade.py \
  ~/protocol_pulse/video_pipeline_v3/output/2026-03-24/pulse_check_20260324.mp4

Expected behavior:
  - "Uploading XXmb video to Gemini Files API..." in logs
  - "Video uploaded: files/..." in logs
  - "Two-pass grading enabled" in logs
  - Grade returned with REAL scores on content dims (not "Assumed")
  - No "assumed" in any dimension notes
  - host_authenticity score based on actual lip sync observation
  - Cleaned up file after grading

COMMIT:
bash ~/protocol_pulse/regression_test.sh — 0 FAILs
git add video_pipeline_v3/gemini_grade.py
git commit -m "feat(grading): two-pass grader — uploads actual video to Gemini for real content scoring
- Gemini now watches the video file, not just ffprobe + render log
- host_authenticity, no_artifacts, visual_polish scored from real observation
- Fallback: text-only grading if upload fails
- File deleted from Gemini after grading (no storage leak)
- Expected: content dims from assumed 7-8s to accurate real scores"
git push
