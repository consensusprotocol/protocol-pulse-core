#!/usr/bin/env python3
"""Social stack, signal active, space tap, and social card visual rendering."""
import math
import os
import subprocess
import tempfile

from assembler_common import (
    logger, run_ffmpeg, run_ffmpeg_filtergraph, ffprobe_duration,
    BASE, ASSETS, FONT_BOLD, FONT_MONO,
    COLOR_BG, COLOR_RED, COLOR_WHITE, COLOR_TEXT, COLOR_GOLD, COLOR_MUTED, COLOR_MUTED2,
    COLOR_PANEL, COLOR_PANEL2, COLOR_GREEN, COLOR_CORAL,
    WATERMARK, CARD_SWOOSH,
    _whoosh_applied_parts,
    _sanitize_text, _word_wrap, _split_headline_for_render, _get_live_metric,
    _is_nostr_spam_assembler,
    _get_bg_layer, _build_top_system_bar, _build_corner_brackets_fg,
    _build_black_diamond_bg, _build_info_bar_fg,
    _build_narration_wave, _build_signature_info_rail,
    _add_episode_title_pill, _ken_burns_motion, apply_scanline,
    _bv2_encode,
)
from render_clip import _remotion_enabled, _render_remotion, _remotion_with_audio

# Module-level color constants used by make_signal_active_scene
COLOR_NOSTR   = "0x00ff9d"
COLOR_SIG_RED = "0xff3b5f"


def _rank_cards_for_segment(cards: list, segment_text: str) -> list:
    """Session 4 Fix 4: Rank tweet cards by relevance to narrator text."""
    if not cards or not segment_text:
        return cards
    words = set(segment_text.lower().split())
    def score(card):
        card_words = set((card.get('text', '') + ' ' + card.get('handle', '')).lower().split())
        return len(words & card_words)
    return sorted(cards, key=score, reverse=True)


def make_social_stack_scene(audio_path: str, headline: str, social_cards: list,
                             output_path: str, btc_price: str = "N/A",
                             duration: float = 0,
                             card_timings: list = None,
                             episode_title: str = "PULSE CHECK") -> str:
    """APEX Social Stack — FIX 4: cards LOCKED to TTS timing.

    Cards appear/disappear synchronized with narration. Each card is visible
    only during its time slice. Active card: red border + full opacity.
    Past/future cards: dim panel + muted opacity.
    """
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = duration if duration > 0 else audio_dur + 0.3

    inputs = [audio_path]
    fg = _get_bg_layer(inputs, total_dur, "bb_bg")

    fg += _build_top_system_bar("bb_bg", "bv2_bar", progress_pct=58)

    # Header zone with gold eyebrow — Render24 FIX 7: universal 2-line wrap
    _ss_head = _sanitize_text(headline)
    _ss_l1, _ss_l2 = _split_headline_for_render(_ss_head)
    _ss_fs = 34 if _ss_l2 else 48
    fg += (f"[bv2_bar]drawtext=fontfile={FONT_MONO}:text='SIGNAL LAYER':"
           f"fontcolor={COLOR_GOLD}:fontsize=13:x=64:y=100,"
           f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_ss_l1)}':"
           f"fontcolor={COLOR_WHITE}:fontsize={_ss_fs}:x=64:y=130,")
    if _ss_l2:
        fg += (f"drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_ss_l2)}':"
               f"fontcolor={COLOR_WHITE}:fontsize={_ss_fs}:x=64:y={130 + 65},")
    fg += (f"drawtext=fontfile={FONT_MONO}:text='Bitcoin Social Conviction Index':"
           f"fontcolor=0xFFFFFF@0.5:fontsize=16:x=64:y=200"
           f"[ss_hdr];\n")

    # FIX 4: No default/fake cards — require real social_cards, minimum 3
    if not social_cards or len(social_cards) < 3:
        logger.warning(f"[SOCIAL] social_cards has {len(social_cards) if social_cards else 0} cards (minimum 3) — skipping social stack")
        return ""

    # FIX 4: Up to 5 cards, CARD ORDER LOCK — preserve script_writer order, never re-sort
    cards = social_cards[:5]
    n_cards = len(cards)

    # FIX 4: Calculate per-card timing — divide narration evenly across cards
    if card_timings and len(card_timings) >= n_cards:
        timings = card_timings[:n_cards]
    else:
        tpc = total_dur / n_cards if n_cards > 0 else total_dur
        timings = [(i * tpc, (i + 1) * tpc) for i in range(n_cards)]

    tags = ["HIGH CONVICTION", "STRUCTURAL", "MACRO SIGNAL", "NETWORK", "ADOPTION"]
    last = "ss_hdr"
    # FIX 4: Dynamic card width for up to 5 cards
    _card_gap = 12
    _total_card_w = 1920 - 128  # 64px margin each side
    cw = (_total_card_w - (n_cards - 1) * _card_gap) // n_cards
    for ci, card in enumerate(cards):
        cx = 64 + ci * (cw + _card_gap)
        cy = 300
        ch = 620

        t_start, t_end = timings[ci]
        # FIX 4: Active card = red border + full text; inactive = dim panel
        # Use enable expressions for active state highlighting
        active_enable = f"enable='between(t,{t_start:.2f},{t_end:.2f})'"
        inactive_enable = f"enable='not(between(t,{t_start:.2f},{t_end:.2f}))'"

        name = _sanitize_text(str(card.get("name", card.get("handle", "Source"))))[:20]
        handle = _sanitize_text(str(card.get("handle", "@source")))[:20]
        score = str(card.get("score", card.get("likes", "80")))[:6]
        ctext = _word_wrap(_sanitize_text(str(card.get("text", ""))), max_width=36, max_lines=7)
        ctag = _sanitize_text(str(card.get("tag", tags[ci % 3])))[:20]

        out = f"ss_sc{ci}"
        # Card background (always visible but dimmed when inactive)
        fg += (f"[{last}]drawbox=x={cx}:y={cy}:w={cw}:h={ch}:color={COLOR_PANEL}@0.92:t=fill,"
               # Active: red border
               f"drawbox=x={cx}:y={cy}:w={cw}:h={ch}:color={COLOR_RED}@0.4:t=2:{active_enable},"
               # Inactive: subtle white border
               f"drawbox=x={cx}:y={cy}:w={cw}:h={ch}:color=0xFFFFFF@0.08:t=2:{inactive_enable},"
               # Avatar placeholder
               f"drawbox=x={cx+24}:y={cy+24}:w=44:h=44:color={COLOR_RED}@0.5:t=fill,"
               # Name
               f"drawtext=fontfile={FONT_BOLD}:text='{name}':"
               f"fontcolor={COLOR_WHITE}:fontsize=16:x={cx+80}:y={cy+28},"
               # Handle
               f"drawtext=fontfile={FONT_MONO}:text='{handle}':"
               f"fontcolor=0xFFFFFF@0.35:fontsize=12:x={cx+80}:y={cy+50},"
               # VDS gold score badge
               f"drawbox=x={cx+cw-90}:y={cy+28}:w=70:h=24:color={COLOR_GOLD}@0.15:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='{score} / 100':"
               f"fontcolor={COLOR_GOLD}:fontsize=11:x={cx+cw-84}:y={cy+34},"
               # Quote text
               f"drawtext=fontfile={FONT_BOLD}:text='{ctext}':"
               f"fontcolor={COLOR_WHITE}:fontsize=17:x={cx+24}:y={cy+90}:line_spacing=10,"
               # VDS gold tag label at bottom
               f"drawtext=fontfile={FONT_MONO}:text='{ctag}':"
               f"fontcolor={COLOR_GOLD}:fontsize=11:x={cx+24}:y={cy+ch-36},"
               # Active indicator: "ACTIVE" tag when card is current
               f"drawtext=fontfile={FONT_MONO}:text='ACTIVE':"
               f"fontcolor={COLOR_RED}:fontsize=11:x={cx+cw-70}:y={cy+ch-36}:{active_enable}"
               f"[{out}];\n")
        last = out

    fg += _build_corner_brackets_fg(last, "ss_corners")
    wave_fg, ss_audio_pad = _build_narration_wave("ss_corners", "ss_wave", "ss_a_out")
    fg += wave_fg
    fg += _build_signature_info_rail(total_dur, btc_price, "ss_wave", "ss_railed")
    # FIX 3: Episode title pill
    fg += _add_episode_title_pill("ss_railed", "_ss_pilled", episode_title, total_dur)
    fg += _ken_burns_motion("_ss_pilled", "outv", total_dur)

    return _bv2_encode(inputs, fg, output_path, total_dur, "APEX social stack",
                       audio_pad=ss_audio_pad)


