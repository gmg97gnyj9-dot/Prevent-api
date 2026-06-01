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

def compute_prevent_ascvd_10yr(data: PatientData) -> float:
    # 1. تحويل المتغيرات للنظام المتمركز (Centered Variables) كما في كود AHA
    age_c = (data.age - 55.0) / 10.0
    
    tc_mmol = data.total_chol * 0.02586
    hdl_mmol = data.hdl * 0.02586
    non_hdl_c = (tc_mmol - hdl_mmol) - 3.5
    hdl_c = (hdl_mmol - 1.3) / 0.3
    
    sbp_low = (min(data.sbp, 110.0) - 110.0) / 20.0
    sbp_high = (max(data.sbp, 110.0) - 130.0) / 20.0
    
    egfr_low = (min(data.egfr, 60.0) - 60.0) / -15.0
    egfr_high = (max(data.egfr, 60.0) - 90.0) / -15.0
    
    is_dm = 1 if data.diabetes else 0
    is_smoker = 1 if data.smoker else 0
    is_bp_med = 1 if data.bp_med else 0
    is_statin = 1 if data.statin else 0
    
    # 2. حساب لوغاريتم الأرجحية (Log-Odds) بالمعاملات الرسمية الدقيقة
    if data.sex.lower() == "female":
        log_odds = -3.838746
        log_odds += 0.719883 * age_c
        log_odds += 0.1176967 * non_hdl_c
        log_odds += -0.151185 * hdl_c
        log_odds += -0.0835358 * sbp_low
        log_odds += 0.3592852 * sbp_high
        log_odds += 0.8348585 * is_dm
        log_odds += 0.4831078 * is_smoker
        log_odds += 0.4864619 * egfr_low
        log_odds += 0.0397779 * egfr_high
        log_odds += 0.2265309 * is_bp_med
        log_odds += -0.0592374 * is_statin
        
        # التفاعلات المتقاطعة للإناث (Interaction Terms)
        log_odds += -0.0395762 * (is_bp_med * sbp_high)
        log_odds += 0.0844423 * (is_statin * non_hdl_c)
        log_odds += -0.0567839 * (age_c * non_hdl_c)
        log_odds += 0.0325692 * (age_c * hdl_c)
        log_odds += -0.1035985 * (age_c * sbp_high)
        log_odds += -0.2417542 * (age_c * is_dm)
        log_odds += -0.0791142 * (age_c * is_smoker)
        log_odds += -0.1671492 * (age_c * egfr_low)
        
    else:
        log_odds = -3.51835
        log_odds += 0.7099847 * age_c
        log_odds += 0.1658663 * non_hdl_c
        log_odds += -0.1144285 * hdl_c
        log_odds += -0.2837212 * sbp_low
        log_odds += 0.3239977 * sbp_high
        log_odds += 0.7189597 * is_dm
        log_odds += 0.3956973 * is_smoker
        log_odds += 0.3690075 * egfr_low
        log_odds += 0.0203619 * egfr_high
        log_odds += 0.2036522 * is_bp_med
        log_odds += -0.0865581 * is_statin
        
        # التفاعلات المتقاطعة للذكور (Interaction Terms)
        log_odds += -0.0322916 * (is_bp_med * sbp_high)
        log_odds += 0.114563 * (is_statin * non_hdl_c)
        log_odds += -0.0300005 * (age_c * non_hdl_c)
        log_odds += 0.0232747 * (age_c * hdl_c)
        log_odds += -0.0927024 * (age_c * sbp_high)
        log_odds += -0.2018525 * (age_c * is_dm)
        log_odds += -0.0970527 * (age_c * is_smoker)
        log_odds += -0.1217081 * (age_c * egfr_low)
        
    # 3. التحويل النهائي لنسبة مئوية
    risk = 1.0 / (1.0 + math.exp(-log_odds))
    return round(risk * 100, 2)

@app.post("/calculate_prevent")
def calculate_risk(patient: PatientData):
    try:
        if not (30 <= patient.age <= 79):
            raise HTTPException(status_code=400, detail="العمر غير مدعوم")
        risk = compute_prevent_ascvd_10yr(patient)
        return {"prevent_10yr_risk_percent": risk}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
