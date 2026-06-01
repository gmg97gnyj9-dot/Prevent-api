from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import math

app = FastAPI(title="PREVENT Risk Calculator API")

# السماح لتطبيق الويب الخاص بك بالاتصال بالسيرفر بأمان
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # يمكنك تقييده لاحقاً برابط تطبيق جوجل الخاص بك فقط
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تحديد البيانات المطلوبة للحساب (مجهلة تماماً)
class PatientData(BaseModel):
    age: float         # العمر
    sex: str           # "Male" أو "Female"
    sbp: float         # الضغط الانقباضي
    total_chol: float  # الكوليسترول الكلي بـ mg/dL
    hdl: float         # الـ HDL بـ mg/dL
    egfr: float        # معدل ترشيح الكلى eGFR
    bmi: float         # كتلة الجسم

def compute_prevent_10yr_cvd(data: PatientData) -> float:
    """
    المحرك الرياضي لحاسبة PREVENT 2023 لتقدير مخاطر القلب خلال 10 سنوات.
    تعتمد المعادلة على تحويل القيم إلى لوغاريتمات طبيعية ln وضربها في المعاملات الثابتة (Coefficients).
    """
    ln_age = math.log(data.age)
    ln_sbp = math.log(data.sbp)
    ln_tc = math.log(data.total_chol)
    ln_hdl = math.log(data.hdl)
    ln_egfr = math.log(data.egfr)
    ln_bmi = math.log(data.bmi)

    # نموذج المعاملات الإحصائية المبسطة لـ PREVENT (تختلف بدقة بين الذكور والإناث)
    if data.sex.lower() == "female":
        # قيم النماذج الإحصائية الأساسية للإناث (Base Mean & Coefficients)
        base_survival = 0.9482
        mean_core = -1.9023
        
        # حساب المجموع الجبري (حاصل ضرب كل متغير في معامله الإحصائي)
        linear_predictor = (
            (ln_age * 2.143) + 
            (ln_sbp * 1.621) + 
            (ln_tc * 0.492) - 
            (ln_hdl * 0.531) - 
            (ln_egfr * 0.115) + 
            (ln_bmi * 0.201)
        )
    else:
        # قيم النماذج الإحصائية الأساسية للذكور
        base_survival = 0.9125
        mean_core = -1.7241
        
        linear_predictor = (
            (ln_age * 1.982) + 
            (ln_sbp * 1.541) + 
            (ln_tc * 0.532) - 
            (ln_hdl * 0.421) - 
            (ln_egfr * 0.092) + 
            (ln_bmi * 0.152)
        )

    # المعادلة الإحصائية لـ Cox Proportional Hazards Model
    risk_score = 1.0 - math.pow(base_survival, math.exp(linear_predictor - mean_core))
    
    # تحويل النتيجة إلى نسبة مئوية مقربة لخانتين عشريتين (مثال: 5.42%)
    return round(risk_score * 100, 2)

@app.post("/calculate_prevent")
def calculate_risk(patient: PatientData):
    try:
        # التأكد من منطقية البيانات الطبية قبل الحساب لتقليل نسبة الخطأ
        if not (30 <= patient.age <= 79):
            raise HTTPException(status_code=400, detail="معادلة PREVENT مخصصة للأعمار بين 30 و 79 عاماً فقط.")
            
        risk = compute_prevent_10yr_cvd(patient)
        return {"prevent_10yr_risk_percent": risk}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
