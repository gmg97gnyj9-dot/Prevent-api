from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
import pyprevent

app = FastAPI(title="PREVENT Gold Standard Calculator API")
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

@app.post("/calculate_prevent")
def calculate_risk(patient: PatientData):
    try:
        # توحيد الوحدات للنظام الأمريكي الذي تعتمده المكتبة حصرياً (mg/dL)
        tc_mgdl = patient.total_chol if patient.total_chol > 30 else patient.total_chol * 38.67
        hdl_mgdl = patient.hdl if patient.hdl > 10 else patient.hdl * 38.67

        # تجهيز المتغيرات بالأسماء الدقيقة المطلوبة داخل مكتبة pyprevent
        kwargs = {
            "sex": "MALE" if patient.sex.lower() == "male" else "FEMALE",
            "age": float(patient.age),
            "total_cholesterol": float(tc_mgdl),
            "hdl_cholesterol": float(hdl_mgdl),
            "systolic_bp": float(patient.sbp),
            "has_diabetes": bool(patient.diabetes),
            "current_smoker": bool(patient.smoker),
            "bmi": float(patient.bmi),
            "egfr": float(patient.egfr),
            "on_htn_meds": bool(patient.bp_med),
            "on_cholesterol_meds": bool(patient.statin)
        }

        # إضافة السكر التراكمي في حال توفره
        if patient.hba1c is not None:
            kwargs["hba1c"] = float(patient.hba1c)

        # مسح ذكي للمكتبة لاستخراج دالة حساب (10 سنوات للخطر الكلي) ديناميكياً
        available_funcs = dir(pyprevent)
        target_func_name = None
        
        # البحث أولاً عن دالة الخطر الكلي CVD
        for f in available_funcs:
            if "10" in f.lower() and "cvd" in f.lower() and "ascvd" not in f.lower():
                target_func_name = f
                break
                
        # كخيار بديل إذا لم تتوفر سوى ASCVD
        if not target_func_name:
            for f in available_funcs:
                if "10" in f.lower() and "ascvd" in f.lower():
                    target_func_name = f
                    break
                    
        if not target_func_name:
            raise Exception(f"Functions available in library: {available_funcs}")

        target_func = getattr(pyprevent, target_func_name)

        # استدعاء الدالة بحذر (إذا كانت المكتبة لا تقبل التراكمي كمدخل مباشر سيتم استبعاده)
        try:
            risk = target_func(**kwargs)
        except TypeError as e:
            if "hba1c" in str(e).lower() and "hba1c" in kwargs:
                del kwargs["hba1c"]
                risk = target_func(**kwargs)
            else:
                raise e

        # تحويل الرقم إذا جاء بصيغة كسر (0.157) ليصبح (15.7)
        if risk < 1.0:
            risk = risk * 100

        return {"prevent_10yr_risk_percent": round(risk, 2), "used_function": target_func_name}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
