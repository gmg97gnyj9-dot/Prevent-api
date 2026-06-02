from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
import math

app = FastAPI(title="PREVENT Risk Calculator API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class PatientData(BaseModel):
    age: float
    sex: str
    sbp: float
    total_chol: float
    hdl: float
    egfr: float
    bmi: float
    diabetes: bool
    smoker: bool
    bp_med: bool
    statin: bool
    hba1c: Optional[float] = None

# ==========================================================
# 1. معاملات النموذج الأساسي (Total CVD - Base Model)
# ==========================================================
COEFS_BASE = {
    "female": {
        "const": -3.307728, "age": 0.7939329, "non_hdl": 0.0305239, "hdl": -0.1606857,
        "sbp_low": -0.2394003, "sbp_high": 0.3600781, "dm": 0.8667604, "smoker": 0.5360739,
        "egfr_low": 0.6045917, "egfr_high": 0.0433769, "bp_med": 0.3151672, "statin": -0.1477655,
        "treated_sbp_high": -0.0663612, "treated_non_hdl": 0.1197879, "age_non_hdl": -0.0819715,
        "age_hdl": 0.0306769, "age_sbp_high": -0.0946348, "age_dm": -0.27057, "age_smoker": -0.078715,
        "age_egfr_low": -0.1637806
    },
    "male": {
        "const": -3.031168, "age": 0.7688528, "non_hdl": 0.0736174, "hdl": -0.0954431,
        "sbp_low": -0.4347345, "sbp_high": 0.3362658, "dm": 0.7692857, "smoker": 0.4386871,
        "egfr_low": 0.5378979, "egfr_high": 0.0164827, "bp_med": 0.288879, "statin": -0.1337349,
        "treated_sbp_high": -0.0475924, "treated_non_hdl": 0.150273, "age_non_hdl": -0.0517874,
        "age_hdl": 0.0191169, "age_sbp_high": -0.1049477, "age_dm": -0.2251948, "age_smoker": -0.0895067,
        "age_egfr_low": -0.1543702
    }
}

# ==========================================================
# 2. معاملات نموذج التراكمي (Total CVD - HbA1c Model)
# ==========================================================
COEFS_HBA1C = {
    "female": {
        "const": -3.306162, "age": 0.7858178, "non_hdl": 0.0194438, "hdl": -0.1521964,
        "sbp_low": -0.2296681, "sbp_high": 0.3465777, "dm": 0.5366241, "smoker": 0.5411682,
        "egfr_low": 0.5931898, "egfr_high": 0.0472458, "bp_med": 0.3158567, "statin": -0.1535174,
        "treated_sbp_high": -0.0687752, "treated_non_hdl": 0.1054746, "age_non_hdl": -0.0761119,
        "age_hdl": 0.0307469, "age_sbp_high": -0.0905966, "age_dm": -0.2241857, "age_smoker": -0.080186,
        "age_egfr_low": -0.1667286, "hba1c_dm": 0.1338348, "hba1c_no_dm": 0.1622409
    },
    "male": {
        "const": -3.040901, "age": 0.7699177, "non_hdl": 0.0605093, "hdl": -0.0888525,
        "sbp_low": -0.417713, "sbp_high": 0.3288657, "dm": 0.4759471, "smoker": 0.4385663,
        "egfr_low": 0.5334616, "egfr_high": 0.0206431, "bp_med": 0.2917524, "statin": -0.1383313,
        "treated_sbp_high": -0.0482622, "treated_non_hdl": 0.1393796, "age_non_hdl": -0.0463501,
        "age_hdl": 0.0205926, "age_sbp_high": -0.1037717, "age_dm": -0.1737697, "age_smoker": -0.0915839,
        "age_egfr_low": -0.1637039, "hba1c_dm": 0.13159, "hba1c_no_dm": 0.1295185
    }
}

def compute_prevent_risk(data: PatientData) -> float:
    # تحديد النموذج بناءً على توفر التراكمي
    use_hba1c = data.hba1c is not None
    gender = "female" if data.sex.lower() == "female" else "male"
    c = COEFS_HBA1C[gender] if use_hba1c else COEFS_BASE[gender]

    # الحل الجذري لمشكلة الـ 0% (التعامل الذكي مع الوحدات)
    # الواجهة لديك ترسل البيانات بـ mg/dL دائماً، لذلك نعيدها إلى mmol/L إذا كانت قيمتها عالية
    tc_mmol = data.total_chol * 0.02586 if data.total_chol > 30 else data.total_chol
    hdl_mmol = data.hdl * 0.02586 if data.hdl > 10 else data.hdl
    
    age_c = (data.age - 55.0) / 10.0
    non_hdl_c = (tc_mmol - hdl_mmol) - 3.5
    hdl_c_main = (hdl_mmol - 1.3) / 0.3
    hdl_c_inter = (hdl_mmol - 1.3) / 1.0  
    
    sbp_low = (min(data.sbp, 110.0) - 110.0) / 20.0
    sbp_high = (max(data.sbp, 110.0) - 130.0) / 20.0
    
    egfr_low = (min(data.egfr, 60.0) - 60.0) / -15.0
    egfr_high = (max(data.egfr, 60.0) - 90.0) / -15.0
    
    is_dm = 1 if data.diabetes else 0
    is_smoker = 1 if data.smoker else 0
    is_bp_med = 1 if data.bp_med else 0
    is_statin = 1 if data.statin else 0
    
    # بناء اللوغاريتم الأرجحي
    log_odds = c["const"] + \
               (c["age"] * age_c) + \
               (c["non_hdl"] * non_hdl_c) + \
               (c["hdl"] * hdl_c_main) + \
               (c["sbp_low"] * sbp_low) + \
               (c["sbp_high"] * sbp_high) + \
               (c["dm"] * is_dm) + \
               (c["smoker"] * is_smoker) + \
               (c["egfr_low"] * egfr_low) + \
               (c["egfr_high"] * egfr_high) + \
               (c["bp_med"] * is_bp_med) + \
               (c["statin"] * is_statin) + \
               (c["treated_sbp_high"] * is_bp_med * sbp_high) + \
               (c["treated_non_hdl"] * is_statin * non_hdl_c) + \
               (c["age_non_hdl"] * age_c * non_hdl_c) + \
               (c["age_hdl"] * age_c * hdl_c_inter) + \
               (c["age_sbp_high"] * age_c * sbp_high) + \
               (c["age_dm"] * age_c * is_dm) + \
               (c["age_smoker"] * age_c * is_smoker) + \
               (c["age_egfr_low"] * age_c * egfr_low)

    # حساب التراكمي في حال توفره (متمركز عند 5.3)
    if use_hba1c:
        hba1c_c = data.hba1c - 5.3
        if is_dm:
            log_odds += c["hba1c_dm"] * hba1c_c
        else:
            log_odds += c["hba1c_no_dm"] * hba1c_c

    risk = 1.0 / (1.0 + math.exp(-log_odds))
    return round(risk * 100, 2)

@app.post("/calculate_prevent")
def calculate_risk(patient: PatientData):
    try:
        if not (30 <= patient.age <= 79):
            raise HTTPException(status_code=400, detail="العمر غير مدعوم")
        risk = compute_prevent_risk(patient)
        return {"prevent_10yr_risk_percent": risk}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
