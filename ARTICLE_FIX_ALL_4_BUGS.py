#!/usr/bin/env python3
"""
PROTOCOL PULSE — COMPREHENSIVE ARTICLE SYSTEM FIX
Run this once in your Replit shell: python3 ARTICLE_FIX_ALL_4_BUGS.py

Fixes all 4 bugs identified by Grok + Perplexity audits:
  BUG 1: Duplicate topic flooding (_is_topic_oversaturated never called)
  BUG 2: Same header image (get_article_header_url returns default)
  BUG 3: Featured article broken image (wrong variable in template)
  BUG 4: Auto-publish not working (published flag never set in return dict)
"""

import re, os, sys, shutil
from datetime import datetime

BACKUP_SUFFIX = f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup(filepath):
    if os.path.exists(filepath):
        shutil.copy2(filepath, filepath + BACKUP_SUFFIX)
        print(f"  backed up {filepath}")

def read(filepath):
    with open(filepath, 'r') as f:
        return f.read()

def write(filepath, content):
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"  wrote {filepath}")

# ============================================================
# BUG 1: Duplicate topic flooding
# ============================================================
print("\n" + "="*60)
print("BUG 1: DUPLICATE TOPIC FLOODING")
print("="*60)

filepath = "services/article_automation.py"
backup(filepath)
content = read(filepath)

# Step 1A: Replace _is_topic_oversaturated with time-based version
NEW_TOPIC_FUNC = '''def _is_topic_oversaturated(title, max_same=1, hours=24):
    """Check if topic was covered in the last `hours`. Returns True to skip."""
    try:
        import models
        from app import db
        from datetime import datetime, timedelta
        import logging

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = (
            models.Article.query
            .filter(models.Article.created_at >= cutoff)
            .order_by(models.Article.created_at.desc())
            .all()
        )

        new_topic = _detect_topic(title)
        if new_topic == "general":
            return False

        count = sum(1 for a in recent if _detect_topic(a.title) == new_topic)
        if count >= max_same:
            logging.getLogger("article_automation").info(
                f"TOPIC DIVERSITY: Skipping '{title[:80]}' -- topic '{new_topic}' "
                f"already covered {count}x in last {hours}h"
            )
            return True
        return False
    except Exception as e:
        import logging
        logging.getLogger("article_automation").warning(
            f"Topic cooldown check failed for '{title[:80]}': {e}"
        )
        return False'''

# Find existing function with flexible matching
match = re.search(
    r'def _is_topic_oversaturated\(.*?\).*?(?=\ndef |\nclass |\Z)',
    content, re.DOTALL
)
if match:
    content = content.replace(match.group(0), NEW_TOPIC_FUNC)
    print("  FIXED: _is_topic_oversaturated now uses 24h time window")
else:
    print("  WARNING: _is_topic_oversaturated not found")

# Step 1B: Inject topic cooldown HARD GATE into run_article_generation_cycle
cycle_marker = 'def run_article_generation_cycle'
if cycle_marker in content:
    cycle_section = content[content.find(cycle_marker):]
    first_func_body = cycle_section.split('\ndef ')[0] if '\ndef ' in cycle_section else cycle_section
    if '_is_topic_oversaturated' not in first_func_body:
        cycle_start = content.find(cycle_marker)
        article_create = content.find('article = Article(', cycle_start)
        if article_create < 0:
            article_create = content.find('Article(', cycle_start)

        if article_create >= 0:
            line_start = content.rfind('\n', cycle_start, article_create) + 1
            indent = ''
            for ch in content[line_start:]:
                if ch in (' ', '\t'):
                    indent += ch
                else:
                    break

            gate_code = "\n"
            gate_code += indent + "# HARD GATE: 24h topic cooldown\n"
            gate_code += indent + "_check_title = locals().get('final_title') or (generated.get('title', '') if isinstance(locals().get('generated'), dict) else '')\n"
            gate_code += indent + "if _check_title and _is_topic_oversaturated(_check_title, max_same=1, hours=24):\n"
            gate_code += indent + "    logger.info('Skipping article due to 24h topic cooldown: ' + repr(_check_title[:120]))\n"
            gate_code += indent + "    return {'success': False, 'skipped': True, 'reason': 'topic_oversaturated', 'title': _check_title}\n"
            gate_code += "\n"

            content = content[:line_start] + gate_code + content[line_start:]
            print("  FIXED: Injected topic cooldown HARD GATE before Article() creation")
        else:
            print("  WARNING: Could not find Article() creation in run_article_generation_cycle")
    else:
        print("  OK: Topic cooldown already present in run_article_generation_cycle")
else:
    print("  WARNING: run_article_generation_cycle not found")

write(filepath, content)