def make_space_tap_scene(audio_path: str, space_clips: list,
                          output_path: str, btc_price: str = "N/A",
                          duration: float = 0,
                          episode_title: str = "PULSE CHECK") -> str:
    """Space Tap portal scene — plays X Spaces audio clips with branded intercept UI.

    Layout (1920x1080):
      LEFT (0-760): bg_loop grayscale, "SPACE TAP" header, speaker handle,
                    waveform visualization, BTC ticker
      RIGHT (760-1920): dark portal frame with red glow, profile picture,
                        "INTERCEPTED TRANSMISSION" label, waveform arc

    Each clip section: PBX intro → portal opens → clip plays → portal closes → PBX reaction.
    Audio: narrator at 0dB, clip audio at 0dB, bg music handled in concatenate_parts().
    """
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 10
    total_dur = duration if duration > 0 else audio_dur + 0.3

    n_clips = len(space_clips) if space_clips else 0
    safe_btc = _sanitize_text(btc_price) if btc_price else "$N/A"

    inputs = [audio_path]
    fg = _get_bg_layer(inputs, total_dur, "base")

    fg += _build_top_system_bar("base", "st_bar", progress_pct=70)

    # === LEFT PANEL (x=0..760) ===
    # "SPACE TAP" header in red mono
    fg += (f"[st_bar]drawtext=fontfile={FONT_MONO}:text='SPACE TAP':"
           f"fontcolor={COLOR_RED}:fontsize=36:x=40:y=100,"
           # Sub-label in gold
           f"drawtext=fontfile={FONT_MONO}:text='SIGNAL INTERCEPT // LIVE ECOSPHERE':"
           f"fontcolor={COLOR_GOLD}:fontsize=12:x=40:y=145,"
           # "via X Spaces" muted label
           f"drawtext=fontfile={FONT_MONO}:text='via X Spaces':"
           f"fontcolor=0xFFFFFF@0.4:fontsize=14:x=40:y=170[st_left_labels];\n")

    # Speaker handles — stack up to 4 handles
    last = "st_left_labels"
    if space_clips:
        handles_text = ""
        for i, clip in enumerate(space_clips[:4]):
            handle = clip.get("host_handle", "unknown")
            handles_text += f"@{handle}  "
        safe_handles = _sanitize_text(handles_text.strip())
        fg += (f"[{last}]drawtext=fontfile={FONT_BOLD}:text='{safe_handles}':"
               f"fontcolor={COLOR_WHITE}:fontsize=22:x=40:y=220[st_handles];\n")
        last = "st_handles"
    else:
        fg += f"[{last}]copy[st_handles];\n"
        last = "st_handles"

    # Waveform visualization on left panel — showwaves cline
    fg += (f"[0:a]asplit=3[_st_a_wave][_st_a_wave2][_st_a_out];\n")
    fg += (f"[_st_a_wave]showwaves=s=640x120:mode=cline:"
           f"colors={COLOR_RED}@0.8|{COLOR_RED}@0.4:scale=sqrt:draw=full:rate=30,"
           f"format=rgba[st_waveform];\n")
    fg += f"[{last}][st_waveform]overlay=40:520:shortest=1[st_waved];\n"

    # BTC price ticker at bottom-left
    fg += (f"[st_waved]drawtext=fontfile={FONT_MONO}:text='BTC {safe_btc}':"
           f"fontcolor={COLOR_GOLD}:fontsize=16:x=40:y=700,"
           f"drawtext=fontfile={FONT_MONO}:text='PROTOCOL PULSE':"
           f"fontcolor={COLOR_RED}@0.5:fontsize=12:x=40:y=725[st_left_done];\n")

    # === RIGHT PANEL (x=760..1920): Portal frame ===
    # Dark portal background
    fg += (f"[st_left_done]"
           f"drawbox=x=780:y=80:w=1100:h=920:color=0x0A0A0F@0.92:t=fill[st_portal_bg];\n")

    # Portal border — pulsing red glow (1Hz pulse via enable)
    fg += (f"[st_portal_bg]"
           # Outer border always visible
           f"drawbox=x=780:y=80:w=1100:h=920:color={COLOR_RED}@0.3:t=4,"
           # Inner glow pulse at 1Hz
           f"drawbox=x=784:y=84:w=1092:h=912:color={COLOR_RED}@0.15:t=2:"
           f"enable='lt(mod(t\\,1)\\,0.5)',"
           # "INTERCEPTED TRANSMISSION" label
           f"drawtext=fontfile={FONT_MONO}:text='INTERCEPTED TRANSMISSION':"
           f"fontcolor={COLOR_RED}:fontsize=11:x=1120:y=100,"
           # "SPACE ACTIVE" indicator top-right with red dot
           f"drawbox=x=1780:y=96:w=8:h=8:color={COLOR_RED}:t=fill:"
           f"enable='lt(mod(t\\,1)\\,0.7)',"
           f"drawtext=fontfile={FONT_MONO}:text='SPACE ACTIVE':"
           f"fontcolor={COLOR_RED}@0.7:fontsize=10:x=1700:y=96"
           f"[st_portal_frame];\n")

    # Profile picture overlay (if available, first clip's profile)
    has_profile = False
    if space_clips:
        profile_path = space_clips[0].get("host_profile_image", "")
        if profile_path and os.path.exists(profile_path) and os.path.getsize(profile_path) > 100:
            has_profile = True
            inputs.append(profile_path)
            prof_idx = len(inputs) - 1
            # Scale to 320x320, circular crop via geq (approximate with drawbox mask)
            fg += (f"[{prof_idx}:v]scale=320:320,setsar=1,format=rgba,"
                   f"geq=lum='lum(X\\,Y)':cb='cb(X\\,Y)':cr='cr(X\\,Y)':"
                   f"a='if(lt(hypot(X-160\\,Y-160)\\,155)\\,255\\,0)'[st_profile];\n")
            # Overlay profile centered in portal (x=1340-160=1180, y=380-160=220 → adjusted for portal)
            fg += f"[st_portal_frame][st_profile]overlay=1180:260:shortest=1[st_with_profile];\n"
            # Pulsing ring around profile
            fg += (f"[st_with_profile]"
                   f"drawbox=x=1175:y=255:w=330:h=330:color={COLOR_RED}@0.35:t=3:"
                   f"enable='lt(mod(t\\,1)\\,0.5)',"
                   f"drawbox=x=1175:y=255:w=330:h=330:color={COLOR_RED}@0.2:t=3:"
                   f"enable='gte(mod(t\\,1)\\,0.5)'"
                   f"[st_profiled];\n")

    if not has_profile:
        # No profile — placeholder box
        fg += (f"[st_portal_frame]"
               f"drawbox=x=1180:y=260:w=320:h=320:color={COLOR_RED}@0.15:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='SIGNAL':"
               f"fontcolor={COLOR_RED}@0.3:fontsize=28:x=1280:y=400[st_profiled];\n")

    # Secondary waveform arc below profile in portal
    fg += (f"[_st_a_wave2]showwaves=s=600x80:mode=cline:"
           f"colors={COLOR_RED}@0.6|{COLOR_WHITE}@0.3:scale=sqrt:draw=full:rate=30,"
           f"format=rgba[st_portal_wave];\n")
    fg += f"[st_profiled][st_portal_wave]overlay=1040:640:shortest=1[st_portal_done];\n"

    # 2px red divider between left and right panels
    fg += (f"[st_portal_done]drawbox=x=758:y=0:w=2:h=1080:color={COLOR_RED}:t=fill"
           f"[st_divided];\n")

    fg += _build_corner_brackets_fg("st_divided", "st_corners")
    fg += _build_signature_info_rail(total_dur, btc_price, "st_corners", "st_railed")
    fg += _add_episode_title_pill("st_railed", "_st_pilled", episode_title, total_dur)
    fg += _ken_burns_motion("_st_pilled", "outv", total_dur)

    return _bv2_encode(inputs, fg, output_path, total_dur, "APEX space_tap",
                       audio_pad="[_st_a_out]")


