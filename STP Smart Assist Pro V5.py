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
# ENGINE
# =========================================================
def calculate_svi(sv30, mlss):
    return (sv30 * 1000) / mlss if mlss > 0 else 0

def calculate_srt(mlss, volume, was_flow, was_mlss):
    return (mlss * volume) / (was_flow * was_mlss) if was_flow > 0 and was_mlss > 0 else 0

def calculate_fm(flow, bod, mlss, volume):
    return (flow * bod) / (mlss * volume) if mlss > 0 and volume > 0 else 0

# =========================================================
# DIAGNOSIS ENGINE
# =========================================================
def diagnose_process(do, mlss, nh3, svi, srt, fm):

    issues = []
    actions = []

    if mlss < 500 or srt < 3:
        return {
            "status": "🔴 Critical",
            "process": "Biomass Washout",
            "issues": ["Low MLSS / SRT"],
            "actions": ["Stop wasting sludge", "Increase SRT"],
            "confidence": "HIGH"
        }

    status = "🟢 Normal"
    process = "Stable Operation"

    if do < 2:
        status = "🔴 Critical"
        issues.append("Low DO")
        actions.append("Increase aeration")

    if nh3 > 10:
        status = "🔴 Critical"
        issues.append("High NH3")
        actions.append("Increase aeration + SRT")

    if svi > 150:
        issues.append("Bulking Risk")
        actions.append("Check sludge condition")

    if not issues:
        issues = ["System Stable"]
        actions = ["Maintain operation"]

    return {
        "status": status,
        "process": process,
        "issues": issues,
        "actions": actions,
        "confidence": "MEDIUM"
    }

# =========================================================
# SCORE
# =========================================================
def stability_score(svi, mlss, do, srt, fm):
    score = 100
    if mlss < 1500: score -= 20
    if svi > 150: score -= 20
    if do < 2: score -= 20
    if srt < 3: score -= 30
    if fm < 0.1 or fm > 0.5: score -= 10
    return max(0, min(100, score))

# =========================================================
# PDF GENERATOR (FIXED)
# =========================================================
def generate_pdf(data, result, score):
    filename = "STP_Report.pdf"
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("🌊 STP SMART ASSIST PRO REPORT", styles["Title"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"Status: {result['status']}", styles["Heading2"]))
    content.append(Paragraph(f"Process: {result['process']}", styles["Normal"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("Issues:", styles["Heading2"]))
    content.append(Paragraph(", ".join(result["issues"]), styles["Normal"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("Actions:", styles["Heading2"]))
    content.append(Paragraph(", ".join(result["actions"]), styles["Normal"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Score: {score}/100", styles["Heading2"]))
    content.append(Spacer(1, 10))

    doc.build(content)
    return filename

# =========================================================
# SESSION
# =========================================================
if "user" not in st.session_state:
    st.session_state["user"] = None

# =========================================================
# UI
# =========================================================
st.title("🌊 STP Smart Assist Pro")

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
    rp = st.text_input("Password", key="rp", type="password")
    rn = st.text_input("Name")

    if st.button("Register"):
        if create_user(ru, rp, rn):
            st.success("Account created")
        else:
            st.error("User exists")

user = st.session_state.get("user")
if not user:
    st.stop()

st.header(f"Welcome {user['name']}")

# =========================================================
# INPUTS
# =========================================================
st.subheader("Process Inputs")

sv30 = st.number_input("SV30", 250.0)
mlss = st.number_input("MLSS", 3000.0)
do = st.number_input("DO", 2.0)
nh3 = st.number_input("NH3", 5.0)

volume = st.number_input("Volume", 500.0)
was_flow = st.number_input("WAS Flow", 50.0)
was_mlss = st.number_input("WAS MLSS", 8000.0)

flow = st.number_input("Flow", 1000.0)
bod = st.number_input("BOD", 250.0)

# =========================================================
# CALC
# =========================================================
svi = calculate_svi(sv30, mlss)
srt = calculate_srt(mlss, volume, was_flow, was_mlss)
fm = calculate_fm(flow, bod, mlss, volume)

result = diagnose_process(do, mlss, nh3, svi, srt, fm)
score = stability_score(svi, mlss, do, srt, fm)

# =========================================================
# OUTPUT
# =========================================================
st.subheader("Diagnosis")
st.json(result)

st.metric("Score", score)

# =========================================================
# PDF BUTTON (FIXED SAFE)
# =========================================================
st.subheader("Report")

if st.button("Generate PDF"):
    file_path = generate_pdf(
        {
            "SVI": svi,
            "SRT": srt,
            "FM": fm
        },
        result,
        score
    )

    with open(file_path, "rb") as f:
        st.download_button(
            "Download PDF",
            f,
            file_name="STP_Report.pdf",
            mime="application/pdf"
        )