# ============================================================
# BUG 2: Same header image for every article
# ============================================================
print("\n" + "="*60)
print("BUG 2: SAME HEADER IMAGE")
print("="*60)

# Fix 2A: content_generator.py - get_article_header_url
filepath = "services/content_generator.py"
if os.path.exists(filepath):
    backup(filepath)
    content = read(filepath)

    new_func = '''def get_article_header_url(title: str, article_html: str = "") -> str:
    """
    Resolve a per-article header image using the full pipeline:
    1) AI header via image_service (title + summary)
    2) Deterministic pick from local pool as fallback
    """
    try:
        header, src_url, src_type = resolve_header_image_url(title, article_html)
        if header and header != "/static/images/default-header.png":
            return header
    except Exception:
        pass

    # Final fallback: deterministic pick from local pool based on title hash
    import hashlib
    pool = ARTICLE_HEADER_IMAGE_POOL or ["/static/images/default-header.png"]
    idx = int(hashlib.md5(title.encode("utf-8")).hexdigest(), 16) % len(pool)
    return pool[idx]'''

    match = re.search(
        r'def get_article_header_url\(.*?\).*?(?=\ndef |\nclass |\Z)',
        content, re.DOTALL
    )
    if match:
        content = content.replace(match.group(0), new_func)
        write(filepath, content)
        print("  FIXED: get_article_header_url now uses real image pipeline")
    else:
        print("  WARNING: get_article_header_url not found in content_generator.py")
else:
    print(f"  WARNING: {filepath} not found")

# Fix 2B: image_service.py - Add uniqueness seed to DALL-E prompts
filepath = "services/image_service.py"
if os.path.exists(filepath):
    backup(filepath)
    content = read(filepath)

    if "variation_seed" not in content and "unique photographic" not in content:
        func_match = re.search(r'def generate_article_header_image\(self.*?\):', content)
        if func_match:
            func_start = func_match.end()
            prompt_match = re.search(r'(\n(\s+))(prompt\s*=\s*)', content[func_start:])
            if prompt_match:
                inject_point = func_start + prompt_match.start()
                indent = prompt_match.group(2)

                seed_block = "\n"
                seed_block += indent + "# Uniqueness seed to prevent identical DALL-E outputs\n"
                seed_block += indent + "import hashlib as _hl, time as _tm\n"
                seed_block += indent + 'variation_seed = _hl.sha256((str(title) + "|" + str(_tm.time())).encode()).hexdigest()[:12]\n'

                content = content[:inject_point] + seed_block + content[inject_point:]

                # Find the prompt line after our insertion and append seed suffix
                new_func_start = func_match.end() + len(seed_block)
                prompt_line_match = re.search(r'(\n(\s+)prompt\s*=\s*.*)', content[new_func_start:])
                if prompt_line_match:
                    prompt_line_end = new_func_start + prompt_line_match.end()
                    append_indent = prompt_line_match.group(2)
                    append_line = "\n" + append_indent + 'prompt = prompt + " unique photographic composition id " + variation_seed + ", cinematic color grade, dramatic lighting"'
                    content = content[:prompt_line_end] + append_line + content[prompt_line_end:]

                write(filepath, content)
                print("  FIXED: Added uniqueness seed to DALL-E image prompts")
            else:
                print("  WARNING: Could not find prompt construction in generate_article_header_image")
        else:
            print("  WARNING: generate_article_header_image not found")
    else:
        print("  OK: Uniqueness seed already present")
else:
    print(f"  WARNING: {filepath} not found")

# ============================================================
# BUG 3: Featured article broken image
# ============================================================
print("\n" + "="*60)
print("BUG 3: FEATURED ARTICLE BROKEN IMAGE")
print("="*60)

filepath = "templates/articles.html"
if os.path.exists(filepath):
    backup(filepath)
    content = read(filepath)

    fixes_applied = 0

    for bad, good in [
        ('featured.image_url', "featured.header_image_url or '/static/images/default-header.png'"),
        ('featured_article.image_url', "featured_article.header_image_url or '/static/images/default-header.png'"),
    ]:
        if bad in content:
            content = content.replace(bad, good)
            fixes_applied += 1
            print(f"  FIXED: {bad} -> header_image_url with fallback")

    # Ensure existing header_image_url refs have fallback
    pattern = r"""src="\{\{\s*(featured(?:_article)?\.header_image_url)\s*\}\}"""
    replacement = r"""src="{{ \1 or '/static/images/default-header.png' }}" """
    new_content = re.sub(pattern, replacement, content)
    if new_content != content:
        content = new_content
        fixes_applied += 1
        print("  FIXED: Added default fallback to existing header_image_url references")

    write(filepath, content)
    if fixes_applied == 0:
        print("  No known bad patterns found. Current image lines in template:")
        for i, line in enumerate(content.split('\n'), 1):
            ll = line.lower()
            if ('hero' in ll or 'featured' in ll) and ('img' in ll or 'src' in ll or 'image' in ll):
                print(f"    Line {i}: {line.strip()[:140]}")
    else:
        print(f"  Total: {fixes_applied} pattern(s) fixed")
