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

if "messages" not in st.session_state:
    st.session_state.messages = []

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
</style>
""", unsafe_allow_html=True)

# ── CLOUD DATABASE CONNECTION ────────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)

def get_ledger():
    # ttl=0 ensures we don't read cached data; always checks the live sheet
    return conn.read(spreadsheet=SPREADSHEET_URL, ttl=0)

def update_ledger(df):
    conn.update(spreadsheet=SPREADSHEET_URL, data=df)

# ── SIDEBAR PART 1: GATEKEEPER ───────────────────────────────────────────────
with st.sidebar:
    st.header("🎟️ Get Access")
    st.markdown("Want 50 log generations? Scan & pay **RM10**.")
    
    if os.path.exists(QR_FILE):
        st.image(QR_FILE, caption="Scan to Pay via DuitNow", use_container_width=True)
        
    st.markdown("Send your receipt screenshot to **[Your Contact]** to receive your Access Passcode.")
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

raw_notes = st.text_area("Drop your messy daily notes here", height=160)
tone = st.selectbox("Tone", options=["Highly Technical", "Management / Soft Skills", "General IT"], index=0)

# ── GENERATION & CLOUD LOGIC ──────────────────────────────────────────────────
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
        try:
            df = get_ledger()
            # Ensure columns exist
            if 'Passcode' not in df.columns or 'Tokens' not in df.columns:
                st.markdown('<div class="error-box">⚠ Database configuration error. Columns missing.</div>', unsafe_allow_html=True)
                st.stop()

            # Check if passcode exists
            if user_passcode not in df['Passcode'].values:
                st.markdown('<div class="error-box">⚠ Invalid passcode. Scan the QR code to buy a token pack.</div>', unsafe_allow_html=True)
                st.stop()

            # Get user's row index and balance
            user_idx = df.index[df['Passcode'] == user_passcode][0]
            current_balance = int(df.at[user_idx, 'Tokens'])

            if current_balance <= 0:
                st.markdown('<div class="error-box">⚠ This passcode has run out of tokens. Please purchase a top-up.</div>', unsafe_allow_html=True)
                st.stop()

        except Exception as e:
            st.markdown(f'<div class="error-box">⚠ Cloud Connection Error: {e}</div>', unsafe_allow_html=True)
            st.stop()

    # 2. Execute API Call
    with st.spinner("Engineering your logbook..."):
        try:
            client = anthropic.Anthropic(api_key=api_key)
            system_prompt = f"You are an expert technical writer. Convert the following rough notes into a professional internship logbook entry. The tone should be {tone}. Use strict bullet points. Structure with DATE, OBJECTIVES, ACTIVITIES PERFORMED, and REFLECTION. Do not invent tasks."
            
            response = client.messages.create(
                model=MODEL, max_tokens=1024, system=system_prompt,
                messages=[{"role": "user", "content": raw_notes}]
            )
            generated_log = response.content[0].text
            
            # 3. Post-API Cloud Deduction
            df.at[user_idx, 'Tokens'] = current_balance - 1
            update_ledger(df)
            tokens_left = current_balance - 1
            
            # 4. Display Results
            st.session_state.messages.append(generated_log)
            st.success(f"Success! {tokens_left} tokens remaining on passcode {user_passcode}.")
            st.markdown(f'<div class="output-wrapper"><div class="output-body">{generated_log}</div></div>', unsafe_allow_html=True)
            st.code(generated_log, language=None)
            
        except Exception as e:
            st.markdown(f'<div class="error-box">⚠ API Error: {e}</div>', unsafe_allow_html=True)

st.markdown('<div style="text-align:center; margin-top:3rem; font-size:0.7rem; color:#6b7280;">POWERED BY CLAUDE HAIKU · CLOUD DATABASE ACTIVE</div>', unsafe_allow_html=True)

# ── SIDEBAR PART 2: HISTORY ──────────────────────────────────────────────────
with st.sidebar:
    st.divider()
    st.header("📜 Session History")
    if st.button("Clear History"):
        st.session_state.messages = []
        st.rerun()
    for idx, msg in enumerate(reversed(st.session_state.messages)):
        log_number = len(st.session_state.messages) - idx
        with st.expander(f"Log {log_number}"):
            st.markdown(msg)
            st.divider()
            st.caption("Copy raw text below:")
            st.code(msg, language=None)