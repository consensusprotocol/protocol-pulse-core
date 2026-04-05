#!/usr/bin/env python3
"""Data dashboard scene rendering for Protocol Pulse episodes."""
import os

from assembler_common import (
    logger, run_ffmpeg, run_ffmpeg_filtergraph, ffprobe_duration,
    _PIPELINE_DIR, BASE, ASSETS, FONT_BOLD, FONT_MONO,
    COLOR_BG, COLOR_RED, COLOR_WHITE, COLOR_GOLD, COLOR_MUTED,
    COLOR_PANEL2, COLOR_GREEN, COLOR_CORAL,
    _sanitize_text, _split_headline_for_render, _get_live_metric,
    _get_bg_layer, _build_corner_brackets_fg, _build_narration_wave,
    _build_signature_info_rail, apply_scanline,
    _add_episode_title_pill, _ken_burns_motion, _bv2_encode,
)


def make_data_segment_scene(audio_path: str, headline: str, metrics: list,
                             output_path: str, btc_price: str = "N/A",
                             duration: float = 0, script_text: str = "",
                             chart_keyword: str = "",
                             episode_title: str = "PULSE CHECK") -> str:
    """APEX Data Segment — intelligence dashboard with chart overlays aligned to narration."""
    try:
        return _make_data_segment_inner(audio_path, headline, metrics,
                                        output_path, btc_price, duration,
                                        script_text, chart_keyword,
                                        episode_title=episode_title)
    except Exception as e:
        logger.error(f"Data segment failed entirely: {e} — writing 20s filler")
        _fdur = 20.0
        if audio_path and os.path.exists(audio_path):
            _fdur = max(ffprobe_duration(audio_path), 20.0)
        _fargs = ["-f", "lavfi", "-i", f"color=c=0x0A0A0F:s=1920x1080:d={_fdur}:r=30"]
        if audio_path and os.path.exists(audio_path):
            _fargs.extend(["-i", audio_path])
        else:
            _fargs.extend(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"])
        _fargs.extend([
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
            "-t", str(_fdur), output_path
        ])
        run_ffmpeg(_fargs, "data segment filler", 30)
        return output_path if os.path.exists(output_path) else ""


def _make_data_segment_inner(audio_path: str, headline: str, metrics: list,
                              output_path: str, btc_price: str = "N/A",
                              duration: float = 0, script_text: str = "",
                              chart_keyword: str = "",
                              episode_title: str = "PULSE CHECK") -> str:
    """Inner implementation of data segment — raises on failure for outer try/except."""
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = duration if duration > 0 else audio_dur + 0.3

    # Fetch intelligence data and render chart PNGs
    _intel_data = {}
    try:
        from fetch_intelligence_data import load_or_refresh as _intel_load
        _intel_data = _intel_load()
        from render_chart_assets import render_all as _render_charts
        _render_charts(_intel_data)
    except Exception as _intel_err:
        logger.warning("Intelligence data/chart render failed: %s", _intel_err)

    _chart_dir = os.path.join(_PIPELINE_DIR, "cache", "charts")
    _chart_map = {
        "price": os.path.join(_chart_dir, "price_chart.png"),
        "hashrate": os.path.join(_chart_dir, "hashrate_chart.png"),
        "difficulty": os.path.join(_chart_dir, "hashrate_chart.png"),  # reuse hashrate chart
        "dominance": os.path.join(_chart_dir, "dominance_chart.png"),
        "mempool": os.path.join(_chart_dir, "price_chart.png"),  # V9 FIX 3: was dominance, no mempool chart
        "etf": os.path.join(_chart_dir, "price_chart.png"),  # ETF overlaid on price
        "lth": os.path.join(_chart_dir, "dominance_chart.png"),  # LTH supply via dominance
    }

    # Session fix 6a: Strict segment→chart keyword routing
    # Priority order: specific topics first, then general BTC price as default
    if not chart_keyword and script_text:
        _st = script_text.lower()
        if any(kw in _st for kw in ("hashrate", "hash rate", "eh/s", "mining", "miner")):
            chart_keyword = "hashrate"
        elif any(kw in _st for kw in ("dominance", "btc dominance", "market share", "alt season")):
            chart_keyword = "dominance"
        elif any(kw in _st for kw in ("difficulty", "difficulty adjustment", "retarget")):
            chart_keyword = "difficulty"
        elif any(kw in _st for kw in ("long-term holder", "long term holder", "lth", "lth supply")):
            chart_keyword = "lth"
        elif any(kw in _st for kw in ("etf", "etf flow", "etf inflow", "etf outflow", "spot etf")):
            chart_keyword = "etf"
        elif any(kw in _st for kw in ("mempool", "sat/vb", "fees", "congestion", "transaction")):
            chart_keyword = "mempool"
        elif any(kw in _st for kw in ("price", "$", "rally", "dump", "correction", "btc at", "bitcoin at")):
            chart_keyword = "price"
        else:
            chart_keyword = "price"  # default to BTC price chart

    _fg_value = _intel_data.get("fear_greed_value", 0)
    _fg_label = _intel_data.get("fear_greed_label", "N/A")

    inputs = [audio_path]
    # Session fix 4b: Solid dark background for intelligence segment (no bg_loop)
    fg = (f"color=c=0x0d0d0d:s=1920x1080:d={total_dur + 2.0}:r=30,"
          f"drawbox=x=0:y=0:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
          f"drawbox=x=0:y=1078:w=1920:h=2:color={COLOR_RED}@0.75:t=fill,"
          f"drawbox=x=0:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill,"
          f"drawbox=x=1918:y=0:w=2:h=1080:color={COLOR_RED}@0.75:t=fill[bb_bg];\n")

    # Top eyebrow
    import datetime
    date_str = datetime.date.today().strftime("%B %d, %Y").upper()
    fg += (f"[bb_bg]drawtext=fontfile={FONT_MONO}:text='TODAYS INTELLIGENCE':"
           f"fontcolor={COLOR_GOLD}:fontsize=11:x=40:y=40,"
           f"drawtext=fontfile={FONT_MONO}:text='{date_str}':"
           f"fontcolor={COLOR_GOLD}:fontsize=11:x=w-tw-40:y=40"
           f"[ds_eyebrow];\n")

    # Headline (2-line support)
    safe_head = _sanitize_text(headline)
    _ds_l1, _ds_l2 = _split_headline_for_render(safe_head)
    _ds_fs = 34 if _ds_l2 else 42
    fg += (f"[ds_eyebrow]drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_ds_l1)}':"
           f"fontcolor={COLOR_WHITE}:fontsize={_ds_fs}:x=40:y=72")
    if _ds_l2:
        fg += (f",drawtext=fontfile={FONT_BOLD}:text='{_sanitize_text(_ds_l2)}':"
               f"fontcolor={COLOR_WHITE}:fontsize={_ds_fs}:x=40:y={72 + 65}")
    fg += f"[ds_headline];\n"

    # 6 metric cards
    default_metrics = [
        ("FEAR GREED", str(_fg_value), _sanitize_text(_fg_label), _fg_value > 50),
        ("HASHRATE", _get_live_metric("hashrate", "850 EH/s"), "+4.2 pct", True),
        ("ETF FLOW", _get_live_metric("etf_flow", "$340M"), "+18 pct", True),
        ("MEMPOOL FEE", _get_live_metric("mempool_fee", "12 sat/vB"), "-8 pct", False),
        ("HALVING PCT", "78 pct", "+0.3 pct", True),
        ("DOMINANCE", _get_live_metric("dominance", "63.5 pct"), "+1.1 pct", True),
    ]
    use_metrics = []
    if metrics:
        for m in metrics[:6]:
            if isinstance(m, dict):
                use_metrics.append((
                    m.get("label", "DATA"),
                    _sanitize_text(str(m.get("value", "N/A"))),
                    _sanitize_text(str(m.get("delta", ""))),
                    m.get("positive", True),
                ))
            elif isinstance(m, (list, tuple)) and len(m) >= 3:
                use_metrics.append((str(m[0]), _sanitize_text(str(m[1])),
                                    _sanitize_text(str(m[2])),
                                    m[3] if len(m) > 3 else True))
    while len(use_metrics) < 6:
        use_metrics.append(default_metrics[len(use_metrics)])

    # Session fix 4c: 2 rows of 3 metric cards, 40% larger
    card_w, card_h, gap = 392, 112, 16  # 40% larger than 280x80
    grid_x, grid_y = 40, 140
    last = "ds_headline"
    for mi, (mlabel, mval, mdelta, mpos) in enumerate(use_metrics):
        col = mi % 3
        row = mi // 3
        mx = grid_x + col * (card_w + gap)
        my = grid_y + row * (card_h + gap)
        dc = COLOR_GREEN if mpos else COLOR_CORAL
        out = f"ds_m{mi}"
        fg += (f"[{last}]"
               f"drawbox=x={mx}:y={my}:w={card_w}:h={card_h}:color={COLOR_PANEL2}@0.95:t=fill,"
               f"drawbox=x={mx}:y={my}:w={card_w}:h=4:color={COLOR_RED}@0.6:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='{mlabel}':"
               f"fontcolor={COLOR_GOLD}:fontsize=14:x={mx+14}:y={my+14},"
               f"drawtext=fontfile={FONT_BOLD}:text='{mval}':"
               f"fontcolor={COLOR_WHITE}:fontsize=30:x={mx+14}:y={my+38},"
               f"drawtext=fontfile={FONT_MONO}:text='{mdelta}':"
               f"fontcolor={dc}:fontsize=15:x={mx+14}:y={my+80}"
               f"[{out}];\n")
        last = out

    # HERO CHART — narration-aligned chart display
    chart_panel_x, chart_panel_y = 200, 250
    chart_panel_w, chart_panel_h = 1520, 460

    # Load available charts — PNG inputs with -loop 1
    _available_charts = {}
    if chart_keyword and chart_keyword in _chart_map:
        # Single chart mode — only load the matched chart
        cp = _chart_map[chart_keyword]
        if os.path.exists(cp) and os.path.getsize(cp) > 1000:
            inputs.append(["-loop", "1", "-framerate", "30", "-i", cp])
            _available_charts[chart_keyword] = len(inputs) - 1
            logger.info(f"  Chart: single {chart_keyword} (keyword match)")
    else:
        # Grid mode — load all available charts
        for key, cp in _chart_map.items():
            if os.path.exists(cp) and os.path.getsize(cp) > 1000:
                inputs.append(["-loop", "1", "-framerate", "30", "-i", cp])
                _available_charts[key] = len(inputs) - 1

    if len(_available_charts) == 1:
        # Single chart full-panel — Ken Burns motion on static PNG
        _key, _idx = list(_available_charts.items())[0]
        _cw_up, _ch_up = int(chart_panel_w * 1.02), int(chart_panel_h * 1.02)
        _cw_pan, _ch_pan = _cw_up - chart_panel_w, _ch_up - chart_panel_h
        fg += (f"[{_idx}:v]scale={_cw_up}:{_ch_up},"
               f"crop={chart_panel_w}:{chart_panel_h}:"
               f"'{_cw_pan}*t/{total_dur:.2f}':'{_ch_pan}*t/{total_dur:.2f}',"
               f"setsar=1,format=yuv420p[ds_chts_single];\n")
        fg += (f"[{last}][ds_chts_single]overlay=x={chart_panel_x}:y={chart_panel_y}"
               f"[ds_chart_done];\n")
        logger.info(f"  Chart: showing {_key} full-panel (Ken Burns)")
    elif len(_available_charts) >= 2:
        # Horizontal grid — Ken Burns motion on each static PNG
        n_charts = len(_available_charts)
        _grid_w = chart_panel_w // n_charts - 8
        chart_items = list(_available_charts.items())
        _gw_up, _gh_up = int(_grid_w * 1.02), int(chart_panel_h * 1.02)
        _gw_pan, _gh_pan = _gw_up - _grid_w, _gh_up - chart_panel_h
        for ci, (key, idx) in enumerate(chart_items):
            fg += (f"[{idx}:v]scale={_gw_up}:{_gh_up},"
                   f"crop={_grid_w}:{chart_panel_h}:"
                   f"'{_gw_pan}*t/{total_dur:.2f}':'{_gh_pan}*t/{total_dur:.2f}',"
                   f"setsar=1,format=yuv420p[ds_chtg{ci}];\n")
        _gx = chart_panel_x
        _chart_last = last
        for ci in range(len(chart_items)):
            _out = f"ds_chto{ci}" if ci < len(chart_items) - 1 else "ds_chart_done"
            fg += (f"[{_chart_last}][ds_chtg{ci}]overlay=x={_gx}:y={chart_panel_y}"
                   f"[{_out}];\n")
            _chart_last = _out
            _gx += _grid_w + 12
        logger.info(f"  Charts: {n_charts} in grid")
    else:
        # No charts available — solid dark fallback
        fg += (f"[{last}]"
               f"drawbox=x={chart_panel_x}:y={chart_panel_y}:w={chart_panel_w}:h={chart_panel_h}:"
               f"color={COLOR_PANEL2}@0.85:t=fill,"
               f"drawtext=fontfile={FONT_MONO}:text='CHARTS LOADING...':"
               f"fontcolor={COLOR_MUTED}:fontsize=24:x={chart_panel_x+chart_panel_w//2-120}:"
               f"y={chart_panel_y+chart_panel_h//2-12}"
               f"[ds_chart_done];\n")
        logger.info("  Charts: none available — dark fallback")

# Session fix 7a: Daily sponsor rotation for data segment
    import datetime as _dt_sp_ds
    _DS_SPONSORS = [
        {"name": "Meanwhile", "tagline": "Bitcoin Life Insurance",
         "cta": "Get covered in Bitcoin  protocolpulse.io/meanwhile", "color": COLOR_GOLD},
        {"name": "Curated Mining", "tagline": "White-Glove Bitcoin Mining",
         "cta": "Start mining  curatedmining.com", "color": COLOR_RED},
        {"name": "River", "tagline": "Buy Bitcoin. Earn Bitcoin.",
         "cta": "Start stacking  river.com", "color": COLOR_GOLD},
    ]
    _ds_sp = _DS_SPONSORS[_dt_sp_ds.date.today().timetuple().tm_yday % len(_DS_SPONSORS)]
    strip_x, strip_y, strip_w, strip_h = 40, 730, 1840, 120

    last_sp = "ds_chart_done"
    sp_name = _sanitize_text(_ds_sp["name"])
    sp_tagline = _sanitize_text(_ds_sp["tagline"])
    sp_cta = _sanitize_text(_ds_sp["cta"])
    sp_color = _ds_sp["color"]
    fg += (f"[{last_sp}]"
           f"drawbox=x={strip_x}:y={strip_y}:w={strip_w}:h={strip_h}:"
           f"color={COLOR_PANEL2}@0.95:t=fill,"
           f"drawbox=x={strip_x}:y={strip_y}:w=6:h={strip_h}:"
           f"color={sp_color}@1.0:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='SPONSORED BY':"
           f"fontcolor={COLOR_GOLD}:fontsize=10:x={strip_x+20}:y={strip_y+18},"
           f"drawtext=fontfile={FONT_BOLD}:text='{sp_name}':"
           f"fontcolor={COLOR_WHITE}:fontsize=34:x={strip_x+20}:y={strip_y+38},"
           f"drawtext=fontfile={FONT_MONO}:text='{sp_tagline}':"
           f"fontcolor={COLOR_MUTED}:fontsize=15:x={strip_x+20}:y={strip_y+80},"
           f"drawtext=fontfile={FONT_MONO}:text='{sp_cta}':"
           f"fontcolor={sp_color}:fontsize=14:"
           f"x={strip_x+strip_w}-tw-20:y={strip_y+80},"
           f"drawbox=x={strip_x+strip_w-100}:y={strip_y+8}:w=90:h=22:"
           f"color={sp_color}@0.15:t=fill,"
           f"drawtext=fontfile={FONT_MONO}:text='PARTNER':"
           f"fontcolor={sp_color}:fontsize=10:"
           f"x={strip_x+strip_w-90}:y={strip_y+13}"
           f"[ds_sp0];\n")
    last_sp = "ds_sp0"

    fg += _build_corner_brackets_fg(last_sp, "ds_corners")
    wave_fg, ds_audio_pad = _build_narration_wave("ds_corners", "ds_wave", "ds_a_out")
    fg += wave_fg
    fg += _build_signature_info_rail(total_dur, btc_price, "ds_wave", "ds_railed")
    fg = apply_scanline(inputs, fg, "ds_railed", "ds_scanned", total_dur)
    # FIX 3: Episode title pill
    fg += _add_episode_title_pill("ds_scanned", "_ds_pilled", episode_title, total_dur)
    fg += _ken_burns_motion("_ds_pilled", "outv", total_dur)

    result = _bv2_encode(inputs, fg, output_path, total_dur, "APEX data segment",
                         audio_pad=ds_audio_pad)
    if result:
        return result

    # Fallback: 20s dark filler so episode never drops below 360s
    logger.error("Data segment encode failed — writing 20s dark filler")
    _fdur = max(ffprobe_duration(audio_path) if audio_path and os.path.exists(audio_path) else 20.0, 20.0)
    _fargs = ["-f", "lavfi", "-i", f"color=c=0x0A0A0F:s=1920x1080:d={_fdur}:r=30"]
    if audio_path and os.path.exists(audio_path):
        _fargs.extend(["-i", audio_path])
    else:
        _fargs.extend(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"])
    _fargs.extend([
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        "-t", str(_fdur), output_path
    ])
    run_ffmpeg(_fargs, "data segment filler", 30)
    return output_path if os.path.exists(output_path) else ""
