from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PREVENT Risk Calculator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تم إضافة الستاتين والتراكمي (اختياري)
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

def compute_prevent_stable_mock(data: PatientData) -> float:
    # محاكاة مستقرة رياضياً لتفادي مشكلة الـ 100% أثناء اختبار الواجهة
    # (النسخة الإكلينيكية النهائية تتطلب إدراج الجداول الأصلية للـ AHA)
    
    age_c = (data.age - 55) / 10
    sbp_c = (data.sbp - 120) / 20
    tc_c = (data.total_chol - 190) / 40
    hdl_c = (data.hdl - 45) / 15
    egfr_c = (data.egfr - 90) / 15
    bmi_c = (data.bmi - 25) / 5

    # خطر أساسي افتراضي 5%
    risk_score = 0.05  
    
    risk_score += age_c * 0.03
    risk_score += sbp_c * 0.015
    risk_score += tc_c * 0.01
    risk_score -= hdl_c * 0.01
    risk_score -= egfr_c * 0.005
    risk_score += bmi_c * 0.005
    
    if data.diabetes: risk_score += 0.03
    if data.smoker: risk_score += 0.025
    if data.bp_med: risk_score += 0.01
    if data.statin: risk_score -= 0.015  # الستاتين يقلل الخطر

    # منطق السكر التراكمي: إذا تم إرساله، تتغير الحسبة (Base + HbA1c Model)
    if data.hba1c is not None:
        hba1c_c = (data.hba1c - 5.5) / 1.0
        risk_score += hba1c_c * 0.015

    # حماية الكود من إعطاء نسب غير منطقية (منع الانفجار الرياضي)
    risk_score = max(0.001, min(risk_score, 0.99))
    
    return round(risk_score * 100, 2)

@app.post("/calculate_prevent")
def calculate_risk(patient: PatientData):
    try:
        if not (30 <= patient.age <= 79):
            raise HTTPException(status_code=400, detail="العمر غير مدعوم")
        risk = compute_prevent_stable_mock(patient)
        return {"prevent_10yr_risk_percent": risk}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
