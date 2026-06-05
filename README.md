# 🏭 STP SMART ASSIST PRO (V.5.0)

[![Streamlit App](https://static.streamlit.io/badge_svg.svg)](https://stpsmartassistv2-knrc5e5tspwnqpauk2ieqe.streamlit.app)

An enterprise-grade Human-Machine Interface (HMI) Core Terminal designed to serve as a predictive "Digital Twin" for Sewage Treatment Plants (STPs). This decision support framework ingests biological and structural telemetry ($SV_{30}$, $MLSS$, $DO$) and translates real-time kinetic calculations into actionable process control automation protocols aligned with global wastewater guidelines and mass balance equations.

---

## 🚀 Live HMI Dashboard
Experience the application running live on Streamlit Cloud:  
👉 [STP Smart Assist Pro Core Terminal](https://stpsmartassistv2-knrc5e5tspwnqpauk2ieqe.streamlit.app)

---

## ✨ Key Architectural Features

* **📡 Telemetry Ingestion Desk:** A centralized register interface collecting live operational variables including Sludge Volume ($SV_{30}$), Mixed Liquor Suspended Solids ($MLSS$), Dissolved Oxygen ($DO$), Ammonia Nitrogen ($NH_3$), and volumetric flow tracking.
* **🧠 AIMeCHA Process Insight Engine:** Evaluates mathematical kinetic variables against targeted plant baselines to catch organic overloading or biomass washout events before effluent quality drops.
* **📈 Dynamic Plant Health Score:** Computes a real-time health rating (0-100%). It applies automated penalty deductions for critical failure vectors such as oxygen depletion, nitrification shocks, and filament dominance.
* **⚙️ Control Automation Protocol:** Serves as an expert system that interprets multi-variable anomalies to output immediate operational directives for operators (e.g., dynamic blower tuning or sludge wasting mitigation).
* **🎓 Role-Based Training Layer:** Embeds a responsive "What-If Matrix Calibration" component. The interface dynamically escalates features based on user authorization (Operator, Technician, or Engineer), revealing deep process metrics like $SVI$ and $F/M$ ratios to high-level engineers.
* **💾 Local Event Logging:** Features an automated background write-to-disk process (`plant_log.json`) to retain real-time logs of sensor outputs and calculate health values for historical compliance review.

---

## 🔬 Core Wastewater Process Engineering Equations

The system operates a continuous back-end calculation framework using fundamental biological treatment mechanics:

### 1. Sludge Volume Index ($SVI$)
Determines the settling and compaction characteristics of the activated sludge biomass:
$$SVI = \frac{SV_{30} \times 1000}{MLSS} \quad [mL/g]$$

### 2. Sludge Retention Time ($SRT$ / Sludge Age)
Calculates the mean cell residence time of biological solids within the system boundary:
$$SRT = \frac{MLSS \times V_{reactor}}{Q_{WAS} \times MLSS_{WAS}} \quad [Days]$$

### 3. Food-to-Microorganism Ratio ($F/M$)
Quantifies the organic loading rate applied to the biological population:
$$F/M = \frac{Q_{Influent} \times BOD}{MLSS \times V_{reactor}} \quad [kg \ BOD \ / \ kg \ MLSS \cdot d]$$

---

## 🛠️ Tech Stack & Dependencies

* **Core Language:** Python 3.x
* **HMI Dashboard Framework:** Streamlit (Custom Advanced Commercial Dark Theme CSS)
* **Mathematical Vectorization:** NumPy
* **Data Pipelines & Manipulation:** Pandas
* **Persistence Layer:** JSON-based local append logging

---

## 📈 Process Configuration Matrices

The platform dynamically adjusts its evaluation thresholds based on the kinetics of the specific biological system chosen:

| Plant Architecture | Target F/M Range ($kg/kg\cdot d$) | Minimum Target SRT ($Days$) |
| :--- | :--- | :--- |
| **Extended Aeration** | 0.05 - 0.30 | 8 |
| **Sequencing Batch Reactor (SBR)** | 0.08 - 0.40 | 10 |
| **Moving Bed Biofilm Reactor (MBBR)** | 0.10 - 0.50 | 5 |
| **Oxidation Ditch** | 0.05 - 0.25 | 12 |

---

## 💻 Local Installation & Deployment

To clone, set up, and run this HMI terminal locally, execute the following commands in your environment:

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/EUR-ING-Tc-HazwanHosdi/STPsmartassistV2.git](https://github.com/EUR-ING-Tc-HazwanHosdi/STPsmartassistV2.git)
   cd STPsmartassistV2

2. Install library dependencies:

Bash
pip install -r requirements.txt

3. Launch the application core:
Bash
streamlit run STP_Smart_Assist_Pro_V5.py


📁 Repository Blueprint

Plaintext
├── .gitignore                  # Excludes standard __pycache__ and local environments
├── ChatGPT Image Jun 4...      # System application branding asset
├── LICENSE                     # Repository licensing and utilization terms
├── README.md                   # Comprehensive portfolio and documentation overview
├── STP_Smart_Assist_Pro_V5.py  # Main HMI terminal application core code
├── plant_log.json              # Live system append log for engineering telemetry
└── requirements.txt            # Application package dependencies
