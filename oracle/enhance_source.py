"""Upscale avatar source image using Real-ESRGAN or GFPGAN for better Wav2Lip input."""
import cv2
import numpy as np
import os


def upscale_avatar_source(input_path, output_path, scale=2):
    """Try Real-ESRGAN first, fall back to GFPGAN, fall back to Lanczos."""
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError(f"Cannot read {input_path}")

    print(f"Input: {img.shape[1]}x{img.shape[0]}")

    enhanced = None

    # Try Real-ESRGAN (best for clean upscaling)
    try:
        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
        upsampler = RealESRGANer(
            scale=4,
            model_path='https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth',
            model=model,
            tile=0,
            tile_pad=10,
            pre_pad=0,
            half=True
        )
        enhanced, _ = upsampler.enhance(img, outscale=2)
        print(f"Real-ESRGAN output: {enhanced.shape[1]}x{enhanced.shape[0]}")
    except Exception as e:
        print(f"Real-ESRGAN failed: {e}")

    # Try GFPGAN (face-specific enhancement)
    if enhanced is None:
        try:
            from gfpgan import GFPGANer
            restorer = GFPGANer(
                model_path='https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth',
                upscale=2,
                arch='clean',
                channel_multiplier=2
            )
            _, _, enhanced = restorer.enhance(img, has_aligned=False, only_center_face=True, paste_back=True)
            print(f"GFPGAN output: {enhanced.shape[1]}x{enhanced.shape[0]}")
        except Exception as e:
            print(f"GFPGAN failed: {e}")

    # Fallback: high-quality Lanczos upscale
    if enhanced is None:
        target_size = (img.shape[1] * scale, img.shape[0] * scale)
        enhanced = cv2.resize(img, target_size, interpolation=cv2.INTER_LANCZOS4)
        print(f"Lanczos output: {enhanced.shape[1]}x{enhanced.shape[0]}")

    cv2.imwrite(output_path, enhanced)
    print(f"Saved: {output_path}")
    return enhanced


if __name__ == '__main__':
    src = os.path.expanduser('~/protocol_pulse/oracle/Proto_P_Avatar_512.png')
    dst = os.path.expanduser('~/protocol_pulse/oracle/Proto_P_Avatar_1024.png')
    upscale_avatar_source(src, dst, scale=2)
