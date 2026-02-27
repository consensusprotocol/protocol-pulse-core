#!/bin/bash
# ============================================
# MuseTalk Deployment Script for Ultron
# ============================================
# Run from local Mac to set up MuseTalk on Ultron.
#
# Usage:
#   bash scripts/deploy_musetalk.sh
#
# Prerequisites:
#   - SSH access to ultron (ssh ultron)
#   - MuseTalk repo already cloned at ~/MuseTalk
#   - Video engine running at ~/video_engine

set -e

echo "=========================================="
echo "  MuseTalk Deployment — Ultron GPU Server"
echo "=========================================="

# Step 1: Create venv and install PyTorch
echo ""
echo "Step 1: Setting up Python environment..."
ssh ultron 'cd ~/MuseTalk && \
    python3 -m venv venv && \
    source venv/bin/activate && \
    pip install --upgrade pip && \
    pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu121'

# Step 2: Install MuseTalk dependencies
echo ""
echo "Step 2: Installing MuseTalk dependencies..."
ssh ultron 'cd ~/MuseTalk && \
    source venv/bin/activate && \
    pip install -r requirements.txt'

# Step 3: Download model weights
echo ""
echo "Step 3: Downloading model weights..."
ssh ultron 'cd ~/MuseTalk && \
    source venv/bin/activate && \
    bash download_weights.sh'

# Step 4: Deploy musetalk_wrapper.py to video_engine
echo ""
echo "Step 4: Deploying wrapper to video_engine..."
python3 -c "
from services.video_engine.ultron_musetalk import MUSETALK_WRAPPER_CODE
print(MUSETALK_WRAPPER_CODE)
" | ssh ultron "cat > ~/video_engine/musetalk_wrapper.py"

# Step 5: Add avatar endpoint to api_server.py (if not already present)
echo ""
echo "Step 5: Checking avatar endpoint..."
if ssh ultron "grep -q 'generate_avatar' ~/video_engine/api_server.py"; then
    echo "  Avatar endpoint already present in api_server.py"
else
    echo "  Adding avatar endpoint to api_server.py..."
    python3 -c "
from services.video_engine.ultron_musetalk import AVATAR_ENDPOINT_CODE
print(AVATAR_ENDPOINT_CODE)
" | ssh ultron "cat >> ~/video_engine/api_server.py"
    echo "  Added. Restart api_server.py to activate."
fi

# Step 6: Verify installation
echo ""
echo "Step 6: Verifying installation..."
ssh ultron 'cd ~/MuseTalk && source venv/bin/activate && python3 -c "
import torch
print(f\"  PyTorch: {torch.__version__}\")
print(f\"  CUDA: {torch.cuda.is_available()}\")
print(f\"  GPU count: {torch.cuda.device_count()}\")
"'

ssh ultron 'cd ~/MuseTalk && ls -la models/ 2>/dev/null || echo "  Models directory not found — run download_weights.sh"'

echo ""
echo "=========================================="
echo "  MuseTalk deployment complete!"
echo ""
echo "  Next steps:"
echo "  1. Upload oracle_face.png to ~/video_engine/assets/"
echo "  2. Restart api_server.py on Ultron"
echo "  3. Test: curl -X POST https://video.protocolpulse.io/generate_avatar"
echo "=========================================="
