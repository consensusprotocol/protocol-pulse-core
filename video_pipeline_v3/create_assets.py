#!/usr/bin/env python3
"""Step 2: Create all reusable video assets with FFmpeg."""
import subprocess, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def run(cmd, label=""):
    print(f"  [asset] {label}...")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"  [FAIL] {label}: {r.stderr[:500]}")
        return False
    return True

def verify(path, label=""):
    r = subprocess.run(f"ffprobe -v error -show_entries format=duration -of csv=p=0 '{path}'",
                       shell=True, capture_output=True, text=True)
    dur = r.stdout.strip()
    sz = os.path.getsize(path) if os.path.exists(path) else 0
    print(f"  [OK] {label}: {dur}s, {sz//1024}KB")
    return os.path.exists(path)

def create_transition():
    """0.5s red/black glitch transition."""
    out = os.path.join(ASSETS, "transitions", "glitch_transition.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # Red flash -> black with noise
    cmd = (
        f"ffmpeg -y -f lavfi -i color=c=black:s=1920x1080:d=0.5:r=30 "
        f"-f lavfi -i color=c=0xCC0000:s=1920x1080:d=0.5:r=30 "
        f"-f lavfi -i nullsrc=s=1920x1080:d=0.5:r=30,geq=random(1)*255:128:128 "
        f"-filter_complex \""
        f"[0:v][1:v]blend=all_expr='if(gt(T,0.15),A,B)':shortest=1[bg];"
        f"[bg][2:v]blend=all_expr='A*(1-0.3*B/255)+B*0.3':shortest=1[mix];"
        f"[mix]colorbalance=rs=0.5:gs=-0.3:bs=-0.3,"
        f"noise=alls=40:allf=t,format=yuv420p[out]\" "
        f"-map '[out]' -c:v libx264 -crf 18 -t 0.5 '{out}'"
    )
    if run(cmd, "glitch transition"):
        verify(out, "transition")
    return out

def create_lower_third_template():
    """Red accent bar lower third template (5s for testing)."""
    out = os.path.join(ASSETS, "lower_third_template.mp4")
    # Animated red bar sliding from left with headline text
    cmd = (
        f"ffmpeg -y -f lavfi -i color=c=0x0A0A0A@0.85:s=1920x120:d=3:r=30 "
        f"-f lavfi -i color=c=0xCC0000:s=8x120:d=3:r=30 "
        f"-filter_complex \""
        f"[1:v]pad=1920:120:0:0:0x0A0A0A@0.0[bar];"
        f"[0:v][bar]overlay=x='min(0,(-1920+t/0.3*1920))':y=0:shortest=1,"
        f"drawtext=fontfile={FONT_BOLD}:text='HEADLINE TEXT':"
        f"fontcolor=white:fontsize=38:x='max(20,(-1900+t/0.3*1920))':y=40:"
        f"enable='gt(t,0.1)',"
        f"drawtext=fontfile={FONT_MONO}:text='Source Channel':"
        f"fontcolor=0xCC0000:fontsize=24:x='max(20,(-1900+t/0.3*1920))':y=78:"
        f"enable='gt(t,0.15)',"
        f"format=yuv420p[out]\" "
        f"-map '[out]' -c:v libx264 -crf 18 '{out}'"
    )
    if run(cmd, "lower third template"):
        verify(out, "lower third")
    return out

def create_background():
    """Animated dark tech grid background with red pulse."""
    out = os.path.join(ASSETS, "backgrounds", "tech_grid.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # Dark background with grid lines and subtle red pulse
    cmd = (
        f"ffmpeg -y -f lavfi -i color=c=0x0A0A0A:s=1920x1080:d=10:r=30 "
        f"-filter_complex \""
        f"[0:v]drawgrid=w=60:h=60:t=1:c=0x1A1A1A@0.5,"
        f"drawgrid=w=300:h=300:t=2:c=0x2A0000@0.4,"
        f"colorbalance=rs='0.15*sin(2*PI*t/4)':gs=0:bs=0,"
        f"noise=alls=3:allf=t,"
        f"format=yuv420p[out]\" "
        f"-map '[out]' -c:v libx264 -crf 20 '{out}'"
    )
    if run(cmd, "tech grid background"):
        verify(out, "background")
    return out

def create_intro():
    """3-5 second Protocol Pulse branded intro with glitch text reveal."""
    out = os.path.join(ASSETS, "intro.mp4")
    # Dark background, red glow, text appears with glitch
    cmd = (
        f"ffmpeg -y -f lavfi -i color=c=0x050505:s=1920x1080:d=4:r=30 "
        f"-f lavfi -i 'anoisesrc=d=4:c=pink:r=44100:a=0.03' "
        f"-filter_complex \""
        f"[0:v]drawgrid=w=80:h=80:t=1:c=0x1A0000@0.3,"
        # Red glow circle in center
        f"drawbox=x=860:y=440:w=200:h=200:c=0xCC0000@'0.3*sin(2*PI*t/2)':t=fill,"
        f"gblur=sigma='10+5*sin(2*PI*t/2)',"
        # Main title - appears at 0.8s
        f"drawtext=fontfile={FONT_BOLD}:text='PULSE CHECK':"
        f"fontcolor=white:fontsize=96:"
        f"x=(w-text_w)/2:y=(h-text_h)/2-40:"
        f"enable='gt(t,0.8)':alpha='min(1,(t-0.8)/0.3)',"
        # Subtitle
        f"drawtext=fontfile={FONT_MONO}:text='Bitcoin Intelligence Daily':"
        f"fontcolor=0xCC0000:fontsize=32:"
        f"x=(w-text_w)/2:y=(h/2+40):"
        f"enable='gt(t,1.3)':alpha='min(1,(t-1.3)/0.3)',"
        # Glitch noise overlay in first 1.5s
        f"noise=alls='80*max(0,1-t/1.5)':allf=t,"
        f"format=yuv420p[v];"
        # Bass hit sound
        f"[1:a]lowpass=f=200,volume=2[a]\" "
        f"-map '[v]' -map '[a]' -c:v libx264 -crf 18 -c:a aac -shortest '{out}'"
    )
    if run(cmd, "intro"):
        verify(out, "intro")
    return out

def create_outro():
    """5-second outro with Protocol Pulse branding."""
    out = os.path.join(ASSETS, "outro.mp4")
    cmd = (
        f"ffmpeg -y -f lavfi -i color=c=0x050505:s=1920x1080:d=5:r=30 "
        f"-f lavfi -i 'anoisesrc=d=5:c=pink:r=44100:a=0.02' "
        f"-filter_complex \""
        f"[0:v]drawgrid=w=80:h=80:t=1:c=0x1A0000@0.3,"
        f"drawtext=fontfile={FONT_BOLD}:text='PROTOCOL PULSE':"
        f"fontcolor=white:fontsize=72:"
        f"x=(w-text_w)/2:y=(h-text_h)/2-60:"
        f"alpha='min(1,t/0.5)',"
        f"drawtext=fontfile={FONT_MONO}:text='Stay Sovereign.':"
        f"fontcolor=0xCC0000:fontsize=36:"
        f"x=(w-text_w)/2:y=(h/2+10):"
        f"enable='gt(t,0.8)':alpha='min(1,(t-0.8)/0.4)',"
        f"drawtext=fontfile={FONT_MONO}:text='protocolpulse.io':"
        f"fontcolor=0x888888:fontsize=24:"
        f"x=(w-text_w)/2:y=(h/2+70):"
        f"enable='gt(t,1.5)':alpha='min(1,(t-1.5)/0.4)',"
        f"noise=alls=3:allf=t,"
        f"format=yuv420p[v];"
        f"[1:a]lowpass=f=300,volume=1.5,afade=t=out:st=3.5:d=1.5[a]\" "
        f"-map '[v]' -map '[a]' -c:v libx264 -crf 18 -c:a aac -shortest '{out}'"
    )
    if run(cmd, "outro"):
        verify(out, "outro")
    return out

def create_watermark():
    """Small semi-transparent Protocol Pulse watermark PNG."""
    out = os.path.join(ASSETS, "logo", "watermark.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = (
        f"ffmpeg -y -f lavfi -i color=c=0x000000@0.0:s=280x40 "
        f"-vf \"drawtext=fontfile={FONT_BOLD}:text='PROTOCOL PULSE':"
        f"fontcolor=white@0.35:fontsize=22:x=10:y=10,format=rgba\" "
        f"-frames:v 1 '{out}'"
    )
    run(cmd, "watermark")
    return out

def main():
    print("=" * 60)
    print("STEP 2: CREATING REUSABLE ASSETS")
    print("=" * 60)
    create_transition()
    create_lower_third_template()
    create_background()
    create_intro()
    create_outro()
    create_watermark()
    print("\n[DONE] All assets created.")

if __name__ == "__main__":
    main()
