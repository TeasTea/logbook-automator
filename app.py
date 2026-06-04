import streamlit as st
import anthropic
import os
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ── CONFIGURATION ────────────────────────────────────────────────────────────
MODEL = "claude-haiku-4-5"
LOGO_FILE = "Gemini_Generated_Image_83l7jt83l7jt83l7.png"
QR_FILE = "qr_code.jpeg"

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1z_K3DGC9BbGMNNSDLzJjFzliHLzH2vA1ndX2VjIQnzI/edit?usp=sharing"

# ── Page configuration ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Internship Logbook Automator",
    page_icon="📓",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── SESSION STATE INITIALISATION ─────────────────────────────────────────────
if "messages"         not in st.session_state: st.session_state.messages         = []
if "current_logbook"  not in st.session_state: st.session_state.current_logbook  = None
if "original_notes"   not in st.session_state: st.session_state.original_notes   = ""
if "active_passcode"  not in st.session_state: st.session_state.active_passcode  = ""
if "active_tone"      not in st.session_state: st.session_state.active_tone      = ""
if "weekly_summary"   not in st.session_state: st.session_state.weekly_summary   = None

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"] { background: #0d0e12 !important; }
[data-testid="stAppViewContainer"] {
    background: radial-gradient(ellipse 80% 40% at 50% -10%, rgba(99,102,241,0.18) 0%, transparent 70%),
                radial-gradient(ellipse 40% 30% at 90% 80%, rgba(244,114,182,0.10) 0%, transparent 60%),
                #0d0e12 !important; min-height: 100vh;
}
[data-testid="stHeader"] { background: transparent !important; }
.block-container { max-width: 740px !important; padding: 3rem 2rem 4rem !important; font-family: 'DM Sans', sans-serif; }
.logbook-header { text-align: center; margin-bottom: 2.8rem; }
.logbook-header .badge { display: inline-block; font-family: 'DM Mono', monospace; font-size: 0.68rem; font-weight: 500; letter-spacing: 0.18em; text-transform: uppercase; color: #a5b4fc; background: rgba(99,102,241,0.12); border: 1px solid rgba(99,102,241,0.3); border-radius: 999px; padding: 0.28rem 0.9rem; margin-bottom: 1rem; }
.logbook-header h1 { font-family: 'DM Serif Display', serif; font-size: 2.6rem; font-weight: 400; color: #f0f0f5; line-height: 1.18; margin: 0 0 0.7rem; letter-spacing: -0.01em; }
.logbook-header h1 em { font-style: italic; color: #a5b4fc; }
.logbook-header p { font-size: 0.95rem; color: #6b7280; margin: 0; font-weight: 300; letter-spacing: 0.01em; }
textarea, .stTextArea textarea { background: rgba(255,255,255,0.04) !important; border: 1px solid rgba(255,255,255,0.1) !important; border-radius: 10px !important; color: #e0e0ec !important; font-family: 'DM Sans', sans-serif !important; font-size: 0.93rem !important; font-weight: 300 !important; line-height: 1.6 !important; resize: vertical !important; }
textarea:focus, .stTextArea textarea:focus { border-color: rgba(99,102,241,0.5) !important; box-shadow: 0 0 0 3px rgba(99,102,241,0.08) !important; outline: none !important; }
.stButton > button { width: 100%; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important; color: #fff !important; border: none !important; border-radius: 10px !important; font-family: 'DM Sans', sans-serif !important; font-size: 0.93rem !important; font-weight: 600 !important; letter-spacing: 0.03em !important; padding: 0.75rem 1.5rem !important; margin-top: 0.4rem !important; }
.output-wrapper { background: rgba(255,255,255,0.03); border: 1px solid rgba(99,102,241,0.2); border-radius: 16px; padding: 1.8rem; margin-top: 1.6rem; }
.output-body { font-family: 'DM Sans', sans-serif; font-size: 0.92rem; font-weight: 300; color: #d0d0de; line-height: 1.75; white-space: pre-wrap; }
.error-box { background: rgba(239,68,68,0.07); border: 1px solid rgba(239,68,68,0.25); border-radius: 12px; padding: 1rem 1.3rem; color: #fca5a5; font-family: 'DM Mono', monospace; font-size: 0.82rem; margin-top: 1rem; }
.refine-label { font-family: 'DM Mono', monospace; font-size: 0.68rem; font-weight: 500; letter-spacing: 0.16em; text-transform: uppercase; color: #6366f1; padding-top: 1.2rem; border-top: 1px solid rgba(99,102,241,0.18); margin-bottom: 0.6rem; display: block; }
.refine-note { font-family: 'DM Mono', monospace; font-size: 0.68rem; color: #4b5563; margin-top: 0.6rem; }
.weekly-hint { font-family: 'DM Sans', sans-serif; font-size: 0.85rem; color: #6b7280; margin-bottom: 1rem; line-height: 1.55; }

/* ── Search-bar form: fuse input + submit button into one pill ── */
div[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}
div[data-testid="stForm"] > div:first-child {
    display: flex !important;
    gap: 0 !important;
    align-items: stretch !important;
}
div[data-testid="stForm"] input[type="text"] {
    border-radius: 10px 0 0 10px !important;
    border-right: none !important;
    height: 2.75rem !important;
}
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] > button {
    border-radius: 10px !important;
    margin-top: 0.5rem !important;
    height: 2.75rem !important;
    width: auto !important;
    padding: 0 1.4rem !important;
    white-space: nowrap !important;
}
</style>
""", unsafe_allow_html=True)

# ── CLOUD DATABASE CONNECTION ────────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)

def get_ledger():
    return conn.read(spreadsheet=SPREADSHEET_URL, ttl=0)

def update_ledger(df):
    conn.update(spreadsheet=SPREADSHEET_URL, data=df)

# ── SHARED HELPER: passcode validation + token deduction ─────────────────────
# Returns (success: bool, df, user_idx, tokens_left, error_html: str|None)
# On success: df and user_idx are ready; token has NOT been deducted yet.
# Caller deducts AFTER a confirmed API response.
def validate_and_fetch(passcode: str):
    try:
        df = get_ledger()
        if 'Passcode' not in df.columns or 'Tokens' not in df.columns:
            return False, None, None, None, '<div class="error-box">⚠ Database configuration error. Columns missing.</div>'
        if passcode not in df['Passcode'].values:
            return False, None, None, None, '<div class="error-box">⚠ Invalid passcode. Scan the QR code to buy a token pack.</div>'
        user_idx = df.index[df['Passcode'] == passcode][0]
        current_balance = int(df.at[user_idx, 'Tokens'])
        if current_balance <= 0:
            return False, None, None, None, '<div class="error-box">⚠ This passcode has run out of tokens. Please purchase a top-up.</div>'
        return True, df, user_idx, current_balance, None
    except Exception as e:
        return False, None, None, None, f'<div class="error-box">⚠ Cloud Connection Error: {e}</div>'

# ── SIDEBAR PART 1: GATEKEEPER ───────────────────────────────────────────────
with st.sidebar:
    st.header("🎟️ Get Access")
    st.markdown("Want 50 log generations? Scan & pay **RM10**.")
    
    if os.path.exists(QR_FILE):
        st.image(QR_FILE, caption="Scan to Pay via DuitNow", use_container_width=True)
        
    st.markdown("Send your receipt screenshot to **+60135636986** to receive your Access Passcode.")
    st.divider()
    
    st.header("🔑 Gatekeeper")
    user_passcode_input = st.text_input("Enter Access Passcode:", type="password")

# ── MAIN APP UI ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="logbook-header">
    <div class="badge">AI-Powered</div>
    <h1>Internship <em>Logbook</em><br>Automator</h1>
    <p>Turn messy daily notes into polished academic logbook entries — instantly.</p>
</div>
""", unsafe_allow_html=True)

# ── TABS ─────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📝 Daily Log", "📅 Weekly Wrap-Up"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — DAILY LOG
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    raw_notes = st.text_area("Drop your messy daily notes here", height=160)
    tone = st.selectbox("Tone", options=["Highly Technical", "Management / Soft Skills", "General IT"], index=0)

    # ── GENERATE BUTTON ───────────────────────────────────────────────────
    if st.button("✦  Generate Logbook Entry", type="primary"):
        if not raw_notes.strip():
            st.markdown('<div class="error-box">⚠ Please enter some notes first.</div>', unsafe_allow_html=True)
            st.stop()
        if not user_passcode_input.strip():
            st.markdown('<div class="error-box">⚠ Please enter your Access Passcode in the sidebar.</div>', unsafe_allow_html=True)
            st.stop()

        user_passcode = user_passcode_input.strip().upper()
        api_key = st.secrets.get("ANTHROPIC_API_KEY")

        with st.spinner("Connecting to Google Cloud Database..."):
            ok, df, user_idx, current_balance, err_html = validate_and_fetch(user_passcode)
            if not ok:
                st.markdown(err_html, unsafe_allow_html=True)
                st.stop()

        with st.spinner("Engineering your logbook..."):
            try:
                client = anthropic.Anthropic(api_key=api_key)
                system_prompt = f"You are an expert technical writer. Convert the following rough notes into a professional internship logbook entry. The tone should be {tone}. Use strict bullet points. Structure with DATE, OBJECTIVES, ACTIVITIES PERFORMED, and REFLECTION. Do not invent tasks."
                response = client.messages.create(
                    model=MODEL, max_tokens=1024, system=system_prompt,
                    messages=[{"role": "user", "content": raw_notes}]
                )
                generated_log = response.content[0].text

                # Deduct token ONLY after confirmed API success
                df.at[user_idx, 'Tokens'] = current_balance - 1
                update_ledger(df)
                tokens_left = current_balance - 1

                # Persist state for the Refine feature
                st.session_state.current_logbook = generated_log
                st.session_state.original_notes  = raw_notes
                st.session_state.active_passcode = user_passcode
                st.session_state.active_tone     = tone

                # Add to sidebar history
                st.session_state.messages.append(generated_log)

                st.success(f"Success! {tokens_left} tokens remaining on passcode {user_passcode}.")

            except Exception as e:
                st.markdown(f'<div class="error-box">⚠ API Error: {e}</div>', unsafe_allow_html=True)
                st.stop()

    # ── DISPLAY CURRENT LOGBOOK (persists across all reruns) ──────────────
    if st.session_state.current_logbook:
        logbook_text = st.session_state.current_logbook

        st.markdown(
            f'<div class="output-wrapper"><div class="output-body">{logbook_text}</div></div>',
            unsafe_allow_html=True,
        )

        # ── REFINE SECTION ────────────────────────────────────────────────
        st.markdown(
            '<div class="refine-label" style="margin-top:1.4rem;">✦ Refine This Entry</div>',
            unsafe_allow_html=True,
        )

        with st.form(key="refine_form", clear_on_submit=False):
            refine_instruction = st.text_input(
                "refine_input",
                placeholder="e.g. 'Make it shorter', 'Add a point about the database'",
                label_visibility="collapsed",
                key="refine_input",
            )
            refine_clicked = st.form_submit_button("✦ Refine Output")

        st.markdown(
            '<p class="refine-note">💡 Refining uses no additional tokens.</p>',
            unsafe_allow_html=True,
        )

        # ── REFINE LOGIC ──────────────────────────────────────────────────
        if refine_clicked:
            if not refine_instruction.strip():
                st.markdown(
                    '<div class="error-box">⚠ Please describe what you want changed before clicking Refine.</div>',
                    unsafe_allow_html=True,
                )
            else:
                api_key = st.secrets.get("ANTHROPIC_API_KEY")
                with st.spinner("Applying your refinements…"):
                    try:
                        client = anthropic.Anthropic(api_key=api_key)

                        refine_system = (
                            "You are an expert technical writer assisting with an internship logbook. "
                            "The user will give you: (1) their original rough notes, "
                            "(2) a previously drafted logbook entry, and "
                            "(3) specific refinement instructions. "
                            f"Maintain the {st.session_state.active_tone} tone throughout. "
                            "Apply ONLY the requested changes. Do not invent new tasks or details "
                            "not present in the original notes. Return the full refined logbook entry."
                        )

                        refine_user_message = (
                            f"ORIGINAL ROUGH NOTES:\n{st.session_state.original_notes}\n\n"
                            f"CURRENT LOGBOOK DRAFT:\n{st.session_state.current_logbook}\n\n"
                            f"REFINEMENT INSTRUCTION:\n{refine_instruction.strip()}"
                        )

                        refine_response = client.messages.create(
                            model=MODEL,
                            max_tokens=1024,
                            system=refine_system,
                            messages=[{"role": "user", "content": refine_user_message}]
                        )

                        refined_log = refine_response.content[0].text

                        st.session_state.current_logbook = refined_log

                        if st.session_state.messages:
                            st.session_state.messages[-1] = refined_log
                        else:
                            st.session_state.messages.append(refined_log)

                        st.success("Entry refined! No tokens were deducted.")
                        st.rerun()

                    except anthropic.RateLimitError:
                        st.markdown(
                            '<div class="error-box">⚠️ Server busy right now. Wait 5 seconds and try again.</div>',
                            unsafe_allow_html=True,
                        )
                    except Exception as e:
                        st.markdown(
                            f'<div class="error-box">⚠ Refinement error: {e}</div>',
                            unsafe_allow_html=True,
                        )

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — WEEKLY WRAP-UP
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown(
        '<p class="weekly-hint">Paste your 5 daily logbook entries below. '
        'The AI will synthesize them into a single professional weekly summary — '
        'no bullet points, just clean paragraphs. Costs 1 token.</p>',
        unsafe_allow_html=True,
    )

    weekly_notes = st.text_area(
        "Paste your 5 daily logs here",
        height=300,
        placeholder="--- Day 1 ---\n...\n\n--- Day 2 ---\n...\n\n--- Day 3 ---\n...",
    )

    if st.button("📅  Generate Weekly Summary", type="primary"):
        if not weekly_notes.strip():
            st.markdown('<div class="error-box">⚠ Please paste your daily logs first.</div>', unsafe_allow_html=True)
            st.stop()
        if not user_passcode_input.strip():
            st.markdown('<div class="error-box">⚠ Please enter your Access Passcode in the sidebar.</div>', unsafe_allow_html=True)
            st.stop()

        user_passcode = user_passcode_input.strip().upper()
        api_key = st.secrets.get("ANTHROPIC_API_KEY")

        # Validate passcode (same logic as Tab 1, via shared helper)
        with st.spinner("Connecting to Google Cloud Database..."):
            ok, df, user_idx, current_balance, err_html = validate_and_fetch(user_passcode)
            if not ok:
                st.markdown(err_html, unsafe_allow_html=True)
                st.stop()

        # Call Claude API for weekly synthesis
        with st.spinner("Synthesizing your week…"):
            try:
                client = anthropic.Anthropic(api_key=api_key)

                weekly_system = (
                    "You are an expert technical writer. The user will provide multiple daily "
                    "internship logs. Synthesize them into a single, professional 2-paragraph "
                    "weekly summary highlighting the main achievements, challenges resolved, "
                    "and overall progress. Do not use bullet points."
                )

                weekly_response = client.messages.create(
                    model=MODEL,
                    max_tokens=1024,
                    system=weekly_system,
                    messages=[{"role": "user", "content": weekly_notes}]
                )
                weekly_output = weekly_response.content[0].text

                # Deduct token ONLY after confirmed API success
                df.at[user_idx, 'Tokens'] = current_balance - 1
                update_ledger(df)
                tokens_left = current_balance - 1

                # Persist and add to sidebar history
                st.session_state.weekly_summary = weekly_output
                st.session_state.messages.append(f"[WEEKLY WRAP-UP]\n{weekly_output}")

                st.success(f"Weekly summary generated! {tokens_left} tokens remaining on passcode {user_passcode}.")

            except anthropic.RateLimitError:
                st.markdown(
                    '<div class="error-box">⚠️ Server busy right now. Wait 5 seconds and try again.</div>',
                    unsafe_allow_html=True,
                )
                st.stop()
            except Exception as e:
                st.markdown(f'<div class="error-box">⚠ API Error: {e}</div>', unsafe_allow_html=True)
                st.stop()

    # Display weekly summary (persists across reruns)
    if st.session_state.weekly_summary:
        st.markdown(
            f'<div class="output-wrapper"><div class="output-body">{st.session_state.weekly_summary}</div></div>',
            unsafe_allow_html=True,
        )

# ── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown('<div style="text-align:center; margin-top:3rem; font-size:0.7rem; color:#6b7280;">POWERED BY CLAUDE HAIKU · CLOUD DATABASE ACTIVE</div>', unsafe_allow_html=True)

# ── SIDEBAR PART 2: HISTORY ──────────────────────────────────────────────────
with st.sidebar:
    st.divider()
    st.header("📜 Session History")
    
    if st.button("Clear History"):
        st.session_state.messages        = []
        st.session_state.current_logbook = None
        st.session_state.original_notes  = ""
        st.session_state.active_passcode = ""
        st.session_state.active_tone     = ""
        st.session_state.weekly_summary  = None
        st.rerun()
        
    for idx, msg in enumerate(reversed(st.session_state.messages)):
        log_number = len(st.session_state.messages) - idx
        label = f"Weekly Wrap-Up {log_number}" if msg.startswith("[WEEKLY WRAP-UP]") else f"Log {log_number}"
        with st.expander(label):
            clean_msg = msg.replace("[WEEKLY WRAP-UP]\n", "")
            st.markdown(clean_msg)
            st.divider()
            st.caption("Copy raw text below:")
            st.code(clean_msg, language=None)
            
    # --- FEEDBACK SECTION ---
    st.markdown("---")
    st.markdown("### 🗣️ Got Feedback?")
    st.markdown("Help improve the app or report bugs! Takes 30 seconds.")
    st.link_button("📝 Give Feedback", "https://docs.google.com/forms/d/e/1FAIpQLSfTHvUEbkJraHZseXpIfnZF55T21O7bYcREMxUix2iwbJ_87Q/viewform?usp=dialog")
