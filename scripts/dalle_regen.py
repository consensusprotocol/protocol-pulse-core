"""
DALL-E 3 image regeneration for last 20 articles.
Runs in background, uses no GPU, rate-limited to 1 image per 15 seconds.
Updates cover_image_url in DB via Flask app context.
"""
import sys, os, time, requests, base64
from io import BytesIO
from PIL import Image

sys.path.insert(0, '/home/ultron/protocol_pulse/core')
os.chdir('/home/ultron/protocol_pulse/core')
from dotenv import load_dotenv
load_dotenv('/home/ultron/protocol_pulse/.env')

from app import app, db
from models import Article

OPENAI_KEY = os.environ.get('OPENAI_API_KEY', '')
IMG_SAVE_DIR = '/home/ultron/protocol_pulse/static/images/articles'
os.makedirs(IMG_SAVE_DIR, exist_ok=True)

# Protocol Pulse brand prompt — cinematic, dark, Bitcoin-native
BRAND_PROMPT = (
    "Cinematic editorial photograph. Dark dramatic lighting. "
    "Deep reds, blacks, and amber tones. Hyper-realistic photojournalism. "
    "Professional photography. No text, no logos, no watermarks, no borders. "
    "Full bleed edge-to-edge composition. Subject: {topic}"
)

def generate_dalle_image(title, article_id):
    """Generate DALL-E 3 HD image for an article."""
    # Extract topic essence from title
    topic = title[:120]
    prompt = BRAND_PROMPT.format(topic=f"Bitcoin/cryptocurrency news story about: {topic}")
    
    try:
        resp = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json={
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": "1792x1024",
                "quality": "hd"
            },
            timeout=90
        )
        
        if resp.status_code == 200:
            data = resp.json()
            item = data.get('data', [{}])[0]
            
            if 'url' in item:
                # Download and save locally
                img_resp = requests.get(item['url'], timeout=30)
                if img_resp.ok:
                    filename = f"article_{article_id}_dalle.jpg"
                    filepath = os.path.join(IMG_SAVE_DIR, filename)
                    img = Image.open(BytesIO(img_resp.content)).convert('RGB')
                    img.save(filepath, 'JPEG', quality=90, optimize=True)
                    return f"/static/images/articles/{filename}"
            elif 'b64_json' in item:
                filename = f"article_{article_id}_dalle.jpg"
                filepath = os.path.join(IMG_SAVE_DIR, filename)
                img = Image.open(BytesIO(base64.b64decode(item['b64_json']))).convert('RGB')
                img.save(filepath, 'JPEG', quality=90, optimize=True)
                return f"/static/images/articles/{filename}"
        else:
            print(f"  DALL-E error {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"  Error: {e}")
    return None

def main():
    print("=" * 60)
    print("DALL-E 3 Article Image Regeneration")
    print("Targeting last 20 articles for on-brand imagery")
    print("Rate: 1 image/15s, no GPU usage")
    print("=" * 60)
    
    with app.app_context():
        articles = Article.query.filter_by(published=True)\
            .order_by(Article.created_at.desc())\
            .limit(20).all()
        
        print(f"Found {len(articles)} articles to process")
        
        for i, article in enumerate(articles):
            print(f"\n[{i+1}/20] {article.title[:60]}...")
            print(f"  Current image: {'pexels' in (article.cover_image_url or '') and 'stock' or article.cover_image_url and 'custom' or 'none'}")
            
            img_url = generate_dalle_image(article.title, article.id)
            
            if img_url:
                article.cover_image_url = img_url
                db.session.commit()
                print(f"  ✓ DALL-E image saved: {img_url}")
            else:
                print(f"  ✗ Failed — keeping existing image")
            
            # Rate limit: 4 images/minute (well under OpenAI limit)
            if i < len(articles) - 1:
                print(f"  Waiting 15s...")
                time.sleep(15)
    
    print("\n" + "=" * 60)
    print("DALL-E regeneration complete!")
    print("=" * 60)

if __name__ == '__main__':
    main()