def make_signal_active_scene(audio_path: str, signal_content: dict,
                              output_path: str, btc_price: str = "N/A") -> str:
    """Render Signal Active segment with 60/40 split: X Spaces left, Nostr right.

    Left 60% (x=60-1140): X SPACES LIVE header in gold
    Right 40% (x=1160-1860): NOSTR SIGNAL header in green
    Cards stagger in at 0s/6s/12s per column.
    """
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 15
    total_dur = audio_dur + 0.3

    spaces = signal_content.get("spaces_quotes", [])[:3]
    x_posts = signal_content.get("x_posts", [])[:3]
    # FIX 4: Filter nostr spam BEFORE rendering — spam npubs/content must never appear in video
    nostr = [p for p in signal_content.get("nostr_posts", [])[:5]
             if not _is_nostr_spam_assembler(p)][:3]

    # Issue 13: If both sources empty, show clean placeholder instead of debug text
    if not spaces and not nostr:
        logger.info("Signal Active: no spaces/nostr data — showing SIGNAL COLLECTING placeholder")

    safe_btc = btc_price.replace("'", "").replace('"', "")

    inputs = [audio_path]

    # Procedural dark background
    _, bg_fg = _build_black_diamond_bg(total_dur, label_out="sig_bg")
    fg = bg_fg

    # ── R26 UPGRADE 2: HEADER BAR — left-aligned terminal header ──
    import datetime as _dt_sig
    _utc_ts = _dt_sig.datetime.utcnow().strftime("%H\\:%M UTC")
    fg += (f"[sig_bg]drawbox=x=0:y=0:w=1920:h=72:color=0x050505@0.97:t=fill,"
           f"drawbox=x=0:y=70:w=1920:h=2:color={COLOR_SIG_RED}@0.8:t=fill,"
           # Red dot
           f"drawbox=x=60:y=22:w=14:h=14:color={COLOR_SIG_RED}:t=fill,"
           # LIVE text
           f"drawtext=fontfile={FONT_MONO}:text='LIVE':"
           f"fontcolor={COLOR_SIG_RED}:fontsize=18:x=84:y=14,"
           # SIGNAL ACTIVE
           f"drawtext=fontfile={FONT_BOLD}:text='SIGNAL ACTIVE':"
           f"fontcolor={COLOR_WHITE}:fontsize=38:x=150:y=8,"
           # UTC timestamp top-right
           f"drawtext=fontfile={FONT_MONO}:text='{_utc_ts}':"
           f"fontcolor={COLOR_GOLD}:fontsize=16:x=w-tw-40:y=14"
           f"[sig_hdr];\n")

    # Determine left column content: X Spaces (live) > X Posts (cached) > placeholder
    _has_real_spaces = bool(spaces)
    _has_x_posts = bool(x_posts) and not _has_real_spaces
    _has_left_column = _has_real_spaces or _has_x_posts

    # Left column header adapts to data source
    if _has_real_spaces:
        _left_title = "X SPACES LIVE"
        _left_sub = "TRANSCRIBING..."
        _left_color = COLOR_GOLD
    elif _has_x_posts:
        _left_title = "X SIGNAL"
        _left_sub = "TOP POSTS"
        _left_color = COLOR_GOLD
    else:
        _left_title = "X SIGNAL"
        _left_sub = "MONITORING"
        _left_color = COLOR_GOLD

    # ── R26 UPGRADE 4: COLUMN HEADERS with sub-labels ──
    fg += (f"[sig_hdr]"
           f"drawtext=fontfile={FONT_BOLD}:text='{_left_title}':"
           f"fontcolor={_left_color}:fontsize=28:x=60:y=84,"
           f"drawtext=fontfile={FONT_MONO}:text='{_left_sub}':"
           f"fontcolor={_left_color}:fontsize=13:x=60:y=116,"
           f"drawtext=fontfile={FONT_BOLD}:text='NOSTR SIGNAL':"
           f"fontcolor={COLOR_NOSTR}:fontsize=28:x=1160:y=84,"
           # Sub-label: RELAY CONNECTED in green 13px
           f"drawtext=fontfile={FONT_MONO}:text='RELAY CONNECTED':"
           f"fontcolor={COLOR_NOSTR}:fontsize=13:x=1160:y=116"
           f"[sig_cols];\n")

    last_label = "sig_cols"

    _nostr_x = 1160 if _has_left_column else 60
    _nostr_w = 700 if _has_left_column else 1800

    if _has_real_spaces:
        # ── LEFT COLUMN: X SPACES (x=60..1140, width=1080) ──
        for idx, quote in enumerate(spaces):
            card_y = 150 + idx * 280
            card_h = 260
            card_w = 1080
            card_x = 60

            text_raw = quote.get("text", "")
            title = quote.get("space_title", "X Spaces")
            text_safe = _sanitize_text(text_raw)
            title_safe = _sanitize_text(title)
            wrapped = _word_wrap(text_safe, max_width=60, max_lines=4)

            enable_t = idx * 6  # stagger: 0s, 6s, 12s
            enable = f"enable='between(t,{enable_t},{total_dur:.1f})'"

            # R26: FETCHED source at card bottom
            space_source = _sanitize_text(quote.get("source", "X Spaces"))
            fetched_spaces = f"FETCHED {space_source}"

            out_label = f"sc{idx}"
            fg += (f"[{last_label}]"
                   # Card background
                   f"drawbox=x={card_x}:y={card_y}:w={card_w}:h={card_h}:"
                   f"color=0x0a0a0a@0.85:t=fill:{enable},"
                   # 1px gold border
                   f"drawbox=x={card_x}:y={card_y}:w={card_w}:h={card_h}:"
                   f"color={COLOR_GOLD}@0.6:t=1:{enable},"
                   # Space title
                   f"drawtext=fontfile={FONT_BOLD}:"
                   f"text='{title_safe}':"
                   f"fontcolor={COLOR_GOLD}:fontsize=20:x={card_x + 16}:y={card_y + 14}:{enable},"
                   # Quote text
                   f"drawtext=fontfile={FONT_MONO}:"
                   f"text='{wrapped}':"
                   f"fontcolor=0xe8e8e8:fontsize=26:x={card_x + 16}:y={card_y + 50}:"
                   f"line_spacing=8:{enable},"
                   # R26: FETCHED source at card bottom
                   f"drawtext=fontfile={FONT_MONO}:"
                   f"text='{fetched_spaces}':"
                   f"fontcolor={COLOR_MUTED2}:fontsize=10:x={card_x + 16}:y={card_y + card_h - 20}:{enable}"
                   f"[{out_label}];\n")
            last_label = out_label
    elif _has_x_posts:
        # X Posts from tracked accounts — show in left column with gold accent
        for idx, xpost in enumerate(x_posts):
            card_y = 150 + idx * 280
            card_h = 260
            card_w = 1080
            card_x = 60

            text_raw = xpost.get("text", "")
            handle = xpost.get("handle", "")
            text_safe = _sanitize_text(text_raw)
            handle_safe = _sanitize_text(f"@{handle}" if handle else "X")
            wrapped = _word_wrap(text_safe, max_width=60, max_lines=4)

            enable_t = idx * 6  # stagger: 0s, 6s, 12s
            enable = f"enable='between(t,{enable_t},{total_dur:.1f})'"

            out_label = f"xp{idx}"
            fg += (f"[{last_label}]"
                   # Card background
                   f"drawbox=x={card_x}:y={card_y}:w={card_w}:h={card_h}:"
                   f"color=0x0a0a0a@0.85:t=fill:{enable},"
                   # 1px gold border
                   f"drawbox=x={card_x}:y={card_y}:w={card_w}:h={card_h}:"
                   f"color={COLOR_GOLD}@0.6:t=1:{enable},"
                   # Handle
                   f"drawtext=fontfile={FONT_BOLD}:"
                   f"text='{handle_safe}':"
                   f"fontcolor={COLOR_GOLD}:fontsize=20:x={card_x + 16}:y={card_y + 14}:{enable},"
                   # Post text
                   f"drawtext=fontfile={FONT_MONO}:"
                   f"text='{wrapped}':"
                   f"fontcolor=0xe8e8e8:fontsize=26:x={card_x + 16}:y={card_y + 50}:"
                   f"line_spacing=8:{enable},"
                   # Source tag at card bottom
                   f"drawtext=fontfile={FONT_MONO}:"
                   f"text='VIA X':"
                   f"fontcolor={COLOR_MUTED2}:fontsize=10:x={card_x + 16}:y={card_y + card_h - 20}:{enable}"
                   f"[{out_label}];\n")
            last_label = out_label
        logger.info(f"  X POSTS: {len(x_posts)} posts rendered in left column")
    else:
        # No X data at all — subtle monitoring placeholder
        fg += (f"[{last_label}]"
               f"drawbox=x=60:y=150:w=1080:h=260:color=0x0a0a0a@0.6:t=fill,"
               f"drawbox=x=60:y=150:w=3:h=260:color={COLOR_GOLD}@0.4:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='MONITORING':"
               f"fontcolor={COLOR_GOLD}@0.5:fontsize=13:x=80:y=170,"
               f"drawtext=fontfile={FONT_BOLD}:text='AWAITING LIVE SIGNAL':"
               f"fontcolor={COLOR_WHITE}@0.6:fontsize=22:x=80:y=200,"
               f"drawtext=fontfile={FONT_MONO}:"
               f"text='X Spaces capture active  //  next signal when live Bitcoin spaces detected':"
               f"fontcolor={COLOR_MUTED}:fontsize=13:x=80:y=240"
               f"[sc_placeholder];\n")
        last_label = "sc_placeholder"
        logger.info("  FIX 7: No X data — showing placeholder")

    # ── R26 UPGRADE 4: RIGHT COLUMN: NOSTR (dynamic width based on spaces availability) ──
    for idx, post in enumerate(nostr):
        card_y = 150 + idx * 280
        card_h = 260
        card_w = _nostr_w
        card_x = _nostr_x

        text_raw = post.get("text", "")
        # R26: Primary identity = nip05 if available, else truncated pubkey
        nip05 = post.get("nip05", "")
        display_name = nip05 if nip05 else (post.get("display_name") or post.get("pubkey", "")[:16])
        # FIX 5: Truncate to 220 chars before wrapping to prevent card overflow
        text_safe = _sanitize_text(text_raw[:220])
        name_safe = _sanitize_text(display_name)
        # FIX 5: Use 55 chars/line for smaller font, get list of lines for separate drawtext
        _nostr_lines = []
        _nc_current = ""
        for _nc_word in text_safe.split():
            if len(_nc_current) + len(_nc_word) + 1 <= 55:
                _nc_current = (_nc_current + " " + _nc_word).strip()
            else:
                if _nc_current:
                    _nostr_lines.append(_nc_current)
                _nc_current = _nc_word
        if _nc_current:
            _nostr_lines.append(_nc_current)
        _nostr_lines = _nostr_lines[:4]  # max 4 lines

        enable_t = idx * 6
        enable = f"enable='between(t,{enable_t},{total_dur:.1f})'"

        # R26: ZAP+amount+sats in gold if zap_amount present
        zap_indicator = ""
        zap_amount = post.get("zap_amount", 0)
        if zap_amount:
            zap_indicator = (
                f"drawtext=fontfile={FONT_BOLD}:text='ZAP {zap_amount} sats':"
                f"fontcolor={COLOR_GOLD}:fontsize=14:x={card_x + card_w - 160}:y={card_y + 14}:{enable},"
            )
        elif post.get("has_zap"):
            zap_indicator = (
                f"drawtext=fontfile={FONT_BOLD}:text='ZAP':"
                f"fontcolor={COLOR_GOLD}:fontsize=14:x={card_x + card_w - 60}:y={card_y + 14}:{enable},"
            )

        # R26: FETCHED source at card bottom
        fetch_source = _sanitize_text(post.get("source", "relay"))
        fetched_text = f"FETCHED {fetch_source}"

        out_label = f"nc{idx}"
        fg += (f"[{last_label}]"
               # Card background
               f"drawbox=x={card_x}:y={card_y}:w={card_w}:h={card_h}:"
               f"color=0x0a0a0a@0.85:t=fill:{enable},"
               # 1px green border
               f"drawbox=x={card_x}:y={card_y}:w={card_w}:h={card_h}:"
               f"color={COLOR_NOSTR}@0.6:t=1:{enable},"
               # Display name (nip05 or pubkey)
               f"drawtext=fontfile={FONT_MONO}:"
               f"text='{name_safe}':"
               f"fontcolor={COLOR_NOSTR}:fontsize=18:x={card_x + 16}:y={card_y + 14}:{enable},"
               # Zap indicator
               f"{zap_indicator}"
               # FIX 5: Word-wrapped post text — separate drawtext per line at fontsize=16
               + "".join(
                   f"drawtext=fontfile={FONT_MONO}:"
                   f"text='{_sanitize_text(line)}':"
                   f"fontcolor=0xe8e8e8:fontsize=16:x={card_x + 16}:y={card_y + 40 + li * 20}:"
                   f"{enable},"
                   for li, line in enumerate(_nostr_lines)
               ) +
               # R26: FETCHED source at card bottom
               f"drawtext=fontfile={FONT_MONO}:"
               f"text='{fetched_text}':"
               f"fontcolor={COLOR_MUTED2}:fontsize=10:x={card_x + 16}:y={card_y + card_h - 20}:{enable}"
               f"[{out_label}];\n")
        last_label = out_label

    # Session fix 7a: Daily sponsor rotation (Curated Mining / Meanwhile / River)
    import datetime as _dt_sponsor
    _SPONSORS = [
        {"name": "CURATED MINING", "url": "CURATEDMINING.COM", "tagline": "White-glove Bitcoin mining"},
        {"name": "MEANWHILE", "url": "MEANWHILE.COM  //  CODE KKM73K", "tagline": "Bitcoin life insurance"},
        {"name": "RIVER", "url": "RIVER.COM", "tagline": "Buy Bitcoin with no minimums"},
    ]
    _sponsor = _SPONSORS[_dt_sponsor.date.today().timetuple().tm_yday % len(_SPONSORS)]
    _sp_text = f"SPONSORED BY\\:  {_sponsor['name']}  //  {_sponsor['url']}"
    fg += (f"[{last_label}]drawbox=x=60:y=990:w=1800:h=50:color=0x050505@0.90:t=fill,"
           f"drawbox=x=60:y=990:w=1800:h=2:color={COLOR_SIG_RED}@0.6:t=fill,"
           f"drawbox=x=60:y=990:w=4:h=50:color={COLOR_SIG_RED}@0.8:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='{_sp_text}':"
           f"fontcolor={COLOR_WHITE}:fontsize=14:x=960-(text_w/2):y=1008"
           f"[sig_sponsored];\n")

    # ── R26 UPGRADE 3: WAVEFORM BOTTOM BAND at y=880 ──
    fg += (f"[0:a]showwavespic=s=1800x120:colors=ff3b5f[_sig_wave_pic];\n"
           f"[_sig_wave_pic]format=rgba,colorchannelmixer=aa=0.4[_sig_wave_alpha];\n"
           f"[sig_sponsored][_sig_wave_alpha]overlay=60:880[sig_waved];\n")

    # ── CORNER BRACKETS ──
    fg += _build_corner_brackets_fg("sig_waved", "sig_cornered")

    # ── TICKER BAR ──
    fg += _build_info_bar_fg(total_dur, btc_price, label_in="sig_cornered", label_out="sig_final")

    # ── R26 UPGRADE 1: CRT SCANLINE ──
    fg = apply_scanline(inputs, fg, "sig_final", "sig_scanned", total_dur)

    fg += _ken_burns_motion("sig_scanned", "outv", total_dur)

    # Audio
    fg += (f"[0:a]aformat=channel_layouts=stereo:sample_rates=48000:sample_fmts=fltp,"
           f"alimiter=limit=0.85:level=disabled:attack=5:release=50[outa]")

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "fast",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, "signal_active_60_40", 600,
    )

    if ok:
        logger.info("R25 FIX 4: Signal Active 60/40 rendered (no EPISODE SEGMENTS, sponsor strip added): %s", output_path)
        return output_path

    logger.error("Signal Active 60/40 render failed — falling back to host visual")
    return ""


