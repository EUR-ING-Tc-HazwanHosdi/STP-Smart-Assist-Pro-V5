import streamlit as st
import numpy as np
import cv2
from PIL import Image
import json
import os
import hashlib
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# =========================================================
# CONFIG
# =========================================================
st.set_page_config("STP Smart Assist Pro", layout="wide")

USER_DB_FILE = "users.json"

# =========================================================
# USER SYSTEM
# =========================================================
def load_users():
    if not os.path.exists(USER_DB_FILE):
        return {}
    with open(USER_DB_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USER_DB_FILE, "w") as f:
        json.dump(users, f)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user(username):
    return load_users().get(username)

def create_user(username, password, name):
    users = load_users()
    if username in users:
        return False

    users[username] = {
        "username": username,
        "password": hash_password(password),
        "name": name
    }

    save_users(users)
    return True

def authenticate(username, password):
    user = get_user(username)
    return user and user["password"] == hash_password(password)

# =========================================================
# SESSION
# =========================================================
if "user" not in st.session_state:
    st.session_state["user"] = None

# =========================================================
# ENGINE CALCULATIONS
# =========================================================
def calculate_svi(sv30, mlss):
    if mlss <= 0:
        return 0
    return (sv30 * 1000) / mlss


def calculate_srt(mlss, volume, was_flow, was_mlss):
    if was_flow == 0 or was_mlss == 0:
        return 0
    return (mlss * volume) / (was_flow * was_mlss)


def calculate_fm(flow, bod, mlss, volume):
    if mlss == 0 or volume == 0:
        return 0
    return (flow * bod) / (mlss * volume)

# =========================================================
# DIAGNOSIS ENGINE (CONSULTANT LOGIC)
# =========================================================
def diagnose_process(do, mlss, nh3, svi, srt, fm):

    issues = []
    actions = []
    severity = "🟢 Normal"
    process = "Stable Operation"

    # =========================================
    # 1. WASHOUT (TOP PRIORITY)
    # =========================================
    if mlss < 500 or srt < 3:
        severity = "🔴 Critical"
        process = "Biomass Washout"

        issues.append("Extremely Low Biomass / SRT")
        actions += [
            "Reduce sludge wasting immediately",
            "Increase SRT to 5–10 days",
            "Check influent loading"
        ]
        return severity, process, issues, actions

    # =========================================
    # PROCESS CONDITION LOGIC (FIXED)
    # =========================================
    if do < 2 and nh3 > 10:
        process = "Oxygen-Limited Nitrification Failure"

    elif do < 2:
        process = "Oxygen Limitation"

    elif nh3 > 10:
        process = "Nitrification Failure"

    elif fm < 0.1:
        process = "Underloaded System"

    elif fm > 0.5:
        process = "Overloaded System"

    elif svi > 150:
        process = "Settling Issue (Bulking Risk)"

    # =========================================
    # ISSUES & ACTIONS
    # =========================================
    if do < 2:
        severity = "🔴 Critical"
        issues.append("Low Dissolved Oxygen")
        actions.append("Increase aeration (2–3 mg/L)")

    if nh3 > 10:
        severity = "🔴 Critical"
        issues.append("High Ammonia")
        actions.append("Increase aeration + SRT")

    if svi > 150:
        issues.append("Poor Settling (High SVI)")
        actions.append("Check sludge condition / F/M ratio")

    if not issues:
        issues.append("System Operating Normally")
        actions.append("Maintain operation")

    return severity, process, issues, actions

# =========================================================
# STABILITY SCORE
# =========================================================
def stability_score(svi, mlss, do, srt, fm):
    score = 100

    if mlss < 1500: score -= 20
    if mlss > 5000: score -= 10
    if svi > 150: score -= 20
    if do < 2: score -= 20
    if srt < 3:
     score -= 30
    elif 3 <= srt < 5:
     score -= 10   # <-- ADD THIS (critical)
    elif srt > 20:
     score -= 10
    if fm < 0.1 or fm > 0.5: score -= 15

    return max(0, min(100, score))

# =========================================================
# IMAGE ANALYSIS
# =========================================================
def extract_features(img):
    image = np.array(img)
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    return {
        "foam": np.mean(gray > 200),
        "dark": np.mean(gray < 60),
        "texture": cv2.Laplacian(gray, cv2.CV_64F).var()
    }

def diagnose_image(features):
    if features["dark"] > 0.4:
        return "Anaerobic Condition", "Increase aeration"

    if features["foam"] > 0.15:
        return "Foaming", "Check FOG loading"

    if features["texture"] < 40:
        return "Low Activity", "Check MLSS"

    return "Normal", "Maintain operation"

# =========================================================
# UI
# =========================================================
st.title("🌊 STP Smart Assist Pro")
st.success("🟢 Consultant Mode Enabled")

# LOGIN
tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if authenticate(u, p):
            st.session_state["user"] = get_user(u)
            st.rerun()
        else:
            st.error("Invalid credentials")

