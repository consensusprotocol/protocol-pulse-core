#!/usr/bin/env python3
"""
PHASE 4 GATE TEST — Conversation Quality Edge Cases
10 scenarios — all must pass.
Tests: confusion detection, frustration handling, setup tangent recovery,
       vision carry-forward, conversation repair, clean sessions.
"""

import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "oracle"))

import oracle_dialogue_engine as ode


def _mock_haiku_response(text):
    """Create a mock requests.Response for Haiku API calls."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "content": [{"text": text}]
    }
    return mock_resp


def _fresh_session(session_id="test"):
    """Reset and return a clean session."""
    with ode._sessions_lock:
        if session_id in ode._sessions:
            del ode._sessions[session_id]
    return ode._get_session(session_id)


def _inject_history(session_id, messages):
    """Inject conversation history into a session."""
    session = ode._get_session(session_id)
    for role, content in messages:
        session["history"].append({"role": role, "content": content})
        if role == "user":
            session["turn"] += 1
    return session


class Phase4ConversationQuality(unittest.TestCase):
    """Phase 4: Conversation quality edge case tests."""

    def setUp(self):
        """Clean session state before each test."""
        with ode._sessions_lock:
            ode._sessions.clear()

    # ── Test 1: Repeated question triggers confusion detection ──────────
    def test_01_user_repeats_question(self):
        """When user sends the same message twice, confusion detection fires."""
        sid = "repeat_test"
        session = _fresh_session(sid)
        # Simulate first exchange
        session["history"].append({"role": "user", "content": "what is a cold wallet"})
        session["history"].append({"role": "assistant", "content": "A cold wallet stores keys offline."})
        session["turn"] = 1

        # Now call generate_response with the repeated message
        with patch("requests.post") as mock_post:
            mock_post.return_value = _mock_haiku_response(
                "I may have misread what you need — can you tell me differently?"
            )
            result = ode.generate_response(sid, "what is a cold wallet")

        # The context sent to Haiku should contain confusion detection
        call_args = mock_post.call_args
        messages_sent = call_args.kwargs.get("json", call_args[1].get("json", {}))["messages"]
        last_msg = messages_sent[-1]["content"]
        self.assertIn("DETECT: User repeated their message", last_msg,
                       "Confusion detection must fire when user repeats a message")

    # ── Test 2: Frustrated user gets empathetic response ────────────────
    def test_02_frustrated_user(self):
        """Frustration signals trigger AMIABLE pivot and empathy context."""
        sid = "frustration_test"
        _fresh_session(sid)

        with patch("requests.post") as mock_post:
            mock_post.return_value = _mock_haiku_response(
                "I hear you — let's slow down and fix this together. What step are you stuck on?"
            )
            result = ode.generate_response(
                sid, "I've been trying to do this for 3 hours and nothing works"
            )

        call_args = mock_post.call_args
        messages_sent = call_args.kwargs.get("json", call_args[1].get("json", {}))["messages"]
        last_msg = messages_sent[-1]["content"]
        self.assertIn("EMOTIONAL STATE", last_msg,
                       "Frustration detection must inject EMOTIONAL STATE context")
        # Personality should pivot to AMIABLE
        session = ode._get_session(sid)
        self.assertEqual(session["personality"], "AMIABLE",
                         "Personality must pivot to AMIABLE on frustration")

    # ── Test 3: Mid-setup tangent detection ─────────────────────────────
    def test_03_tangent_mid_setup(self):
        """Off-topic question during setup flow triggers tangent handling."""
        sid = "tangent_test"
        session = _fresh_session(sid)
        # Activate Coldcard setup flow at step 1 (PIN)
        session["setup_flow"] = {
            "active": True,
            "device": "coldcard",
            "step": 1,
            "steps": ode._SETUP_STEPS.get("coldcard", [("Verify seal", ["sealed"])]),
            "total_steps": len(ode._SETUP_STEPS.get("coldcard", [])),
        }
        session["turn"] = 2
        session["history"] = [
            {"role": "user", "content": "Coldcard in front of me"},
            {"role": "assistant", "content": "Step one of six: verify the tamper seal."},
            {"role": "user", "content": "seal ok"},
            {"role": "assistant", "content": "Step two of six: set your PIN."},
        ]

        with patch("requests.post") as mock_post:
            mock_post.return_value = _mock_haiku_response(
                "Bitcoin is digital money with a fixed supply. Want to pick back up on step 2 of your coldcard setup?"
            )
            result = ode.generate_response(sid, "actually wait how does Bitcoin work?")

        call_args = mock_post.call_args
        messages_sent = call_args.kwargs.get("json", call_args[1].get("json", {}))["messages"]
        last_msg = messages_sent[-1]["content"]
        self.assertIn("SETUP TANGENT DETECTED", last_msg,
                       "Tangent detection must fire for off-topic question during setup")

    # ── Test 4: Vision context carry-forward ─────────────────────────────
    def test_04_vision_carry_forward(self):
        """Vision history stored in session is injected into generate_response context."""
        sid = "vision_test"
        session = _fresh_session(sid)
        # Simulate vision analysis was stored
        session["vision_history"] = [
            {"turn": 2, "summary": "Coldcard seed confirmation screen — 24 words displayed"},
        ]
        session["turn"] = 3
        session["history"] = [
            {"role": "user", "content": "I'm setting up my Coldcard"},
            {"role": "assistant", "content": "Great, let's do this step by step."},
            {"role": "user", "content": "[showed camera: seed screen]"},
            {"role": "assistant", "content": "I can see your seed confirmation screen."},
        ]

        with patch("requests.post") as mock_post:
            mock_post.return_value = _mock_haiku_response(
                "Based on the seed screen I saw, verify each word matches your backup. Does word five match?"
            )
            result = ode.generate_response(
                sid, "I showed you that screen — what did I do wrong?"
            )

        call_args = mock_post.call_args
        messages_sent = call_args.kwargs.get("json", call_args[1].get("json", {}))["messages"]
        last_msg = messages_sent[-1]["content"]
        self.assertIn("VISION HISTORY", last_msg,
                       "Vision history must be injected into context when available")
        self.assertIn("seed confirmation", last_msg.lower(),
                       "Vision summary content must appear in context")

    # ── Test 5: Vague follow-up triggers conversation repair ────────────
    def test_05_vague_followup_repair(self):
        """System prompt includes conversation repair instruction."""
        self.assertIn("CONVERSATION REPAIR", ode._SYSTEM_PROMPT,
                       "System prompt must contain CONVERSATION REPAIR instruction")
        self.assertIn("what about that", ode._SYSTEM_PROMPT.lower(),
                       "Repair instruction must mention vague follow-up examples")

    # ── Test 6: Frustration then calm — personality pivot then recovery ──
    def test_06_frustration_then_calm(self):
        """Frustration pivots to AMIABLE; calm follow-up doesn't force AMIABLE."""
        sid = "frustration_calm"
        _fresh_session(sid)

        with patch("requests.post") as mock_post:
            mock_post.return_value = _mock_haiku_response(
                "I hear you — let's slow down. What exact step are you on?"
            )
            ode.generate_response(sid, "this is ridiculous nothing works!!!")

        session = ode._get_session(sid)
        self.assertEqual(session["personality"], "AMIABLE",
                         "Personality must be AMIABLE after frustration")

        # Follow-up calm message — AMIABLE should persist (blended) but no frustration context
        with patch("requests.post") as mock_post:
            mock_post.return_value = _mock_haiku_response(
                "Great. Let's start fresh from step one. Do you have your device ready?"
            )
            ode.generate_response(sid, "ok i feel better now, let's try again")

        call_args = mock_post.call_args
        messages_sent = call_args.kwargs.get("json", call_args[1].get("json", {}))["messages"]
        last_msg = messages_sent[-1]["content"]
        # No EMOTIONAL STATE should fire on the calm message
        self.assertNotIn("EMOTIONAL STATE", last_msg,
                          "Calm follow-up must NOT trigger frustration detection")

    # ── Test 7: Setup intact after tangent ──────────────────────────────
    def test_07_setup_intact_after_tangent(self):
        """After a tangent, returning to setup keeps the flow active."""
        sid = "tangent_resume"
        session = _fresh_session(sid)
        session["setup_flow"] = {
            "active": True,
            "device": "coldcard",
            "step": 1,
            "steps": ode._SETUP_STEPS.get("coldcard", []),
            "total_steps": len(ode._SETUP_STEPS.get("coldcard", [])),
        }
        session["turn"] = 3
        session["history"] = [
            {"role": "user", "content": "Coldcard arrived setting up"},
            {"role": "assistant", "content": "Step one: verify seal."},
            {"role": "user", "content": "seal ok"},
            {"role": "assistant", "content": "Step two: set PIN."},
            {"role": "user", "content": "what is inflation?"},
            {"role": "assistant", "content": "Inflation erodes purchasing power. Want to resume step 2?"},
        ]

        # User says "ok back to setup" — flow should still be active
        with patch("requests.post") as mock_post:
            mock_post.return_value = _mock_haiku_response(
                "Step two of six: Set your PIN now — six to twelve digits. Did you pick one?"
            )
            result = ode.generate_response(sid, "ok back to setup")

        session = ode._get_session(sid)
        self.assertTrue(session["setup_flow"]["active"],
                         "Setup flow must remain active after tangent + return")
        self.assertEqual(session["setup_flow"]["device"], "coldcard",
                         "Setup device must still be coldcard")

    # ── Test 8: Garbled input triggers clarification ─────────────────────
    def test_08_garbled_input(self):
        """Very short/garbled input (< 3 words, no intent words) triggers clarification."""
        sid = "garbled_test"
        _fresh_session(sid)

        with patch("requests.post") as mock_post:
            mock_post.return_value = _mock_haiku_response(
                "I want to make sure I understand — what are you trying to do?"
            )
            result = ode.generate_response(sid, "asdfg")

        call_args = mock_post.call_args
        messages_sent = call_args.kwargs.get("json", call_args[1].get("json", {}))["messages"]
        last_msg = messages_sent[-1]["content"]
        self.assertIn("DETECT: Very short or unclear input", last_msg,
                       "Garbled input must trigger short/unclear detection")

    # ── Test 9: Long frustrated rant ─────────────────────────────────────
    def test_09_long_rant(self):
        """Long frustrated message still triggers frustration detection."""
        sid = "rant_test"
        _fresh_session(sid)

        rant = ("I cannot believe this - I've been trying to set up this stupid wallet for 6 hours, "
                "nothing is working, the instructions are garbage, I'm about to give up entirely")

        with patch("requests.post") as mock_post:
            mock_post.return_value = _mock_haiku_response(
                "I hear you — six hours is brutal. Let's slow down and tackle one thing. What device do you have?"
            )
            result = ode.generate_response(sid, rant)

        call_args = mock_post.call_args
        messages_sent = call_args.kwargs.get("json", call_args[1].get("json", {}))["messages"]
        last_msg = messages_sent[-1]["content"]
        self.assertIn("EMOTIONAL STATE", last_msg,
                       "Long rant must trigger frustration detection")
        session = ode._get_session(sid)
        self.assertEqual(session["personality"], "AMIABLE",
                         "Long rant must pivot personality to AMIABLE")

    # ── Test 10: Clean new session ───────────────────────────────────────
    def test_10_clean_new_session(self):
        """Fresh session has no stale context from other sessions."""
        sid = "fresh_session_test"
        session = _fresh_session(sid)

        self.assertEqual(session["turn"], 0, "Fresh session must start at turn 0")
        self.assertEqual(session["history"], [], "Fresh session must have empty history")
        self.assertIsNone(session["personality"], "Fresh session must have no personality")
        self.assertFalse(session["setup_flow"]["active"],
                          "Fresh session must have no active setup flow")
        self.assertEqual(session.get("vision_history", []), [],
                          "Fresh session must have no vision history")


# ── Gate summary ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  PHASE 4 GATE — Conversation Quality (10 scenarios)")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Phase4ConversationQuality)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    if result.wasSuccessful():
        print("✅  PHASE 4 GATE: ALL 10 PASSED")
    else:
        failed = len(result.failures) + len(result.errors)
        print(f"❌  PHASE 4 GATE: {failed} FAILED — fix before proceeding")

    sys.exit(0 if result.wasSuccessful() else 1)