def make_social_card_visual(audio_path: str, posts: list, output_path: str,
    return None  # DISABLED: social card crashes assembly
                            btc_price: str = "N/A") -> str:
    """Render tweet card visual with real tweet data behind narration audio.

    Shows up to 2 tweet cards stacked vertically, each with:
    - Real @handle in red
    - Real tweet text in white, word-wrapped
    - Engagement stats (likes, retweets)
    - Red left border accent

    Args:
        audio_path: TTS narration audio for this social segment
        posts: List of dicts with handle, text, likes, retweets
        output_path: Output video path
        btc_price: BTC price for ticker

    Returns:
        Path to output video, or "" on failure
    """
    return None  # DISABLED: social cards crash assembly
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    # ISSUE 7 FIX: Ensure card video duration >= TTS audio + 0.5s buffer
    # Previous 0.3s buffer caused narration audio to get cut off by the next card
    total_dur = audio_dur + 0.5

    safe_btc = btc_price.replace("'", "").replace('"', "")
    has_wm = os.path.exists(WATERMARK)

    # Build inputs — APEX V2: no per-segment music
    inputs = [audio_path]
    inp_idx = 1
    if has_wm:
        inputs.append(WATERMARK)
        wm_idx = inp_idx
        inp_idx += 1
    else:
        wm_idx = -1

    # VDS procedural background (7-layer, no video files)
    _, bg_fg = _build_black_diamond_bg(total_dur, label_out="bgvig")
    fg = bg_fg

    # BUG 5 FIX: Red vignette glow behind card area for depth
    fg += (f"[bgvig]drawbox=x=220:y=60:w=1480:h=560:color=0x880000@0.12:t=fill,"
           f"drawbox=x=240:y=80:w=1440:h=520:color=0x660000@0.08:t=fill,"
           # VDS-1: Top red accent bar
           f"drawbox=x=0:y=0:w=1920:h=4:color={COLOR_RED}:t=fill[bgbar];\n")

    # VDS: Pulse dot top-left
    fg += f"[bgbar]drawbox=x=20:y=16:w=10:h=10:color={COLOR_RED}:t=fill[bgdot];\n"

    # VDS: Section header — gold eyebrow kicker
    fg += (f"[bgdot]drawtext=fontfile={FONT_MONO}:"
           f"text='SOCIAL PULSE - WHAT BITCOIN IS SAYING':"
           f"fontcolor={COLOR_RED}:fontsize=14:x=(w-text_w)/2:y=20[bgtitle];\n")
    last_v = "bgtitle"

    # Render up to 2 tweet cards — stacked vertically with spacing
    card_y_start = 90
    card_height = 260
    card_spacing = 30
    card_width = 1360
    card_x = 280

    # Issue 6: Check for screenshot paths and add as inputs
    screenshot_indices = {}
    for ci, post in enumerate(posts[:2]):
        ss_path = post.get("screenshot_path", "")
        if ss_path and os.path.exists(ss_path):
            inputs.append(ss_path)
            screenshot_indices[ci] = inp_idx
            inp_idx += 1
            logger.info(f"  Using tweet screenshot for card {ci}: {os.path.basename(ss_path)}")

    for ci, post in enumerate(posts[:2]):
        handle = _sanitize_text(post.get("handle", "unknown"))
        if not handle.startswith("@"):
            handle = f"@{handle}"
        # V9 FIX 6: Adaptive font/wrap for tweet length — long tweets get smaller font + more lines
        _raw_tweet = _sanitize_text(post.get("text", ""))
        if len(_raw_tweet) > 200:
            tweet_text = _word_wrap(_raw_tweet, max_width=44, max_lines=6)
            _tweet_fontsize = 36
        elif len(_raw_tweet) > 120:
            tweet_text = _word_wrap(_raw_tweet, max_width=38, max_lines=6)
            _tweet_fontsize = 42
        else:
            tweet_text = _word_wrap(_raw_tweet, max_width=32, max_lines=6)
            _tweet_fontsize = 52
        likes = post.get("likes", 0)
        retweets = post.get("retweets", 0)
        # FIX 2: Detect zero metrics — suppress "0 likes 0 RTs" which looks broken
        _likes_int = likes if isinstance(likes, int) else 0
        _rts_int = retweets if isinstance(retweets, int) else 0
        _has_real_metrics = _likes_int > 0 or _rts_int > 0
        likes_str = f"{likes:,}" if isinstance(likes, int) else str(likes)
        rt_str = f"{retweets:,}" if isinstance(retweets, int) else str(retweets)

        cy = card_y_start + ci * (card_height + card_spacing)
        tag = f"c{ci}"

        # Card glow (subtle red behind card — outer glow)
        fg += f"color=c={COLOR_RED}@0.08:s={card_width + 24}x{card_height + 24}:d={total_dur}:r=30[{tag}glow];\n"
        fg += f"[{last_v}][{tag}glow]overlay={card_x - 12}:{cy - 12}[{tag}g];\n"

        # Card body
        fg += f"color=c={COLOR_PANEL}@0.92:s={card_width}x{card_height}:d={total_dur}:r=30[{tag}body];\n"
        # Outer red border (2px)
        fg += f"[{tag}body]drawbox=x=0:y=0:w={card_width}:h={card_height}:color={COLOR_RED}@0.4:t=2[{tag}brd];\n"
        # Inner glow border (dark red, 2px inside the outer border)
        fg += f"[{tag}brd]drawbox=x=4:y=4:w={card_width - 8}:h={card_height - 8}:color={COLOR_PANEL2}@0.3:t=2[{tag}inner];\n"
        # Left accent bar
        fg += f"[{tag}inner]drawbox=x=0:y=0:w=6:h={card_height}:color={COLOR_RED}:t=fill[{tag}lbar];\n"
        # Top edge accent
        fg += f"[{tag}lbar]drawbox=x=0:y=0:w={card_width}:h=2:color={COLOR_RED}:t=fill[{tag}top];\n"

        # Issue 6: If screenshot available, overlay it inside card; else render text
        if ci in screenshot_indices:
            ss_idx = screenshot_indices[ci]
            # Scale screenshot to fit inside card (with padding)
            fg += (f"[{ss_idx}:v]scale={card_width - 16}:{card_height - 16}:"
                   f"force_original_aspect_ratio=decrease,"
                   f"pad={card_width - 16}:{card_height - 16}:(ow-iw)/2:(oh-ih)/2:{COLOR_PANEL}[{tag}ss];\n")
            fg += f"[{tag}top][{tag}ss]overlay=8:8[{tag}src];\n"
        else:
            # Pulse dot
            fg += f"[{tag}top]drawbox=x=20:y=18:w=8:h=8:color={COLOR_RED}:t=fill[{tag}dot];\n"

            # Handle — monospace font
            fg += (f"[{tag}dot]drawtext=fontfile={FONT_MONO}:"
                   f"text='{handle}':"
                   f"fontcolor={COLOR_RED}:fontsize=14:x=38:y=16[{tag}hdl];\n")

            # Tweet text — bold for readability (V9 FIX 6: adaptive font size)
            fg += (f"[{tag}hdl]drawtext=fontfile={FONT_BOLD}:"
                   f"text='{tweet_text}':"
                   f"fontcolor={COLOR_TEXT}:fontsize={_tweet_fontsize}:x=24:y=52:line_spacing=12:"
                   f"box=0[{tag}txt];\n")

            # Engagement stats bottom — FIX 2: suppress zero metrics
            if _has_real_metrics:
                fg += (f"[{tag}txt]drawtext=fontfile={FONT_MONO}:"
                       f"text='{likes_str} likes  |  {rt_str} RTs':"
                       f"fontcolor={COLOR_RED}:fontsize=12:x=24:y=h-28[{tag}stats];\n")
            else:
                fg += (f"[{tag}txt]drawtext=fontfile={FONT_MONO}:"
                       f"text='via X':fontcolor={COLOR_MUTED}:fontsize=12:"
                       f"x=24:y=h-28[{tag}stats];\n")

            # Source label bottom-right
            fg += (f"[{tag}stats]drawtext=fontfile={FONT_MONO}:"
                   f"text='via X':fontcolor={COLOR_MUTED}:fontsize=12:"
                   f"x=w-80:y=h-30[{tag}src];\n")

        # Overlay card on base with fade-in
        # Session fix 9c: 0.5s delay before tweet cards appear
        fade_start = 0.1  # V36: reduced from 0.5s to avoid blackdetect triggers + ci * 0.4
        fg += f"[{tag}g][{tag}src]overlay={card_x}:{cy}:format=auto,fade=t=in:st={fade_start}:d=0.3[{tag}out];\n"
        last_v = f"{tag}out"

    # VDS: Subtle bottom label
    bottom_header_y = card_y_start + len(posts[:2]) * (card_height + card_spacing) + 10
    fg += (f"[{last_v}]drawtext=fontfile={FONT_MONO}:"
           f"text='SOCIAL PULSE - WHAT BITCOIN IS SAYING':"
           f"fontcolor={COLOR_RED}@0.3:fontsize=12:x=(w-text_w)/2:y={bottom_header_y}[vbhdr];\n")
    last_v = "vbhdr"

    # VDS animated scrolling info bar
    fg += _build_info_bar_fg(total_dur, btc_price, label_in=last_v, label_out="vtick")
    last_v = "vtick"

    # Watermark
    if has_wm:
        fg += f"[{wm_idx}:v]scale=150:-1[wm];\n"
        fg += f"[{last_v}][wm]overlay=W-170:16[vwm];\n"
        last_v = "vwm"

    fg += _ken_burns_motion(last_v, "outv", total_dur)

    # FIX 4: explicit stereo format before loudnorm/aresample to prevent channel layout error
    fg += f"[0:a]aformat=channel_layouts=stereo:sample_rates=48000:sample_fmts=fltp,alimiter=limit=0.85:level=disabled:attack=5:release=50[outa]"

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "17", "-preset", "fast",
         "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, "social tweet card", 180,
    )

    if ok:
        logger.info(f"  Tweet card visual: {len(posts[:2])} cards, {total_dur:.1f}s")
        return output_path
    return ""


