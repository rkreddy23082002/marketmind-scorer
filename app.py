import streamlit as st
import requests
import json
import re

st.set_page_config(
    page_title="MarketMind Opportunity Scorer",
    page_icon="📊",
    layout="centered",
)

# ---------- Styling ----------
st.markdown("""
<style>
.stApp { background-color: #FAF9F5; }
h1, h2, h3, p, label, .stMarkdown, .stCaption { color: #16233B !important; }
.score-badge {
    width: 64px; height: 64px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.6rem; font-weight: 700; color: white !important;
    margin: 0 auto 12px auto;
}
.result-card {
    background: white; border: 1px solid #E6E1D6; border-radius: 10px;
    padding: 24px; margin-top: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.result-card h3 { color: #16233B !important; }
.result-card p { color: #16233B !important; }
.reason-text { color: #454C5C !important; font-size: 1.05rem; line-height: 1.5; }
</style>
""", unsafe_allow_html=True)

# ---------- Header ----------
st.title("📊 MarketMind Opportunity Scorer")
st.caption("Paste in a market signal — a funding announcement, a news headline, a trend you noticed — and get an AI-scored read on whether it's worth your time.")

st.divider()

# ---------- API key handling ----------
# On Streamlit Community Cloud, set this in Settings -> Secrets as:
# GEMINI_API_KEY = "your-key-here"
# Never hardcode a real key in this file.
api_key = st.secrets.get("GEMINI_API_KEY", None)

if not api_key:
    st.warning(
        "⚠️ No Gemini API key configured. The app owner needs to add a `GEMINI_API_KEY` "
        "in Streamlit's Secrets settings for scoring to work. You can still see the form below."
    )

# ---------- Input form ----------
st.subheader("Describe the signal")

col1, col2 = st.columns(2)
with col1:
    company_or_topic = st.text_input(
        "Company or Topic",
        placeholder="e.g. Xona Space Systems",
        help="Who or what this signal is about. This becomes the headline of your scored result.",
    )
with col2:
    industry_category = st.text_input(
        "Industry / Category",
        placeholder="e.g. Space, Startups, GPS",
        help="A few keywords describing the sector — helps the AI judge market context.",
    )

metric_or_headline = st.text_area(
    "Headline or Signal Description",
    placeholder="e.g. Xona's commercial GPS alternative is about to go live",
    help="The actual news, announcement, or signal you want scored. Be specific — more detail gives the AI more to reason about.",
    height=100,
)

source_url = st.text_input(
    "Source URL (optional)",
    placeholder="https://...",
    help="Link back to where you found this signal, if you have one.",
)

submitted = st.button("Score This Opportunity", type="primary", use_container_width=True)

st.divider()

# ---------- Scoring logic ----------
def score_opportunity(company, industry, headline, key):
    """Calls Gemini and returns (score, reason, error_message)."""
    prompt = (
        f"Score this market opportunity from 1-10 and give a one-sentence reason. "
        f"Company/Topic: {company}. Industry: {industry}. Signal: {headline}. "
        f'Respond ONLY as JSON: {{"score": <number>, "reason": "<text>"}}'
    )
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.5-flash-lite:generateContent?key={key}"
    )
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        resp = requests.post(url, json=body, timeout=20)
    except requests.exceptions.Timeout:
        return None, None, "The AI took too long to respond. Please try again in a moment."
    except requests.exceptions.ConnectionError:
        return None, None, "Couldn't reach the AI service. Check your internet connection and try again."

    if resp.status_code == 429:
        return None, None, "We've hit the AI service's rate limit for the moment. Please wait a minute and try again."
    if resp.status_code == 404:
        return None, None, "The AI model being used is no longer available. Please let the tool owner know."
    if resp.status_code != 200:
        return None, None, f"The AI service returned an unexpected error (code {resp.status_code}). Please try again."

    try:
        raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        cleaned = re.sub(r"```json\n?|\n?```", "", raw_text).strip()
        parsed = json.loads(cleaned)
        score = parsed.get("score")
        reason = parsed.get("reason")
        if score is None or reason is None:
            raise ValueError("Missing score or reason in AI response")
        return score, reason, None
    except (KeyError, IndexError, json.JSONDecodeError, ValueError):
        return None, None, "The AI's response couldn't be understood. This sometimes happens — please try again."


def score_color(score):
    if score is None:
        return "#6B7280"
    if score >= 7:
        return "#2E6B45"
    if score >= 4:
        return "#B0722A"
    return "#9C3F55"


# ---------- Handle submission ----------
if submitted:
    # Input validation — plain-English errors, no stack traces
    missing = []
    if not company_or_topic.strip():
        missing.append("Company or Topic")
    if not industry_category.strip():
        missing.append("Industry / Category")
    if not metric_or_headline.strip():
        missing.append("Headline or Signal Description")

    if missing:
        st.error(
            f"Please fill in the following before scoring: **{', '.join(missing)}**. "
            "All three fields help the AI understand the opportunity — without them, it can't give you a meaningful score."
        )
    elif not api_key:
        st.error("This tool isn't fully set up yet — no AI key is configured. Please contact the tool owner.")
    else:
        with st.spinner("Scoring this opportunity..."):
            score, reason, error = score_opportunity(
                company_or_topic, industry_category, metric_or_headline, api_key
            )

        if error:
            st.error(f"⚠️ {error}")
        else:
            color = score_color(score)
            st.markdown(f"""
            <div class="result-card">
                <div class="score-badge" style="background:{color}">{score}</div>
                <h3 style="text-align:center; margin-bottom:4px;">{company_or_topic}</h3>
                <p style="text-align:center; color:#6B7280; font-size:0.85rem; margin-bottom:16px;">{industry_category}</p>
                <p style="font-weight:600;">{metric_or_headline}</p>
                <p class="reason-text">{reason}</p>
                {f'<p><a href="{source_url}" target="_blank">View source →</a></p>' if source_url.strip() else ''}
            </div>
            """, unsafe_allow_html=True)

st.divider()
st.caption("Built with Streamlit + Google Gemini · MarketMind Opportunity Scorer")
