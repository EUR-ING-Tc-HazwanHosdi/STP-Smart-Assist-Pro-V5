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
st.set_page_config("STP Smart Assist Pro - Master", layout="wide")
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
# PLANT CONFIG
# =========================================================
PLANT_CONFIG = {
    "Extended Aeration": {"srt_min": 10, "fm_range": (0.05, 0.15)},
    "Conventional ASP": {"srt_min": 5, "fm_range": (0.2, 0.5)},
    "Package STP": {"srt_min": 8, "fm_range": (0.1, 0.3)}
}

# =========================================================
# PRESETS
# =========================================================
def apply_preset(p):
    return {
        "Residential": {"flow": 800, "bod": 250, "mlss": 3000},
        "Commercial": {"flow": 1200, "bod": 300, "mlss": 3500},
        "Industrial": {"flow": 1500, "bod": 400, "mlss": 4000}
    }.get(p, {})

# =========================================================
# CALCULATIONS
# =========================================================
def calculate_svi(sv30, mlss):
    return (sv30 * 1000) / mlss if mlss else 0

def calculate_srt(mlss, volume, was_flow, was_mlss):
    return (mlss * volume) / (was_flow * was_mlss) if was_flow and was_mlss else 0

def calculate_fm(flow, bod, mlss, volume):
    return (flow * bod) / (mlss * volume) if mlss and volume else 0

# =========================================================
# DECISION ENGINE
# =========================================================
def decision_engine(data, plant_type):
    cfg = PLANT_CONFIG[plant_type]

    do = data["do"]
    mlss = data["mlss"]
    nh3 = data["nh3"]
    svi = data["svi"]
    srt = data["srt"]
    fm = data["fm"]

    result = {
        "status": "🟢 NORMAL",
        "issue": "Stable Operation",
        "root_cause": [],
        "impact": [],
        "actions": [],
        "confidence": "MEDIUM"
    }

    # =====================================================
    # 1. CRITICAL FAILURE (HIGHEST PRIORITY)
    # =====================================================
    if mlss < 500 or srt < 3:
        return {
            "status": "🔴 CRITICAL",
            "issue": "Biomass Washout",
            "root_cause": ["Low MLSS / SRT"],
            "impact": ["Biological process failure"],
            "actions": ["Stop wasting sludge", "Increase SRT immediately"],
            "confidence": "HIGH"
        }

    # =====================================================
    # 2. OXYGEN PROBLEMS
    # =====================================================
    if do < 2:
        result["status"] = "🔴 CRITICAL"
        result["issue"] = "Low DO"
        result["root_cause"].append("Insufficient aeration")
        result["actions"].append("Increase aeration rate")

    # =====================================================
    # 3. AMMONIA FAILURE
    # =====================================================
    if nh3 > 10:
        result["status"] = "🔴 CRITICAL"
        result["issue"] = "Nitrification Failure"
        result["root_cause"].append("Low DO or SRT")
        result["actions"].append("Increase SRT + aeration")

    # =====================================================
    # 4. SETTLING PROBLEMS
    # =====================================================
    if svi > 150:
        result["status"] = "🟠 WARNING"
        result["issue"] = "Bulking Risk"
        result["root_cause"].append("Filamentous bacteria growth")
        result["actions"].append("Check F/M ratio and sludge age")

    # =====================================================
    # 5. LOADING CONDITIONS
    # =====================================================
    fm_low, fm_high = cfg["fm_range"]

    if fm < fm_low:
        result["status"] = "🟡 WARNING"
        result["issue"] = "Underloading"
        result["root_cause"].append("Low organic loading")

    elif fm > fm_high:
        result["status"] = "🟠 WARNING"
        result["issue"] = "Overloading"
        result["root_cause"].append("High organic loading")

    # =====================================================
    # 6. DEFAULT SAFETY FALLBACK
    # =====================================================
    if not result["root_cause"]:
        result["root_cause"] = ["System stable"]

    if not result["actions"]:
        result["actions"] = ["Maintain current operation"]

    return result

# =========================================================
# COMPLIANCE
# =========================================================
def compliance_check(svi, do, nh3, srt):
    c = []
    if do < 2: c.append("DO < 2 mg/L")
    if svi > 150: c.append("SVI high")
    if nh3 > 10: c.append("NH3 high")
    if srt < 5: c.append("SRT low")
    return c or ["Within acceptable range"]