with tab2:
    ru = st.text_input("Username", key="ru")
    rp = st.text_input("Password", type="password", key="rp")
    rn = st.text_input("Name")

    if st.button("Register"):
        if create_user(ru, rp, rn):
            st.success("Account created")
        else:
            st.error("User exists")

user = st.session_state.get("user")
if not user:
    st.stop()

st.header(f"Welcome {user.get('name')}")

if st.button("Logout"):
    st.session_state.clear()
    st.rerun()

# =========================================================
# INPUTS
# =========================================================
st.subheader("📊 Process Inputs")

sv30 = st.number_input("SV30 (mL/L)", value=250.0)
mlss = st.number_input("MLSS (mg/L)", value=3000.0)
do = st.number_input("DO (mg/L)", value=2.0)
nh3 = st.number_input("NH3 (mg/L)", value=5.0)

volume = st.number_input("Tank Volume (m3)", value=500.0)
was_flow = st.number_input("WAS Flow (m3/day)", value=50.0)
was_mlss = st.number_input("WAS MLSS (mg/L)", value=8000.0)

flow = st.number_input("Influent Flow (m3/day)", value=1000.0)
bod = st.number_input("Influent BOD (mg/L)", value=250.0)

# VALIDATION
if mlss < 200:
    st.error("⚠️ MLSS too low — unreliable")

# =========================================================
# CALCULATIONS
# =========================================================

svi = calculate_svi(sv30, mlss)
srt = calculate_srt(mlss, volume, was_flow, was_mlss)
fm = calculate_fm(flow, bod, mlss, volume)

data = {
    "SV30": sv30,
    "MLSS": mlss,
    "DO": do,
    "NH3": nh3,
    "Volume": volume,
    "WAS Flow": was_flow,
    "WAS MLSS": was_mlss,
    "Flow": flow,
    "BOD": bod,
    "SVI": round(svi, 2),
    "SRT": round(srt, 2),
    "F/M": round(fm, 3)
}

# =========================================================
# DIAGNOSIS
# =========================================================
st.subheader("🧠 Engineering Diagnosis")

severity, process, issues, actions = diagnose_process(do, mlss, nh3, svi, srt, fm)

result = (severity, process, issues, actions)

st.markdown(f"### Status: {severity}")
st.write(f"**Process Condition:** {process}")

st.write("### Issues")
for i in issues:
    st.write("•", i)

st.write("### Actions")
for a in actions:
    st.write("•", a)

# =========================================================
# METRICS
# =========================================================
st.subheader("📈 Key Parameters")

col1, col2, col3 = st.columns(3)
col1.metric("SVI", round(svi, 2))
col2.metric("SRT (days)", round(srt, 2))
col3.metric("F/M Ratio", round(fm, 3))

# =========================================================
# SCORE
# =========================================================
st.subheader("🔬 Stability Score")

score = stability_score(svi, mlss, do, srt, fm)
st.metric("Score", score)
st.subheader("📄 Engineering Report")

def generate_pdf(data, result, score, filename="STP_Report.pdf"):
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    content = []

if st.button("Generate PDF Report"):
    file_path = generate_pdf(data, result, score)

if file_path and os.path.exists(file_path):
    with open(file_path, "rb") as f:
        st.download_button(
            "Download STP Report",
            f,
            file_name="STP_Report.pdf",
            mime="application/pdf"
        )
else:
    st.error("PDF generation failed. Please try again.")
        st.download_button(
            "Download STP Report",
            f,
            file_name="STP_Report.pdf",
            mime="application/pdf"
        )
# =========================================================
# IMAGE ANALYSIS
# =========================================================
st.subheader("📷 Image Analysis")

img = st.file_uploader("Upload tank image", type=["jpg", "png"])

if img:
    image = Image.open(img)
    features = extract_features(image)
    diag, act = diagnose_image(features)

    st.image(image)
    st.write("Diagnosis:", diag)
    st.write("Action:", act)

def generate_pdf(data, result, score, filename=None):
    import os

    if filename is None:
        filename = f"/tmp/STP_Report.pdf"

    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    content = []

    def section(title, value):
        if isinstance(value, list):
            value = "\n".join([f"- {v}" for v in value])

        content.append(Paragraph(f"<b>{title}</b>", styles["Heading2"]))
        content.append(Paragraph(str(value), styles["Normal"]))
        content.append(Spacer(1, 10))

    content.append(Paragraph(
        "🌊 STP SMART ASSIST PRO - ENGINEERING REPORT",
        styles["Title"]
    ))
    content.append(Spacer(1, 15))

    section("PROCESS INPUTS", data)
    section("STATUS", result["status"])
    section("PROCESS CONDITION", result["process"])
    section("ISSUES", result["issues"])
    section("ACTIONS", result["actions"])
    section("STABILITY SCORE", f"{score}/100")

    doc.build(content)

    # IMPORTANT CHECK
    if not os.path.exists(filename):
        raise FileNotFoundError("PDF generation failed")

    return filename