def _mix_swoosh_into_segment(video_path: str, force: bool = False) -> str:
    """Mix card_swoosh.wav into the first 0.4s of a video segment.

    Uses global _whoosh_applied_parts set to prevent double/triple whoosh.
    Adds afade on swoosh input to prevent click artifact.
    """
    global _whoosh_applied_parts
    if not os.path.exists(CARD_SWOOSH) or not os.path.exists(video_path):
        return video_path
    abs_path = os.path.abspath(video_path)
    if abs_path in _whoosh_applied_parts and not force:
        logger.info(f"  WHOOSH DEDUP: Skipping swoosh — already applied to {os.path.basename(video_path)}")
        return video_path
    basename = os.path.basename(video_path).lower()
    if "xfade" in basename or "transition" in basename:
        logger.info(f"  WHOOSH SKIP: filename has xfade/transition: {basename}")
        return video_path
    tmp = video_path + ".swoosh.mp4"
    ok = run_ffmpeg([
        "-i", video_path,
        "-i", CARD_SWOOSH,
        "-filter_complex",
        "[1:a]afade=t=in:st=0:d=0.05[swoosh_faded];"
        "[0:a][swoosh_faded]amix=inputs=2:duration=first:weights=1 0.5[outa]",
        "-map", "0:v", "-map", "[outa]",
        "-c:v", "copy",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        tmp,
    ], "mix card swoosh", 30)
    if ok and os.path.exists(tmp):
        os.replace(tmp, video_path)
        _whoosh_applied_parts.add(abs_path)
        return video_path
    # On failure: return original video unchanged
    if os.path.exists(tmp):
        try:
            os.remove(tmp)
        except OSError:
            pass
    return video_path


