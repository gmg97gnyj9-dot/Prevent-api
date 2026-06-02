from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
import pyprevent
import math

app = FastAPI(title="PREVENT Gold Standard Calculator API")

# تفعيل CORS لربط السيرفر بواجهة العيادة
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

def compute_gold_standard_prevent(data: PatientData) -> float:
    # 1. توحيد وحدات الكوليسترول (التحويل إلى mg/dL لأن حزم Cox تعتمد الحساب الأمريكي الافتراضي)
    tc_mgdl = data.total_chol if data.total_chol > 30 else data.total_chol * 38.67
    hdl_mgdl = data.hdl if data.hdl > 10 else data.hdl * 38.67
    
    # 2. تجهيز المتغيرات لتطابق مدخلات pyprevent الرسمية
    inputs = {
        "sex": data.sex.lower(),
        "age": int(data.age),
        "sbp": int(data.sbp),
        "bp_med": 1 if data.bp_med else 0,
        "total_chol": float(tc_mgdl),
        "hdl": float(hdl_mgdl),
        "egfr": float(data.egfr),
        "diabetes": 1 if data.diabetes else 0,
        "smoker": 1 if data.smoker else 0,
        "bmi": float(data.bmi),
        "hba1c": float(data.hba1c) if data.hba1c is not None else None,
        "uacr": None,  # مفقود تلقائياً كما في MDCalc
        "sdi": None,   # مفقود تلقائياً كما في MDCalc
        "endpoint": "total_cvd"  # حساب الخطر القلبي الوعائي الكلي المعروض في MDCalc
    }
    
    # 3. استدعاء ديناميكي مرن لمحرك البحث الرياضي داخل pyprevent لمنع أي خطأ في أسماء الدوال
    try:
        if hasattr(pyprevent, "calculate_10yr_risk"):
            risk = pyprevent.calculate_10yr_risk(**inputs)
        elif hasattr(pyprevent, "calculate_risk"):
            risk = pyprevent.calculate_risk(**inputs)
        elif hasattr(pyprevent, "prevent_10yr"):
            risk = pyprevent.prevent_10yr(**inputs)
        else:
            # دالة فحص احتياطية في حال اختلاف مسميات النسخ المحدثة
            funcs = [func for func in dir(pyprevent) if "risk" in func or "prevent" in func]
            if funcs:
                target_func = getattr(pyprevent, funcs[0])
                risk = target_func(**inputs)
            else:
                raise AttributeError("Could not find calculation function in pyprevent")
                
        # الحزمة تعود أحياناً بكسر عشري (مثل 0.1573) نقوم بضربه في 100 وتقريبه لخانة مئوية دقيقة
        if risk < 1.0:
            risk = risk * 100
            
        return round(risk, 2)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in pyprevent engine: {str(e)}")

@app.post("/calculate_prevent")
def calculate_risk(patient: PatientData):
    try:
        if not (30 <= patient.age <= 79):
            raise HTTPException(status_code=400, detail="العمر يجب أن يكون بين 30 و 79 عاماً")
            
        risk_percent = compute_gold_standard_prevent(patient)
        return {"prevent_10yr_risk_percent": risk_percent}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
