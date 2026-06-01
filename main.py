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
# 1. قواميس النموذج الأساسي (بدون سكر تراكمي)
# ==========================================================
COEFS_FEMALE_BASE = {
    "age": 0.719883, "non_hdl": 0.1176967, "hdl": -0.151185, "sbp_low": -0.0835358, "sbp_high": 0.3592852,
    "diabetes": 0.8348585, "smoker": 0.4831078, "egfr_low": 0.4864619, "egfr_high": 0.0397779,
    "bp_med": 0.2265309, "statin": -0.0592374, "treated_sbp_high": -0.0395762, "treated_non_hdl": 0.0844423,
    "age_non_hdl": -0.0567839, "age_hdl": 0.0325692, "age_sbp_high": -0.1035985, "age_diabetes": -0.2417542,
    "age_smoker": -0.0791142, "age_egfr_low": -0.1671492, "constant": -3.819975
}

COEFS_MALE_BASE = {
    "age": 0.7099847, "non_hdl": 0.1658663, "hdl": -0.1144285, "sbp_low": -0.2837212, "sbp_high": 0.3239977,
    "diabetes": 0.7189597, "smoker": 0.3956973, "egfr_low": 0.3690075, "egfr_high": 0.0203619,
    "bp_med": 0.2036522, "statin": -0.0865581, "treated_sbp_high": -0.0322916, "treated_non_hdl": 0.114563,
    "age_non_hdl": -0.0300005, "age_hdl": 0.0232747, "age_sbp_high": -0.0927024, "age_diabetes": -0.2018525,
    "age_smoker": -0.0970527, "age_egfr_low": -0.1217081, "constant": -3.500655
}

# ==========================================================
# 2. قواميس نموذج السكر التراكمي (Enhanced HbA1c Model)
# ==========================================================
COEFS_FEMALE_HBA1C = {
    "age": 0.7111831, "non_hdl": 0.106797, "hdl": -0.1425745, "sbp_low": -0.0736824, "sbp_high": 0.3480844,
    "diabetes": 0.5112951, "smoker": 0.4880292, "egfr_low": 0.4754997, "egfr_high": 0.0438132,
    "bp_med": 0.2259093, "statin": -0.0648872, "treated_sbp_high": -0.0437645, "treated_non_hdl": 0.0697082,
    "age_non_hdl": -0.0506382, "age_hdl": 0.0327475, "age_sbp_high": -0.0996442, "age_diabetes": -0.1924338,
    "age_smoker": -0.0803539, "age_egfr_low": -0.1682586, "hba1c_dm": 0.1339055, "hba1c_no_dm": 0.1596461,
    "constant": -3.838746
}

COEFS_MALE_HBA1C = {
    "age": 0.7064146, "non_hdl": 0.1532267, "hdl": -0.1082166, "sbp_low": -0.2675288, "sbp_high": 0.3173809,
    "diabetes": 0.432604, "smoker": 0.3958842, "egfr_low": 0.3665014, "egfr_high": 0.0250243,
    "bp_med": 0.2061158, "statin": -0.0899988, "treated_sbp_high": -0.0334959, "treated_non_hdl": 0.1034168,
    "age_non_hdl": -0.0255406, "age_hdl": 0.0247538, "age_sbp_high": -0.0917441, "age_diabetes": -0.1499195,
    "age_smoker": -0.098089, "age_egfr_low": -0.1305231, "hba1c_dm": 0.1157161, "hba1c_no_dm": 0.1288303,
    "constant": -3.51835
}

def compute_prevent_ascvd(data: PatientData) -> float:
    # تحديد ما إذا كان التطبيق سيستخدم نموذج التراكمي أم النموذج الأساسي
    use_hba1c_model = data.hba1c is not None
    
    if data.sex.lower() == "female":
        coefs = COEFS_FEMALE_HBA1C if use_hba1c_model else COEFS_FEMALE_BASE
    else:
        coefs = COEFS_MALE_HBA1C if use_hba1c_model else COEFS_MALE_BASE
    
    # التمركز والتحويلات
    age_c = (data.age - 55.0) / 10.0
    tc_mmol = data.total_chol * 0.02586
    hdl_mmol = data.hdl * 0.02586
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
    
    # حساب اللوغاريتم الأرجحي بناءً على القاموس المختار
    log_odds = coefs["constant"]
    log_odds += coefs["age"] * age_c
    log_odds += coefs["non_hdl"] * non_hdl_c
    log_odds += coefs["hdl"] * hdl_c_main
    log_odds += coefs["sbp_low"] * sbp_low
    log_odds += coefs["sbp_high"] * sbp_high
    log_odds += coefs["diabetes"] * is_dm
    log_odds += coefs["smoker"] * is_smoker
    log_odds += coefs["egfr_low"] * egfr_low
    log_odds += coefs["egfr_high"] * egfr_high
    log_odds += coefs["bp_med"] * is_bp_med
    log_odds += coefs["statin"] * is_statin
    
    log_odds += coefs["treated_sbp_high"] * (is_bp_med * sbp_high)
    log_odds += coefs["treated_non_hdl"] * (is_statin * non_hdl_c)
    log_odds += coefs["age_non_hdl"] * (age_c * non_hdl_c)
    log_odds += coefs["age_hdl"] * (age_c * hdl_c_inter)
    log_odds += coefs["age_sbp_high"] * (age_c * sbp_high)
    log_odds += coefs["age_diabetes"] * (age_c * is_dm)
    log_odds += coefs["age_smoker"] * (age_c * is_smoker)
    log_odds += coefs["age_egfr_low"] * (age_c * egfr_low)

    # حساب إضافي خاص فقط إذا توفر السكر التراكمي
    if use_hba1c_model:
        hba1c_c = data.hba1c - 5.5
        if data.diabetes:
            log_odds += coefs["hba1c_dm"] * hba1c_c
        else:
            log_odds += coefs["hba1c_no_dm"] * hba1c_c
            
    risk = 1.0 / (1.0 + math.exp(-log_odds))
    return round(risk * 100, 2)

@app.post("/calculate_prevent")
def calculate_risk(patient: PatientData):
    try:
        if not (30 <= patient.age <= 79):
            raise HTTPException(status_code=400, detail="العمر غير مدعوم")
        risk = compute_prevent_ascvd(patient)
        return {"prevent_10yr_risk_percent": risk}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