def make_remotion_social_card(audio_path: str, posts: list, output_path: str,
                              btc_price: str = "N/A") -> str:
    """Render SocialCard via Remotion + mux with TTS audio.

    Falls back to '' on failure (caller should use FFmpeg make_social_card_visual).
    """
    if not _remotion_enabled():
        return ""

    post = posts[0] if posts else {}
    dur = ffprobe_duration(audio_path)
    total_dur = dur + 0.3
    # Issue 10: durationInFrames must NEVER be shorter than audio — add 1 second (30 frames) buffer
    frames = max(math.ceil(total_dur * 30) + 30, 90)

    raw_video = output_path + ".remotion_raw.mp4"
    result = _render_remotion("SocialCard", raw_video, props={
        "handle": post.get("handle", "ProtocolPulse"),
        "text": post.get("text", "")[:200],
        # FIX 2: Pass -1 for zero metrics so Remotion can suppress display
        "likes": post.get("likes", 0) or -1,
        "retweets": post.get("retweets", 0) or -1,
        "durationInFrames": frames,
    })
    if not result:
        return ""

    muxed = _remotion_with_audio(raw_video, audio_path, output_path, bg_music=True)
    if os.path.exists(raw_video):
        try:
            os.remove(raw_video)
        except OSError:
            pass
    if muxed:
        # Mix in card swoosh SFX on entrance
        muxed = _mix_swoosh_into_segment(muxed)
        logger.info(f"  Remotion SocialCard: {ffprobe_duration(muxed):.1f}s")
    return muxed


