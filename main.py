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
# معاملات الخطر الكلي (Total CVD) - النموذج الشامل الكامل (Full Model)
# مأخوذة حرفياً من Table S12.E
# ==========================================================

COEFS_FULL_WOMEN = {
    "constant": -3.860385, "age": 0.7716794, "non_hdl": 0.0062109, "hdl": -0.1547756,
    "sbp_low": -0.1933123, "sbp_high": 0.3071217, "dm": 0.496753, "smoker": 0.466605,
    "egfr_low": 0.4780697, "egfr_high": 0.0529077, "bp_med": 0.3034892, "statin": -0.1556524,
    "treated_sbp_high": -0.0667026, "treated_non_hdl": 0.1061825, "age_non_hdl": -0.0742271,
    "age_hdl": 0.0288245, "age_sbp_high": -0.0875188, "age_dm": -0.2267102, "age_smoker": -0.0676125,
    "age_egfr_low": -0.1493231, "missing_sdi": 0.1804508, "missing_acr": 0.0198413,
    "hba1c_dm": 0.1298513, "hba1c_no_dm": 0.1412555, "missing_hba1c": -0.0031658
}

COEFS_FULL_MEN = {
    "constant": -3.631387, "age": 0.7847578, "non_hdl": 0.0534485, "hdl": -0.0911282,
    "sbp_low": -0.4921973, "sbp_high": 0.2972415, "dm": 0.4527054, "smoker": 0.3726641,
    "egfr_low": 0.3886854, "egfr_high": 0.0081661, "bp_med": 0.2508052, "statin": -0.1538484,
    "treated_sbp_high": -0.0474695, "treated_non_hdl": 0.1415382, "age_non_hdl": -0.0436455,
    "age_hdl": 0.0199549, "age_sbp_high": -0.1022686, "age_dm": -0.1762507, "age_smoker": -0.0715873,
    "age_egfr_low": -0.1428668, "missing_sdi": 0.144759, "missing_acr": 0.1095674,
    "hba1c_dm": 0.1165698, "hba1c_no_dm": 0.1048297, "missing_hba1c": -0.0230072
}

def compute_prevent_total_cvd_full(data: PatientData) -> float:
    coefs = COEFS_FULL_WOMEN if data.sex.lower() == "female" else COEFS_FULL_MEN

    # 1. التمركز (Centering) حسب الجدول
    age_c = (data.age - 55.0) / 10.0
    
    # دعم إدخال الكوليسترول بوحدة mmol/L أو mg/dL
    tc_mmol = data.total_chol * 0.02586 if data.total_chol > 30 else data.total_chol
    hdl_mmol = data.hdl * 0.02586 if data.hdl > 10 else data.hdl
    
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
    
    # 2. حساب اللوغاريتم الأرجحي (Log-Odds) للمتغيرات الأساسية
    log_odds = coefs["constant"]
    log_odds += coefs["age"] * age_c
    log_odds += coefs["non_hdl"] * non_hdl_c
    log_odds += coefs["hdl"] * hdl_c_main
    log_odds += coefs["sbp_low"] * sbp_low
    log_odds += coefs["sbp_high"] * sbp_high
    log_odds += coefs["dm"] * is_dm
    log_odds += coefs["smoker"] * is_smoker
    log_odds += coefs["egfr_low"] * egfr_low
    log_odds += coefs["egfr_high"] * egfr_high
    log_odds += coefs["bp_med"] * is_bp_med
    log_odds += coefs["statin"] * is_statin
    
    # التفاعلات المتقاطعة (Interactions)
    log_odds += coefs["treated_sbp_high"] * (is_bp_med * sbp_high)
    log_odds += coefs["treated_non_hdl"] * (is_statin * non_hdl_c)
    log_odds += coefs["age_non_hdl"] * (age_c * non_hdl_c)
    log_odds += coefs["age_hdl"] * (age_c * hdl_c_inter)
    log_odds += coefs["age_sbp_high"] * (age_c * sbp_high)
    log_odds += coefs["age_dm"] * (age_c * is_dm)
    log_odds += coefs["age_smoker"] * (age_c * is_smoker)
    log_odds += coefs["age_egfr_low"] * (age_c * egfr_low)

    # 3. ضرائب البيانات المفقودة (سر MDCalc)
    # بافتراض أن الزلال والرمز البريدي دائماً مفقودة حسب طلبك
    log_odds += coefs["missing_sdi"]
    log_odds += coefs["missing_acr"]

    # 4. حساب السكر التراكمي (متمركز عند 5.3 كما ورد في ملاحظة الجدول)
    if data.hba1c is not None:
        hba1c_c = data.hba1c - 5.3
        if data.diabetes:
            log_odds += coefs["hba1c_dm"] * hba1c_c
        else:
            log_odds += coefs["hba1c_no_dm"] * hba1c_c
    else:
        # إذا لم يدخل الطبيب السكر التراكمي، تفرض ضريبة "التراكمي المفقود"
        log_odds += coefs["missing_hba1c"]
            
    # 5. المعادلة النهائية
    risk = 1.0 / (1.0 + math.exp(-log_odds))
    return round(risk * 100, 2)

@app.post("/calculate_prevent")
def calculate_risk(patient: PatientData):
    try:
        if not (30 <= patient.age <= 79):
            raise HTTPException(status_code=400, detail="العمر غير مدعوم")
        risk = compute_prevent_total_cvd_full(patient)
        return {"prevent_10yr_risk_percent": risk}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
