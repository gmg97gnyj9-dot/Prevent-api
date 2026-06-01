from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import math

app = FastAPI(title="PREVENT Risk Calculator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# إضافة المتغيرات الثلاثة الجديدة إلى قالب البيانات
class PatientData(BaseModel):
    age: float
    sex: str
    sbp: float
    total_chol: float
    hdl: float
    egfr: float
    bmi: float
    diabetes: bool      # مصاب بالسكري: True أو False
    smoker: bool        # مدخن: True أو False
    bp_med: bool        # يأخذ علاج ضغط: True أو False

def compute_prevent_10yr_cvd(data: PatientData) -> float:
    ln_age = math.log(data.age)
    ln_sbp = math.log(data.sbp)
    ln_tc = math.log(data.total_chol)
    ln_hdl = math.log(data.hdl)
    ln_egfr = math.log(data.egfr)
    ln_bmi = math.log(data.bmi)

    if data.sex.lower() == "female":
        base_survival = 0.9482
        mean_core = -1.9023
        
        # إضافة تأثير السكري، التدخين، وعلاج الضغط في النموذج الإحصائي للإناث
        linear_predictor = (
            (ln_age * 2.143) + 
            (ln_sbp * 1.621) + 
            (ln_tc * 0.492) - 
            (ln_hdl * 0.531) - 
            (ln_egfr * 0.115) + 
            (ln_bmi * 0.201) +
            (0.561 if data.diabetes else 0.0) +
            (0.423 if data.smoker else 0.0) +
            (0.281 if data.bp_med else 0.0)
        )
    else:
        base_survival = 0.9125
        mean_core = -1.7241
        
        # إضافة تأثير السكري، التدخين، وعلاج الضغط في النموذج الإحصائي للذكور
        linear_predictor = (
            (ln_age * 1.982) + 
            (ln_sbp * 1.541) + 
            (ln_tc * 0.532) - 
            (ln_hdl * 0.421) - 
            (ln_egfr * 0.092) + 
            (ln_bmi * 0.152) +
            (0.482 if data.diabetes else 0.0) +
            (0.391 if data.smoker else 0.0) +
            (0.224 if data.bp_med else 0.0)
        )

    risk_score = 1.0 - math.pow(base_survival, math.exp(linear_predictor - mean_core))
    return round(risk_score * 100, 2)

@app.post("/calculate_prevent")
def calculate_risk(patient: PatientData):
    try:
        if not (30 <= patient.age <= 79):
            raise HTTPException(status_code=400, detail="معادلة PREVENT مخصصة للأعمار بين 30 و 79 عاماً فقط.")
            
        risk = compute_prevent_10yr_cvd(patient)
        return {"prevent_10yr_risk_percent": risk}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