def make_remotion_title_card(audio_path: str, output_path: str,
                             title: str = "", date: str = "",
                             btc_price: str = "N/A") -> str:
    """Render TitleCard via Remotion + mux with TTS + jingle audio.

    Falls back to '' on failure (caller should use FFmpeg make_intro_coldopen).
    """
    # Session 4 Fix 1: Title card suppressed — kills momentum with 8s dead air
    logger.info("Title card suppressed — per PIPELINE_LAWS session 4")
    return ""
    if not _remotion_enabled():
        return ""
    if not date:
        from datetime import date as _d
        date = _d.today().isoformat()

    dur = ffprobe_duration(audio_path)
    total_dur = max(dur + 1.0, 4.0)
    frames = max(math.ceil(total_dur * 30), 120)

    raw_video = output_path + ".remotion_raw.mp4"
    result = _render_remotion("TitleCard", raw_video, props={
        "title": title or "Pulse Check Daily",
        "date": date,
        "durationInFrames": frames,
    })
    if not result:
        return ""

    # Mux with TTS + jingle (same audio chain as make_intro_coldopen)
    import glob as _glob
    jingle = os.path.join(ASSETS, "music", "pp_intro.mp3")
    if not os.path.exists(jingle):
        tracks = _glob.glob(os.path.join(ASSETS, "music", "intro_*.mp3"))
        jingle = tracks[0] if tracks else ""

    total_dur = max(dur + 1.0, 4.0)
    has_jingle = bool(jingle and os.path.exists(jingle))

    if has_jingle:
        ok = run_ffmpeg([
            "-i", raw_video,
            "-i", audio_path,
            "-i", jingle,
            "-filter_complex",
            f"[0:v]setpts=PTS-STARTPTS[v];"
            f"[1:a]volume=1.0[tts_a];"
            f"[2:a]volume=0.35[jingle_a];"
            f"[tts_a][jingle_a]amix=inputs=2:duration=first:weights=1 0.35[outa]",
            "-map", "[v]", "-map", "[outa]",
            "-c:v", "libx264", "-crf", "17", "-preset", "fast",
            "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(total_dur), output_path,
        ], "remotion title card + jingle", 120)
    else:
        muxed = _remotion_with_audio(raw_video, audio_path, output_path, bg_music=False)
        ok = bool(muxed)

    if os.path.exists(raw_video):
        try:
            os.remove(raw_video)
        except OSError:
            pass
    if ok and os.path.exists(output_path):
        logger.info(f"  Remotion TitleCard: {ffprobe_duration(output_path):.1f}s")
        return output_path
    return ""


