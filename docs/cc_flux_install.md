Install FLUX.1-schnell (NOT flux-dev — schnell is Apache 2.0 licensed, no HF token needed, same GPU, faster) and wire it into the Protocol Pulse image_of_the_day pipeline.

SYSTEM: Ultron, Ubuntu 22.04, 4x RTX 4090 (24GB each), PyTorch 2.6+cu124, diffusers 0.29
TARGET GPU: cuda:2 (render loop uses cuda:0 and cuda:1 — use cuda:2 to avoid contention)
OUTPUT: ~/protocol_pulse/data/social_queue/image_of_the_day.png

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — INSTALL FLUX.1-schnell
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLUX.1-schnell is Apache 2.0, no HF token needed, downloads from:
  black-forest-labs/FLUX.1-schnell on HuggingFace

Install/upgrade deps:
  pip install --break-system-packages --upgrade diffusers transformers accelerate sentencepiece protobuf

Test download (will cache to ~/.cache/huggingface/hub/):
  python3 -c "
  from diffusers import FluxPipeline
  import torch
  pipe = FluxPipeline.from_pretrained(
      'black-forest-labs/FLUX.1-schnell',
      torch_dtype=torch.bfloat16,
  )
  pipe.enable_attention_slicing()
  pipe.enable_sequential_cpu_offload()  # if VRAM tight
  pipe = pipe.to('cuda:2')
  img = pipe('a simple test', num_inference_steps=4, guidance_scale=0.0).images[0]
  img.save('/tmp/flux_test.png')
  print('FLUX test OK:', img.size)
  "

If VRAM error on cuda:2 try enable_model_cpu_offload() instead of .to('cuda:2').

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — REWRITE image_of_the_day.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
File: ~/protocol_pulse/services/image_of_the_day.py

Replace the Grok Aurora API call with local FLUX.1-schnell inference.
Keep all existing logic (format rotation, statement selection, morning brief integration).

The generate_image() function should become:

def generate_image(prompt_text, env):
    from diffusers import FluxPipeline
    import torch
    
    log("Loading FLUX.1-schnell on cuda:2...")
    pipe = FluxPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-schnell",
        torch_dtype=torch.bfloat16,
    )
    pipe.enable_attention_slicing()
    
    try:
        pipe = pipe.to("cuda:2")
    except RuntimeError:
        log("cuda:2 VRAM tight — using cpu offload")
        pipe.enable_model_cpu_offload()
    
    log(f"Generating image...")
    result = pipe(
        prompt_text,
        width=1024,
        height=1024, 
        num_inference_steps=4,   # schnell is optimized for 4 steps
        guidance_scale=0.0,      # schnell uses 0 guidance
    )
    img = result.images[0]
    img.save(str(OUT_PATH))
    log(f"Image saved: {OUT_PATH} ({OUT_PATH.stat().st_size // 1024}KB)")
    
    # Unload model to free VRAM for render loop
    del pipe
    torch.cuda.empty_cache()
    return True

Also update build_prompt() to produce a pure visual description 
(no instruction-style text — learned from Grok failure):

The prompt should describe the IMAGE VISUALLY, not give instructions.
Example good prompt for propaganda poster format:
"Soviet constructivist propaganda poster, square format. Solid deep red 
background with paper grain texture. Black silhouette of a fist gripping 
an hourglass, dollar sign price tag hanging from it. High contrast flat 
graphic design. Black banner strip at bottom with cream bold all-caps text: 
FIAT IS LEGALIZED TIME THEFT. Small red ECG waveform icon bottom-right 
corner labeled PROTOCOL PULSE. Three colors only: red black cream. 
Sharp flat design, no gradients, print quality."

Build a FLUX_PROMPTS dict with pre-written visual prompts for each 
STATEMENT in STATEMENTS list. Each prompt describes the image purely 
as a visual scene. Rotate through them by day_of_year.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — TEST END TO END
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 ~/protocol_pulse/services/image_of_the_day.py

Verify:
- File exists at ~/protocol_pulse/data/social_queue/image_of_the_day.png
- Size > 100KB
- No errors

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
git add services/image_of_the_day.py
git commit -m "feat(image): FLUX.1-schnell local image generation — zero cost, no watermark, Protocol Pulse visual style, cuda:2"
git push

DO NOT touch: video pipeline, assembler, tts_engine, overnight_render_loop, routes.py
ONLY touch: services/image_of_the_day.py and pip installs