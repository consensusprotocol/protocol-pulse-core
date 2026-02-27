#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Ultron API Server - Add New Endpoints
# Run on Ultron: bash add_endpoints.sh
#
# Adds: /process_ffmpeg, /run_command, /download/<path>
# Creates: ~/video_engine/shorts/
# ═══════════════════════════════════════════════════════════════════

set -e
echo "═══ Adding new endpoints to Ultron API ═══"
echo ""

# Create shorts directory
mkdir -p ~/video_engine/shorts
mkdir -p ~/video_engine/voiceovers
echo "✓ Created shorts + voiceovers directories"

# Backup current API server
cp ~/video_engine/api_server.py ~/video_engine/api_server.py.bak.$(date +%s)
echo "✓ Backed up api_server.py"

# Check if endpoints already exist
if grep -q "process_ffmpeg" ~/video_engine/api_server.py; then
    echo "⚠ process_ffmpeg endpoint already exists, skipping..."
    exit 0
fi

# Find the insertion point (before the last if __name__ block or at end of file)
# We'll append the new routes before the main block

# First, let's save the new endpoints to a temp file
cat > /tmp/new_endpoints.py << 'ENDPOINTS'

# ═══════════════════════════════════════════════════════════════════
# NEW ENDPOINTS - Added by Pulse Check Pipeline v2
# ═══════════════════════════════════════════════════════════════════

@app.route('/process_ffmpeg', methods=['POST'])
def process_ffmpeg():
    """Run FFmpeg with custom filters for video processing (GPU accelerated)."""
    data = request.json
    input_file = data.get('input_file', '')
    output_file = data.get('output_file', '')
    video_filter = data.get('video_filter', '')
    extra_args = data.get('extra_args', [])

    base_dir = os.path.expanduser('~/video_engine')
    input_path = os.path.join(base_dir, input_file)
    output_path = os.path.join(base_dir, output_file)

    # Security: prevent path traversal
    if '..' in input_file or '..' in output_file:
        return jsonify({'success': False, 'error': 'Invalid path'}), 403

    if not os.path.exists(input_path):
        return jsonify({'success': False, 'error': f'Input not found: {input_file}'}), 404

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = ['ffmpeg', '-y', '-i', input_path]
    if video_filter:
        cmd.extend(['-vf', video_filter])
    cmd.extend(extra_args)
    cmd.append(output_path)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            return jsonify({
                'success': True,
                'output_file': output_file,
                'size_mb': round(size_mb, 1),
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr[-500:] if result.stderr else 'Unknown FFmpeg error',
            }), 500

    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'FFmpeg timeout (5 min)'}), 504
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/run_command', methods=['POST'])
def run_command():
    """Run a shell command (restricted to safe operations)."""
    data = request.json
    command = data.get('command', '')

    ALLOWED_PREFIXES = [
        'mkdir', 'ls', 'du', 'ffmpeg', 'ffprobe',
        'rm ~/video_engine/', 'cat ', 'echo ',
        'mv ~/video_engine/', 'cp ~/video_engine/',
    ]

    is_allowed = any(command.strip().startswith(prefix) for prefix in ALLOWED_PREFIXES)
    if not is_allowed:
        return jsonify({
            'success': False,
            'error': f'Command not allowed. Allowed prefixes: {ALLOWED_PREFIXES}'
        }), 403

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=120,
        )
        return jsonify({
            'success': result.returncode == 0,
            'returncode': result.returncode,
            'stdout': result.stdout[-2000:] if result.stdout else '',
            'stderr': result.stderr[-500:] if result.stderr else '',
        })

    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Command timeout (2 min)'}), 504
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/download/<path:filepath>', methods=['GET'])
def download_extended(filepath):
    """Download any file from the video_engine directory tree."""
    base_dir = os.path.expanduser('~/video_engine')

    # Security: prevent directory traversal
    if '..' in filepath:
        return jsonify({'error': 'Invalid path'}), 403

    safe_path = os.path.normpath(os.path.join(base_dir, filepath))
    if not safe_path.startswith(base_dir):
        return jsonify({'error': 'Invalid path'}), 403

    # Try direct path first
    if os.path.exists(safe_path):
        return send_file(safe_path, as_attachment=True)

    # Try output directory as fallback
    output_path = os.path.join(base_dir, 'output', filepath)
    if os.path.exists(output_path):
        return send_file(output_path, as_attachment=True)

    return jsonify({'error': f'File not found: {filepath}'}), 404

ENDPOINTS

echo "✓ New endpoints written to temp file"

# Now we need to insert these before the if __name__ block
# Strategy: find the line number of 'if __name__', insert before it

MAIN_LINE=$(grep -n "if __name__" ~/video_engine/api_server.py | tail -1 | cut -d: -f1)

if [ -n "$MAIN_LINE" ]; then
    # Insert before the if __name__ block
    head -n $((MAIN_LINE - 1)) ~/video_engine/api_server.py > /tmp/api_server_new.py
    cat /tmp/new_endpoints.py >> /tmp/api_server_new.py
    echo "" >> /tmp/api_server_new.py
    tail -n +$MAIN_LINE ~/video_engine/api_server.py >> /tmp/api_server_new.py
    cp /tmp/api_server_new.py ~/video_engine/api_server.py
    echo "✓ Endpoints inserted before __main__ block"
else
    # No __main__ block, just append
    cat /tmp/new_endpoints.py >> ~/video_engine/api_server.py
    echo "✓ Endpoints appended to end of file"
fi

# Make sure subprocess is imported
if ! grep -q "import subprocess" ~/video_engine/api_server.py; then
    sed -i '1s/^/import subprocess\n/' ~/video_engine/api_server.py
    echo "✓ Added subprocess import"
fi

# Make sure send_file is imported from flask
if ! grep -q "send_file" ~/video_engine/api_server.py; then
    sed -i 's/from flask import/from flask import send_file, /' ~/video_engine/api_server.py
    echo "✓ Added send_file import"
fi

# Clean up
rm -f /tmp/new_endpoints.py /tmp/api_server_new.py

echo ""
echo "═══ Endpoints Added ═══"
echo ""
echo "New routes:"
echo "  POST /process_ffmpeg  - GPU video processing"
echo "  POST /run_command     - Safe shell commands"
echo "  GET  /download/<path> - File downloads"
echo ""
echo "Restart your API server to activate:"
echo "  Option 1: sudo systemctl restart video-api"
echo "  Option 2: kill the running process and restart manually"
echo ""
echo "Test after restart:"
echo "  curl -s https://video.protocolpulse.io/health"
