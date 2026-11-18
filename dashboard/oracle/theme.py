"""ORACLE design system: colours and the global CSS for the Streamlit dashboard."""
import streamlit as st

BG = "#080D1B"
SIDEBAR = "#0D1426"
CARD = "#131E33"
BORDER = "#253451"
PRIMARY = "#8B5CF6"
SECONDARY = "#38BDF8"
TEXT = "#F1F5F9"
MUTED = "#94A3B8"

PRIORITY_COLORS = {
    "Critical": "#EF4444",
    "High": "#F97316",
    "Medium": "#EAB308",
    "Low": "#22C55E",
}
SENTIMENT_COLORS = {"positive": "#22C55E", "negative": "#EF4444", "neutral": "#64748B"}
STATE_COLORS = {"ok": "#22C55E", "warn": "#EAB308", "bad": "#EF4444", "neutral": "#64748B"}

_ROOT = (
    f":root{{--bg:{BG};--sidebar:{SIDEBAR};--card:{CARD};--border:{BORDER};"
    f"--primary:{PRIMARY};--secondary:{SECONDARY};--text:{TEXT};--muted:{MUTED};}}"
)

_CSS = """
.stApp{background:radial-gradient(900px 500px at 90% -10%,rgba(139,92,246,.20),transparent 60%),
radial-gradient(800px 480px at -5% 0%,rgba(56,189,248,.12),transparent 55%),var(--bg);
color:var(--text);}
[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:2rem;max-width:1400px;}
[data-testid="stSidebar"]{background:var(--sidebar);border-right:1px solid var(--border);}
[data-testid="stSidebarNavLink"]{border-radius:10px;margin:2px 0;transition:all .2s ease;}
[data-testid="stSidebarNavLink"]:hover{background:rgba(139,92,246,.15);transform:translateX(2px);}
[data-testid="stSidebarNavLink"][aria-current="page"]{
background:linear-gradient(90deg,rgba(139,92,246,.35),rgba(56,189,248,.15));
border:1px solid rgba(139,92,246,.5);}
h1,h2,h3{letter-spacing:-.02em;color:var(--text);}
p,label,li,span{color:inherit;}
.stButton>button,.stDownloadButton>button,[data-testid="stLinkButton"] a,
[data-testid="stFormSubmitButton"]>button{
background:linear-gradient(135deg,var(--primary),#6D5BF0 55%,var(--secondary));
color:#fff!important;border:0;border-radius:10px;font-weight:600;
transition:transform .15s ease,box-shadow .15s ease;}
.stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stLinkButton"] a:hover,
[data-testid="stFormSubmitButton"]>button:hover{transform:translateY(-1px);
box-shadow:0 6px 18px rgba(139,92,246,.45);color:#fff!important;}
[data-testid="stSidebar"] .stButton>button{width:100%;}
[data-baseweb="input"]>div,[data-baseweb="select"]>div,[data-baseweb="textarea"]>div{
background:#0F1830!important;border:1px solid var(--border)!important;border-radius:10px!important;}
input,textarea{color:var(--text)!important;}
[data-baseweb="tab"][aria-selected="true"]{color:var(--secondary);}
[data-testid="stChatMessage"]{background:rgba(19,30,51,.7);border:1px solid var(--border);
border-radius:14px;}
[class*="st-key-card"]{background:rgba(19,30,51,.78);border:1px solid var(--border);
border-radius:14px;backdrop-filter:blur(10px);padding:.5rem .8rem;margin-bottom:.6rem;
transition:border-color .2s ease,transform .2s ease;}
[class*="st-key-card"]:hover{border-color:rgba(139,92,246,.7);transform:translateY(-1px);}
.page-title{font-size:30px;font-weight:800;line-height:1.2;
background:linear-gradient(90deg,#fff,#C4B5FD 50%,#7DD3FC);-webkit-background-clip:text;
background-clip:text;color:transparent;}
.page-sub{color:var(--muted);margin-bottom:1rem;}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;
margin:.5rem 0 1.2rem;}
.kpi{background:rgba(19,30,51,.8);border:1px solid var(--border);border-radius:14px;
border-top:3px solid var(--accent);padding:16px 18px;transition:transform .2s ease;}
.kpi:hover{transform:translateY(-2px);}
.kpi .label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em;}
.kpi .value{font-size:30px;font-weight:700;color:var(--text);}
.kpi .sub{color:var(--muted);font-size:12px;}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;
font-weight:600;color:#fff;margin:0 4px 4px 0;}
.story-title{font-size:18px;font-weight:600;margin:6px 0;color:var(--text);}
.status-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;}
.status{background:rgba(19,30,51,.8);border:1px solid var(--border);border-radius:12px;
padding:12px 14px;}
.status .s-label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em;}
.status .s-value{font-weight:600;color:var(--text);margin-top:4px;}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:8px;
background:var(--c);box-shadow:0 0 8px var(--c);}
.empty{border:1px dashed var(--border);border-radius:14px;padding:28px;text-align:center;
color:var(--muted);margin:.5rem 0 1rem;}
.empty b{color:var(--text);display:block;margin-bottom:4px;}
.row-item{display:flex;gap:10px;align-items:center;padding:8px 10px;
border-bottom:1px solid var(--border);}
.row-item .row-title{flex:1;color:var(--text);}
.row-item .row-time{color:var(--muted);font-size:12px;white-space:nowrap;}
@media (max-width:768px){
.block-container{padding:1rem .8rem;}
.page-title{font-size:24px;}
.kpi .value{font-size:24px;}
.row-item{flex-wrap:wrap;}
}
"""


def apply() -> None:
    st.markdown(f"<style>{_ROOT}{_CSS}</style>", unsafe_allow_html=True)