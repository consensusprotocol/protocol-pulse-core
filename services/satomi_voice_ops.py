"""
Satomi Voice Ops — Voice command brain for Protocol Pulse team.

Talk to it. It does things.

Pattern: text command -> Claude/Gemini function-calling -> internal tool execution -> spoken reply.

Acts under the identity of the logged-in admin user (passed in by the route handler).
Browser-side Web Speech API handles STT; this module is text-in only.
TTS (ElevenLabs) handled by the blueprint, not here.

Tools registered v1:
  - board_create_card
  - board_move_card
  - board_update_card
  - board_add_comment
  - board_list_cards
  - board_assign_to_me
  - latest_grade
  - system_status

Designed for extension. Add a new tool: register schema in TOOL_SCHEMAS, implement
in TOOL_IMPLEMENTATIONS. Both Claude and Gemini paths pick it up automatically.
"""

import os
import logging
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# --- Lazy SDK imports (avoid blowing up app boot if a key is missing) -------

def _claude_client():
    try:
        import anthropic
        key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
        if not key:
            return None
        return anthropic.Anthropic(api_key=key)
    except Exception as e:
        logger.warning('Claude client unavailable: %s', e)
        return None


def _gemini_client():
    try:
        import google.generativeai as genai
        key = os.environ.get('GEMINI_API_KEY', '').strip() or os.environ.get('GOOGLE_API_KEY', '').strip()
        if not key:
            return None
        genai.configure(api_key=key)
        return genai
    except Exception as e:
        logger.warning('Gemini client unavailable: %s', e)
        return None


# --- Tool schemas (Anthropic format) ----------------------------------------

TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "board_create_card",
        "description": "Create a new card on the team kanban board. Use this when the user asks to add, create, make, or note down a task, bug, idea, or feature.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title of the card"},
                "description": {"type": "string", "description": "Optional longer description"},
                "column": {"type": "string", "enum": ["backlog", "in_progress", "review", "done"], "description": "Column to place the card in. Default backlog."},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "description": "Priority level"},
                "tag": {"type": "string", "enum": ["feature", "bug", "content", "marketing", "ops"], "description": "Card tag/category"},
                "assignee_email": {"type": "string", "description": "Email of admin user to assign. Use 'me' or null to assign to the current user."},
                "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format. Optional."},
            },
            "required": ["title"],
        },
    },
    {
        "name": "board_move_card",
        "description": "Move a card to a different column. Match the card by title (fuzzy) or numeric ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "card_identifier": {"type": "string", "description": "Card title (fuzzy match) or numeric ID"},
                "target_column": {"type": "string", "enum": ["backlog", "in_progress", "review", "done"]},
            },
            "required": ["card_identifier", "target_column"],
        },
    },
    {
        "name": "board_update_card",
        "description": "Update a single field on an existing card (priority, tag, title, description, due_date, assignee_email).",
        "input_schema": {
            "type": "object",
            "properties": {
                "card_identifier": {"type": "string", "description": "Card title (fuzzy) or numeric ID"},
                "field": {"type": "string", "enum": ["title", "description", "priority", "tag", "due_date", "assignee_email"]},
                "value": {"type": "string", "description": "New value for the field"},
            },
            "required": ["card_identifier", "field", "value"],
        },
    },
    {
        "name": "board_add_comment",
        "description": "Add a comment to a card on the board.",
        "input_schema": {
            "type": "object",
            "properties": {
                "card_identifier": {"type": "string", "description": "Card title (fuzzy) or numeric ID"},
                "body": {"type": "string", "description": "Comment text"},
            },
            "required": ["card_identifier", "body"],
        },
    },
    {
        "name": "board_list_cards",
        "description": "List cards on the board, optionally filtered by column, assignee email, or tag. Use this when user asks 'what's on the board', 'what am I working on', or 'show me bugs'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "column": {"type": "string", "enum": ["backlog", "in_progress", "review", "done", "all"]},
                "assignee_email": {"type": "string", "description": "Filter to a specific assignee. Use 'me' for current user."},
                "tag": {"type": "string", "enum": ["feature", "bug", "content", "marketing", "ops", "all"]},
            },
        },
    },
    {
        "name": "board_assign_to_me",
        "description": "Assign a card to the current logged-in user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "card_identifier": {"type": "string", "description": "Card title (fuzzy) or numeric ID"},
            },
            "required": ["card_identifier"],
        },
    },
    {
        "name": "latest_grade",
        "description": "Return the most recent Gemini grade for the Pulse Check video pipeline. Use this when the user asks about the latest render, video grade, or pipeline output.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "system_status",
        "description": "Return Protocol Pulse system status: site uptime, recent errors, avatar server health, render activity.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


# --- Tool implementations ---------------------------------------------------
#
# Each tool returns a dict: {"ok": bool, "summary": str (spoken back), "data": optional}
# Tools have access to the Flask app context via the caller — they import models/db lazily.

def _fuzzy_find_card(identifier: str):
    """Find a card by numeric ID or fuzzy title match. Returns BoardCard or None."""
    from core import models  # late import — only valid inside Flask app context
    identifier = (identifier or '').strip()
    if not identifier:
        return None
    # Numeric ID first
    if identifier.isdigit():
        return models.BoardCard.query.get(int(identifier))
    # Exact title match
    card = models.BoardCard.query.filter(
        models.BoardCard.column != 'archived',
        models.BoardCard.title.ilike(identifier),
    ).first()
    if card:
        return card
    # Fuzzy: title contains the identifier OR identifier contains the title
    cards = models.BoardCard.query.filter(models.BoardCard.column != 'archived').all()
    ident_low = identifier.lower()
    # Best match by overlap length
    best = None
    best_score = 0
    for c in cards:
        title_low = (c.title or '').lower()
        if ident_low in title_low or title_low in ident_low:
            score = min(len(ident_low), len(title_low))
            if score > best_score:
                best, best_score = c, score
    return best


def _resolve_assignee(email_or_me: Optional[str], current_user) -> Optional[int]:
    from core import models
    if not email_or_me:
        return None
    val = email_or_me.strip().lower()
    if val in ('me', 'myself', 'self', current_user.email.lower() if current_user else ''):
        return current_user.id if current_user else None
    user = models.User.query.filter(models.User.email.ilike(val)).first()
    return user.id if user else None


def tool_board_create_card(params: Dict[str, Any], current_user) -> Dict[str, Any]:
    from core import models, db
    title = (params.get('title') or '').strip()[:200]
    if not title:
        return {"ok": False, "summary": "I need a title for the card. What should I call it?"}
    column = params.get('column') or 'backlog'
    priority = params.get('priority') or 'medium'
    tag = params.get('tag') or 'feature'
    description = params.get('description') or ''
    assignee_id = _resolve_assignee(params.get('assignee_email'), current_user)
    due = None
    if params.get('due_date'):
        try:
            due = datetime.strptime(params['due_date'], '%Y-%m-%d')
        except Exception:
            pass

    max_pos = db.session.query(db.func.max(models.BoardCard.position)).filter_by(column=column).scalar() or 0
    card = models.BoardCard(
        title=title,
        description=description,
        column=column,
        priority=priority,
        tag=tag,
        assignee_id=assignee_id,
        creator_id=current_user.id,
        position=max_pos + 1,
        due_date=due,
    )
    db.session.add(card)
    db.session.commit()
    where = column.replace('_', ' ')
    pri = f", priority {priority}" if priority != 'medium' else ""
    return {"ok": True, "summary": f"Card created in {where}: {title}{pri}.", "data": {"id": card.id}}


def tool_board_move_card(params: Dict[str, Any], current_user) -> Dict[str, Any]:
    from core import models, db
    card = _fuzzy_find_card(params.get('card_identifier', ''))
    if not card:
        return {"ok": False, "summary": f"I couldn't find a card matching '{params.get('card_identifier')}'."}
    target = params.get('target_column')
    if target not in ('backlog', 'in_progress', 'review', 'done'):
        return {"ok": False, "summary": "Target column must be backlog, in progress, review, or done."}
    card.column = target
    card.updated_at = datetime.utcnow()
    db.session.commit()
    return {"ok": True, "summary": f"Moved '{card.title}' to {target.replace('_',' ')}."}


def tool_board_update_card(params: Dict[str, Any], current_user) -> Dict[str, Any]:
    from core import models, db
    card = _fuzzy_find_card(params.get('card_identifier', ''))
    if not card:
        return {"ok": False, "summary": f"I couldn't find a card matching '{params.get('card_identifier')}'."}
    field = params.get('field')
    value = params.get('value')
    if field not in ('title', 'description', 'priority', 'tag', 'due_date', 'assignee_email'):
        return {"ok": False, "summary": f"I can't update field '{field}'."}
    if field == 'due_date':
        try:
            card.due_date = datetime.strptime(value, '%Y-%m-%d') if value else None
        except Exception:
            return {"ok": False, "summary": "Due date must be in YYYY-MM-DD format."}
    elif field == 'assignee_email':
        card.assignee_id = _resolve_assignee(value, current_user)
    else:
        setattr(card, field, value)
    card.updated_at = datetime.utcnow()
    db.session.commit()
    return {"ok": True, "summary": f"Updated '{card.title}': {field} -> {value}."}


def tool_board_add_comment(params: Dict[str, Any], current_user) -> Dict[str, Any]:
    from core import models, db
    card = _fuzzy_find_card(params.get('card_identifier', ''))
    if not card:
        return {"ok": False, "summary": f"I couldn't find a card matching '{params.get('card_identifier')}'."}
    body = (params.get('body') or '').strip()
    if not body:
        return {"ok": False, "summary": "Empty comment."}
    comment = models.BoardComment(card_id=card.id, author_id=current_user.id, body=body)
    card.updated_at = datetime.utcnow()
    db.session.add(comment)
    db.session.commit()
    return {"ok": True, "summary": f"Comment added to '{card.title}'."}


def tool_board_list_cards(params: Dict[str, Any], current_user) -> Dict[str, Any]:
    from core import models
    q = models.BoardCard.query.filter(models.BoardCard.column != 'archived')
    column = params.get('column')
    if column and column != 'all':
        q = q.filter_by(column=column)
    tag = params.get('tag')
    if tag and tag != 'all':
        q = q.filter_by(tag=tag)
    assignee = params.get('assignee_email')
    if assignee:
        if assignee.lower() in ('me', 'myself', 'self'):
            q = q.filter_by(assignee_id=current_user.id)
        else:
            user = models.User.query.filter(models.User.email.ilike(assignee)).first()
            if user:
                q = q.filter_by(assignee_id=user.id)
            else:
                return {"ok": True, "summary": f"No user found with email {assignee}."}

    cards = q.order_by(models.BoardCard.column, models.BoardCard.position).limit(20).all()
    if not cards:
        return {"ok": True, "summary": "Nothing matching that filter."}

    # Compact spoken summary
    if len(cards) <= 5:
        lines = []
        for c in cards:
            lines.append(f"{c.title} ({c.column.replace('_',' ')}, {c.priority})")
        summary = f"{len(cards)} card{'s' if len(cards)!=1 else ''}: " + "; ".join(lines)
    else:
        # Group by column
        by_col = {}
        for c in cards:
            by_col.setdefault(c.column, []).append(c.title)
        parts = [f"{len(v)} in {k.replace('_',' ')}" for k, v in by_col.items()]
        summary = f"{len(cards)} cards. " + ", ".join(parts) + ". Open the board for the full list."
    return {"ok": True, "summary": summary, "data": [{"id": c.id, "title": c.title, "column": c.column} for c in cards]}


def tool_board_assign_to_me(params: Dict[str, Any], current_user) -> Dict[str, Any]:
    from core import models, db
    card = _fuzzy_find_card(params.get('card_identifier', ''))
    if not card:
        return {"ok": False, "summary": f"I couldn't find a card matching '{params.get('card_identifier')}'."}
    card.assignee_id = current_user.id
    card.updated_at = datetime.utcnow()
    db.session.commit()
    return {"ok": True, "summary": f"Assigned '{card.title}' to you."}


def tool_latest_grade(params: Dict[str, Any], current_user) -> Dict[str, Any]:
    """Return latest Gemini grade if available."""
    candidates = [
        '/home/ultron/protocol_pulse/video_pipeline_v3/logs/consecutive_a_grades.txt',
        '/home/ultron/protocol_pulse/video_pipeline_v3/output/latest/grade.json',
    ]
    grade_data = None
    for path in candidates:
        try:
            if path.endswith('.json') and os.path.exists(path):
                with open(path) as f:
                    grade_data = json.load(f)
                break
        except Exception:
            continue
    if grade_data:
        score = grade_data.get('overall_score') or grade_data.get('score') or 'unknown'
        bready = grade_data.get('broadcast_ready')
        return {"ok": True, "summary": f"Latest grade: {score} out of 100. Broadcast ready: {bready}."}

    # Fallback: glob recent renders
    import glob
    out_dir = '/home/ultron/protocol_pulse/video_pipeline_v3/output'
    if os.path.isdir(out_dir):
        runs = sorted(glob.glob(os.path.join(out_dir, '*')), key=os.path.getmtime, reverse=True)[:3]
        return {"ok": True, "summary": f"No grade file found. Recent runs: {', '.join(os.path.basename(r) for r in runs) or 'none'}."}
    return {"ok": True, "summary": "No grade data available right now."}


def tool_system_status(params: Dict[str, Any], current_user) -> Dict[str, Any]:
    """Quick health check across Protocol Pulse services."""
    import subprocess
    parts = []
    # Avatar server
    try:
        import urllib.request as ur
        with ur.urlopen('http://localhost:8200/health', timeout=2) as r:
            avatar = 'online' if r.status == 200 else f'status {r.status}'
    except Exception:
        avatar = 'offline'
    parts.append(f"Avatar server {avatar}")
    # Site
    try:
        with ur.urlopen('http://localhost:5000/health', timeout=2) as r:
            site = 'online' if r.status == 200 else f'status {r.status}'
    except Exception:
        site = 'offline'
    parts.append(f"site {site}")
    # GPU
    try:
        out = subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'], timeout=3, text=True)
        gpus = [int(x.strip()) for x in out.splitlines() if x.strip()]
        avg = sum(gpus) // max(len(gpus), 1)
        parts.append(f"GPU avg {avg}%")
    except Exception:
        pass
    return {"ok": True, "summary": "Status: " + ", ".join(parts) + "."}


TOOL_IMPLEMENTATIONS = {
    "board_create_card": tool_board_create_card,
    "board_move_card": tool_board_move_card,
    "board_update_card": tool_board_update_card,
    "board_add_comment": tool_board_add_comment,
    "board_list_cards": tool_board_list_cards,
    "board_assign_to_me": tool_board_assign_to_me,
    "latest_grade": tool_latest_grade,
    "system_status": tool_system_status,
}


# --- System prompt ----------------------------------------------------------

SYSTEM_PROMPT = """You are Satomi, the voice operations agent for the Protocol Pulse team.

You help admin team members manage the Trello-style ops board and check system status by voice. You are intelligent, edgy, confident — never tribal or chatty. Speak in short, direct sentences. No filler. No "great question" preamble.

When the user gives a command:
1. Pick the right tool. Most board edits map to one tool call.
2. If a card identifier is ambiguous, pick the most recent match — don't ask for clarification unless truly impossible.
3. After the tool runs, return a short spoken confirmation (one sentence). The tool's `summary` field is usually fine to repeat or lightly polish.
4. If the user just chats or asks something with no actionable tool, answer in one sentence.

Today's date: {date}. Logged in as: {user_email}.

Never say things like "stay free, stay sovereign" or "no chain but Bitcoin" — that's pipeline-show voice, not ops voice. Just be the operator.
"""


# --- Main entrypoint --------------------------------------------------------

def process_command(text: str, current_user) -> Dict[str, Any]:
    """
    Process a voice command from `text` (already transcribed) and execute against
    the Protocol Pulse stack on behalf of `current_user`.

    Returns:
        {
            "ok": bool,
            "reply": str,                # what Satomi says back
            "tool_calls": [               # what was actually executed
                {"name": str, "input": dict, "result": dict}
            ],
            "engine": "claude" | "gemini" | "fallback"
        }
    """
    text = (text or '').strip()
    if not text:
        return {"ok": False, "reply": "I didn't catch that.", "tool_calls": [], "engine": "fallback"}

    sys_prompt = SYSTEM_PROMPT.format(
        date=datetime.now().strftime('%A, %B %d, %Y'),
        user_email=current_user.email if current_user else 'unknown',
    )

    # Try Claude first
    claude = _claude_client()
    if claude:
        try:
            return _run_claude(claude, text, sys_prompt, current_user)
        except Exception as e:
            logger.warning('Claude path failed, falling back: %s', e)

    # Fallback: Gemini
    genai = _gemini_client()
    if genai:
        try:
            return _run_gemini(genai, text, sys_prompt, current_user)
        except Exception as e:
            logger.warning('Gemini path failed: %s', e)

    return {"ok": False, "reply": "Voice ops backend unavailable. Check API keys.", "tool_calls": [], "engine": "fallback"}


def _run_claude(client, user_text: str, system_prompt: str, current_user) -> Dict[str, Any]:
    """Multi-turn Claude tool-use loop."""
    messages = [{"role": "user", "content": user_text}]
    tool_calls_log = []

    for _turn in range(6):  # safety bound
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=system_prompt,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )
        # Did the model request tools?
        tool_uses = [b for b in resp.content if getattr(b, 'type', '') == 'tool_use']
        text_blocks = [b for b in resp.content if getattr(b, 'type', '') == 'text']
        if not tool_uses:
            reply = "\n".join(b.text for b in text_blocks).strip() or "Done."
            return {"ok": True, "reply": reply, "tool_calls": tool_calls_log, "engine": "claude"}

        # Execute tools, append results, continue
        messages.append({"role": "assistant", "content": resp.content})
        tool_results_block = []
        for tu in tool_uses:
            impl = TOOL_IMPLEMENTATIONS.get(tu.name)
            if not impl:
                result = {"ok": False, "summary": f"Unknown tool {tu.name}"}
            else:
                try:
                    result = impl(tu.input or {}, current_user)
                except Exception as e:
                    logger.exception('Tool %s failed', tu.name)
                    result = {"ok": False, "summary": f"Tool {tu.name} errored: {e}"}
            tool_calls_log.append({"name": tu.name, "input": tu.input, "result": result})
            tool_results_block.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(result),
            })
        messages.append({"role": "user", "content": tool_results_block})

    return {"ok": True, "reply": "Done (loop bound reached).", "tool_calls": tool_calls_log, "engine": "claude"}