else:
    print(f"  WARNING: {filepath} not found")

# ============================================================
# BUG 4: Auto-publish not working
# ============================================================
print("\n" + "="*60)
print("BUG 4: AUTO-PUBLISH NOT WORKING")
print("="*60)

filepath = "services/article_automation.py"
content = read(filepath)

cycle_marker = 'def run_article_generation_cycle'
if cycle_marker in content:
    cycle_start = content.find(cycle_marker)
    next_def = content.find('\ndef ', cycle_start + 10)
    if next_def < 0:
        next_def = len(content)
    cycle_func = content[cycle_start:next_def]

    has_published_return = (
        '"published": True' in cycle_func
        or "'published': True" in cycle_func
        or 'result["published"]' in cycle_func
        or "result['published']" in cycle_func
    )

    if has_published_return:
        print("  OK: run_article_generation_cycle already returns published flag")
    else:
        if 'should_publish' in cycle_func:
            if '"published": should_publish' not in cycle_func:
                match = re.search(r'(return\s*\{[^}]*"article_id"[^}]*)(})', cycle_func)
                if match:
                    old_return = match.group(0)
                    new_return = match.group(1) + ', "published": should_publish' + match.group(2)
                    content = content.replace(old_return, new_return, 1)
                    print("  FIXED: Added published: should_publish to return dict")
                else:
                    print("  WARNING: Could not find return dict with article_id")
            else:
                print("  OK: should_publish already in return dict")
        else:
            commit_pos_in_func = cycle_func.find('db.session.commit()')
            if commit_pos_in_func > 0:
                abs_commit = cycle_start + commit_pos_in_func
                line_start = content.rfind('\n', 0, abs_commit) + 1
                indent = ''
                for ch in content[line_start:]:
                    if ch in (' ', '\t'):
                        indent += ch
                    else:
                        break
                insert_code = "\n"
                insert_code += indent + "# Auto-publish gate\n"
                insert_code += indent + 'auto_publish_enabled = os.environ.get("ENABLE_AUTO_PUBLISH", "").lower() == "true"\n'
                insert_code += indent + "if auto_publish_enabled:\n"
                insert_code += indent + "    article.published = True\n\n"
                content = content[:abs_commit] + insert_code + content[abs_commit:]
                print("  FIXED: Added auto-publish gate before db.session.commit()")
            else:
                print("  WARNING: No db.session.commit() found in run_article_generation_cycle")

    write(filepath, content)
else:
    print("  WARNING: run_article_generation_cycle not found")

print("\n  Required env vars (set in Replit Secrets):")
print("     ENABLE_AUTO_PUBLISH=true")
print("     ENABLE_ARTICLE_AUTOMATION_15M=true")
print("     AUTOPOST_X=true  (optional)")

# ============================================================
# BONUS: Fix ai_service.py system_prompt
# ============================================================
print("\n" + "="*60)
print("BONUS: AI SERVICE system_prompt FIX")
print("="*60)

filepath = "services/ai_service.py"
if os.path.exists(filepath):
    backup(filepath)
    content = read(filepath)

    old_hardcoded = '{"role": "system", "content": "You are an investigative journalist for Protocol Pulse."}'
    new_dynamic = '{"role": "system", "content": system_prompt or "You are an investigative journalist for Protocol Pulse."}'

    if old_hardcoded in content:
        content = content.replace(old_hardcoded, new_dynamic)
        write(filepath, content)
        print("  FIXED: ai_service.py now honors system_prompt parameter")
    else:
        print("  OK: system_prompt already honored or pattern differs")
else:
    print(f"  WARNING: {filepath} not found")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "="*60)
print("FIX COMPLETE")
print("="*60)
print("")
print("Backups created with timestamp suffix.")
print("")
print("NEXT STEPS:")
print("  1. Restart automation:")
print("     pkill -f master_automation")
print("     export ENABLE_AUTO_PUBLISH=true")
print("     export ENABLE_ARTICLE_AUTOMATION_15M=true")
print("     nohup python3 master_automation.py > logs/master_automation.log 2>&1 &")
print("")
print("  2. Watch logs:")
print("     tail -f logs/master_automation.log")
print("")
print("  3. Check /articles page for correct images")
print("")
print("Paste any WARNING output back here and I will fix it manually.")