# =========================================================
# PDF
# =========================================================

def generate_pdf(data, result, filename="stp_report.pdf"):
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    content = []

    def add(title, items):
        content.append(Paragraph(f"=== {title} ===", styles["Heading2"]))

        if not items:
            content.append(Paragraph("No data available", styles["Normal"]))
            return

        if isinstance(items, list):
            for i in items:
                content.append(Paragraph(f"• {i}", styles["Normal"]))
        else:
            content.append(Paragraph(str(items), styles["Normal"]))

        content.append(Spacer(1, 12))

    # HEADER
    content.append(Paragraph("🌊 STP SMART ASSIST REPORT", styles["Title"]))
    content.append(Spacer(1, 20))

    # INPUT DATA (FORCE DISPLAY)
    add("INPUT DATA", [f"{k}: {v}" for k, v in data.items()])

    # ENGINE RESULTS (FORCE SAFETY)
    add("STATUS", result.get("status", "N/A"))
    add("ISSUE", result.get("issue", "N/A"))

    add("ROOT CAUSE", result.get("root_cause", ["No root cause detected"]))
    add("IMPACT", result.get("impact", ["No impact detected"]))
    add("ACTIONS", result.get("actions", ["Maintain operation"]))

    add("CONFIDENCE", result.get("confidence", "UNKNOWN"))

    # FINAL SAFETY LINE (VERY IMPORTANT)
    content.append(Spacer(1, 20))
    content.append(Paragraph("END OF REPORT", styles["Normal"]))

    doc.build(content)
    return filename

# =========================================================
# UI
# =========================================================
st.title("🌊 STP Smart Assist Pro - Master")

# LOGIN
tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate(u, p):
            st.session_state["user"] = get_user(u)
            st.rerun()

with tab2:
    ru = st.text_input("Username", key="ru")
    rp = st.text_input("Password", type="password", key="rp")
    rn = st.text_input("Name")
    if st.button("Register"):
        create_user(ru, rp, rn)

if not st.session_state.get("user"):
    st.stop()

# CONFIG
plant_type = st.selectbox("Plant Type", list(PLANT_CONFIG.keys()))
preset = st.selectbox("Preset", ["None", "Residential", "Commercial", "Industrial"])
preset_data = apply_preset(preset)

# INPUT
sv30 = st.number_input("SV30", 250.0)
mlss = st.number_input("MLSS", preset_data.get("mlss", 3000.0))
do = st.number_input("DO", 2.0)
nh3 = st.number_input("NH3", 5.0)

volume = st.number_input("Volume", 500.0)
was_flow = st.number_input("WAS Flow", 50.0)
was_mlss = st.number_input("WAS MLSS", 8000.0)
flow = st.number_input("Flow", preset_data.get("flow", 1000.0))
bod = st.number_input("BOD", preset_data.get("bod", 250.0))

# CALC
svi = calculate_svi(sv30, mlss)
srt = calculate_srt(mlss, volume, was_flow, was_mlss)
fm = calculate_fm(flow, bod, mlss, volume)

data = {"do": do, "mlss": mlss, "nh3": nh3, "svi": svi, "srt": srt, "fm": fm}
result = decision_engine(data, plant_type)

# OUTPUT
st.subheader("Decision")
st.write(result)

# COMPLIANCE
st.subheader("Compliance")
for c in compliance_check(svi, do, nh3, srt):
    st.write("•", c)

# PDF
st.session_state["report_data"] = data.copy()
st.session_state["report_result"] = result.copy()

if st.button("Generate PDF Report"):

    data_safe = st.session_state.get("report_data")
    result_safe = st.session_state.get("report_result")

    st.write("DEBUG DATA:", data_safe)   # TEMP DEBUG (IMPORTANT)

    file_path = generate_pdf(data_safe, result_safe)

    with open(file_path, "rb") as f:
        st.download_button(
            "Download PDF",
            f,
            file_name="STP_Report.pdf",
            mime="application/pdf"
        )
print("DATA RECEIVED:", data)
print("RESULT RECEIVED:", result)
# IMAGE
img = st.file_uploader("Upload Image")
if img:
    st.image(Image.open(img))