def _run_gemini(genai, user_text: str, system_prompt: str, current_user) -> Dict[str, Any]:
    """Gemini fallback — single-shot tool selection. Less iterative than Claude."""
    # Convert Anthropic tool schema -> Gemini FunctionDeclaration
    tools = []
    for t in TOOL_SCHEMAS:
        tools.append({
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        })
    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        system_instruction=system_prompt,
        tools=[{"function_declarations": tools}],
    )
    chat = model.start_chat()
    resp = chat.send_message(user_text)

    tool_calls_log = []
    # Iterate up to 4 times to handle tool-calls
    for _turn in range(4):
        # Look for function calls in response parts
        fcalls = []
        try:
            for part in resp.candidates[0].content.parts:
                fc = getattr(part, 'function_call', None)
                if fc and fc.name:
                    fcalls.append(fc)
        except Exception:
            fcalls = []

        if not fcalls:
            text = ''
            try:
                text = resp.text or ''
            except Exception:
                pass
            return {"ok": True, "reply": text.strip() or "Done.", "tool_calls": tool_calls_log, "engine": "gemini"}

        # Execute and feed results back
        for fc in fcalls:
            params = dict(fc.args) if fc.args else {}
            impl = TOOL_IMPLEMENTATIONS.get(fc.name)
            if not impl:
                result = {"ok": False, "summary": f"Unknown tool {fc.name}"}
            else:
                try:
                    result = impl(params, current_user)
                except Exception as e:
                    logger.exception('Tool %s failed', fc.name)
                    result = {"ok": False, "summary": f"Tool {fc.name} errored: {e}"}
            tool_calls_log.append({"name": fc.name, "input": params, "result": result})

            resp = chat.send_message(
                genai.protos.Content(
                    parts=[genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=fc.name,
                            response={"result": result},
                        )
                    )]
                )
            )

    return {"ok": True, "reply": "Done.", "tool_calls": tool_calls_log, "engine": "gemini"}