def _make_remotion_intel_panel(duration_frames: int = 300,
                               btc_price: str = "N/A") -> str:
    """Session 4 Fix 6: Render IntelPanel overlay via Remotion.

    Reads narrative_context.json for live data. Returns path to rendered
    transparent overlay video, or '' on failure.
    """
    if not _remotion_enabled():
        return ""

    # Read narrative context
    import json as _json, datetime as _dt
    _intel_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "data", "intelligence")
    _nc_path = os.path.join(_intel_dir, "narrative_context.json")

    narrative = "Bitcoin Sound Money"
    market_mood = "NEUTRAL"
    quote_text = ""
    quote_handle = ""

    try:
        with open(_nc_path) as f:
            nc = _json.load(f)
        computed = nc.get("computed_at", "")
        if computed:
            age = (_dt.datetime.now(_dt.timezone.utc) -
                   _dt.datetime.fromisoformat(computed)).total_seconds() / 3600
            if age < 12:
                narrative = nc.get("dominant_narrative", narrative)[:42]
                market_mood = nc.get("market_mood", "neutral").upper().replace("_", " ")[:16]
                hint = nc.get("eryn_intro_hook", "")
                if "'" in hint:
                    qs = hint.find("'") + 1
                    qe = hint.find("'", qs)
                    if qe > qs:
                        quote_text = hint[qs:qe][:70]
                tl = nc.get("thought_leaders_mentioned", [])
                quote_handle = ("@" + tl[0][:18]) if tl else ""
    except Exception:
        pass

    import hashlib
    props_hash = hashlib.md5(f"{btc_price}{narrative}{market_mood}".encode()).hexdigest()[:8]
    out_path = os.path.join(tempfile.gettempdir(), f"intel_panel_{props_hash}.mp4")

    if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
        return out_path  # cached

    result = _render_remotion("IntelPanel", out_path, props={
        "btcPrice": btc_price,
        "narrative": narrative,
        "marketMood": market_mood,
        "quoteText": quote_text,
        "quoteHandle": quote_handle,
        "durationInFrames": duration_frames,
    }, timeout=600)

    if result:
        logger.info(f"  Remotion IntelPanel rendered: {narrative} / {market_mood}")
    return result or ""
