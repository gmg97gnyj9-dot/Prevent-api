import csv
import os
import math
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PREVENT Gold Standard Precision API")
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

# الهيكل المعماري الأساسي
COEFS = {
    "10yr": {
        "total_cvd": {"male": {"base": {}, "hba1c": {}}, "female": {"base": {}, "hba1c": {}}},
        "ascvd": {"male": {"base": {}, "hba1c": {}}, "female": {"base": {}, "hba1c": {}}},
        "hf": {"male": {"base": {}, "hba1c": {}}, "female": {"base": {}, "hba1c": {}}},
        "chd": {"male": {"base": {}, "hba1c": {}}, "female": {"base": {}, "hba1c": {}}},
        "stroke": {"male": {"base": {}, "hba1c": {}}, "female": {"base": {}, "hba1c": {}}}
    },
    "30yr": {
        "total_cvd": {"male": {"base": {}, "hba1c": {}}, "female": {"base": {}, "hba1c": {}}},
        "ascvd": {"male": {"base": {}, "hba1c": {}}, "female": {"base": {}, "hba1c": {}}},
        "hf": {"male": {"base": {}, "hba1c": {}}, "female": {"base": {}, "hba1c": {}}},
        "chd": {"male": {"base": {}, "hba1c": {}}, "female": {"base": {}, "hba1c": {}}},
        "stroke": {"male": {"base": {}, "hba1c": {}}, "female": {"base": {}, "hba1c": {}}}
    }
}

# 1. حائط الصد الاحتياطي (المعادلة الأصلية لـ 10 سنوات كما هي لضمان عدم تعطل التطبيق أبداً)
COEFS["10yr"]["total_cvd"]["male"]["base"] = {
    "const": -3.031168, "age": 0.7688528, "non_hdl": 0.0736174, "hdl": -0.0954431,
    "sbp_low": -0.4347345, "sbp_high": 0.3362658, "dm": 0.7692857, "smoker": 0.4386871,
    "egfr_low": 0.5378979, "egfr_high": 0.0164827, "bp_med": 0.288879, "statin": -0.1337349,
    "treated_sbp_high": -0.0475924, "treated_non_hdl": 0.150273, "age_non_hdl": -0.0517874,
    "age_hdl": 0.0191169, "age_sbp_high": -0.1049477, "age_dm": -0.2251948, "age_smoker": -0.0895067,
    "age_egfr_low": -0.1543702
}
COEFS["10yr"]["total_cvd"]["male"]["hba1c"] = {
    "const": -3.040901, "age": 0.7699177, "non_hdl": 0.0605093, "hdl": -0.0888525,
    "sbp_low": -0.417713, "sbp_high": 0.3288657, "dm": 0.4759471, "smoker": 0.4385663,
    "egfr_low": 0.5334616, "egfr_high": 0.0206431, "bp_med": 0.2917524, "statin": -0.1383313,
    "treated_sbp_high": -0.0482622, "treated_non_hdl": 0.1393796, "age_non_hdl": -0.0463501,
    "age_hdl": 0.0205926, "age_sbp_high": -0.1037717, "age_dm": -0.1737697, "age_smoker": -0.0915839,
    "age_egfr_low": -0.1637039, "hba1c_dm": 0.13159, "hba1c_no_dm": 0.1295185
}
COEFS["10yr"]["total_cvd"]["female"]["base"] = {
    "const": -3.307728, "age": 0.7939329, "non_hdl": 0.0305239, "hdl": -0.1606857,
    "sbp_low": -0.2394003, "sbp_high": 0.3600781, "dm": 0.8667604, "smoker": 0.5360739,
    "egfr_low": 0.6045917, "egfr_high": 0.0433769, "bp_med": 0.3151672, "statin": -0.1477655,
    "treated_sbp_high": -0.0663612, "treated_non_hdl": 0.1197879, "age_non_hdl": -0.0819715,
    "age_hdl": 0.0306769, "age_sbp_high": -0.0946348, "age_dm": -0.27057, "age_smoker": -0.078715,
    "age_egfr_low": -0.1637806
}
COEFS["10yr"]["total_cvd"]["female"]["hba1c"] = {
    "const": -3.306162, "age": 0.7858178, "non_hdl": 0.0194438, "hdl": -0.1521964,
    "sbp_low": -0.2296681, "sbp_high": 0.3465777, "dm": 0.5366241, "smoker": 0.5411682,
    "egfr_low": 0.5931898, "egfr_high": 0.0472458, "bp_med": 0.3158567, "statin": -0.1535174,
    "treated_sbp_high": -0.0687752, "treated_non_hdl": 0.1054746, "age_non_hdl": -0.0761119,
    "age_hdl": 0.0307469, "age_sbp_high": -0.0905966, "age_dm": -0.2241857, "age_smoker": -0.080186,
    "age_egfr_low": -0.1667286, "hba1c_dm": 0.1338348, "hba1c_no_dm": 0.1622409
}

# 2. محرك القراءة الآلي (CSV Auto-Parser)
# يقوم هذا المحرك بقراءة الملفات الأربعة إذا تم رفعها، واستخراج الـ 800 معامل بدقة متناهية
def load_csv_coefs():
    file_mapping = {
        "10yr": {"base": "base_10.csv", "hba1c": "hba1c_10.csv"},
        "30yr": {"base": "base_30.csv", "hba1c": "hba1c_30.csv"}
    }
    
    base_keys = ["const", "age", "non_hdl", "hdl", "sbp_low", "sbp_high", "dm", "smoker", "egfr_low", "egfr_high", "bp_med", "statin", "treated_sbp_high", "treated_non_hdl", "age_non_hdl", "age_hdl", "age_sbp_high", "age_dm", "age_smoker", "age_egfr_low"]
    hba1c_keys = base_keys + ["hba1c_dm", "hba1c_no_dm"]

    for period, models in file_mapping.items():
        for model_type, filename in models.items():
            if not os.path.exists(filename):
                continue
            
            keys = hba1c_keys if model_type == "hba1c" else base_keys
            try:
                with open(filename, mode='r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    
                    # البحث عن سطر البداية (Intercept) لتخطي العناوين
                    start_idx = 0
                    for i, row in enumerate(rows):
                        if row and "intercept" in row[0].lower():
                            start_idx = i
                            break
                    
                    data_rows = rows[start_idx : start_idx + len(keys)]
                    
                    for r_idx, row_data in enumerate(data_rows):
                        if r_idx >= len(keys): break
                        predictor = keys[r_idx]
                        
                        def get_val(idx):
                            try:
                                return float(row_data[idx])
                            except:
                                return 0.0

                        # تعبئة الإناث (الأعمدة من 1 إلى 5)
                        COEFS[period]["ascvd"]["female"][model_type][predictor] = get_val(1)
                        COEFS[period]["hf"]["female"][model_type][predictor] = get_val(2)
                        COEFS[period]["chd"]["female"][model_type][predictor] = get_val(3)
                        COEFS[period]["stroke"]["female"][model_type][predictor] = get_val(4)
                        COEFS[period]["total_cvd"]["female"][model_type][predictor] = get_val(5)
                        
                        # تعبئة الذكور (الأعمدة من 6 إلى 10)
                        COEFS[period]["ascvd"]["male"][model_type][predictor] = get_val(6)
                        COEFS[period]["hf"]["male"][model_type][predictor] = get_val(7)
                        COEFS[period]["chd"]["male"][model_type][predictor] = get_val(8)
                        COEFS[period]["stroke"]["male"][model_type][predictor] = get_val(9)
                        COEFS[period]["total_cvd"]["male"][model_type][predictor] = get_val(10)
            except Exception as e:
                print(f"Error parsing {filename}: {str(e)}")

# تشغيل المحرك عند بدء السيرفر
load_csv_coefs()

# 3. محرك الحساب الديناميكي (Dynamic Calculation Engine)
def compute_all_risks(data: PatientData) -> dict:
    use_hba1c = data.hba1c is not None
    model_type = "hba1c" if use_hba1c else "base"
    sex = data.sex.lower()
    
    tc_mmol = data.total_chol if data.total_chol < 30 else data.total_chol * 0.02586
    hdl_mmol = data.hdl if data.hdl < 10 else data.hdl * 0.02586
    
    age_c = (data.age - 55.0) / 10.0
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
    hba1c_c = (data.hba1c - 5.3) if use_hba1c else 0

    results = {}

    for period in ["10yr", "30yr"]:
        for outcome in ["total_cvd", "ascvd", "hf", "chd", "stroke"]:
            key = f"prevent_{period}_{outcome}"
            c = COEFS[period][outcome][sex].get(model_type, {})
            
            # إذا لم يتم رفع الإكسل، سيتجاهل المرض ويرجع None (باستثناء Total CVD الأساسي سيعمل دائماً)
            if not c or "const" not in c:
                results[key] = None
                continue

            log_odds = c.get("const", 0)
            log_odds += c.get("age", 0) * age_c
            log_odds += c.get("non_hdl", 0) * non_hdl_c
            log_odds += c.get("hdl", 0) * hdl_c
            log_odds += c.get("sbp_low", 0) * sbp_low
            log_odds += c.get("sbp_high", 0) * sbp_high
            log_odds += c.get("dm", 0) * is_dm
            log_odds += c.get("smoker", 0) * is_smoker
            log_odds += c.get("egfr_low", 0) * egfr_low
            log_odds += c.get("egfr_high", 0) * egfr_high
            log_odds += c.get("bp_med", 0) * is_bp_med
            log_odds += c.get("statin", 0) * is_statin
            
            log_odds += c.get("treated_sbp_high", 0) * is_bp_med * sbp_high
            log_odds += c.get("treated_non_hdl", 0) * is_statin * non_hdl_c
            log_odds += c.get("age_non_hdl", 0) * age_c * non_hdl_c
            log_odds += c.get("age_hdl", 0) * age_c * hdl_c
            log_odds += c.get("age_sbp_high", 0) * age_c * sbp_high
            log_odds += c.get("age_dm", 0) * age_c * is_dm
            log_odds += c.get("age_smoker", 0) * age_c * is_smoker
            log_odds += c.get("age_egfr_low", 0) * age_c * egfr_low

            if use_hba1c:
                log_odds += (c.get("hba1c_dm", 0) if is_dm else c.get("hba1c_no_dm", 0)) * hba1c_c
                
            risk = 1.0 / (1.0 + math.exp(-log_odds))
            results[key] = round(risk * 100, 2)
            
    return results

@app.post("/calculate_prevent")
def calculate_risk(patient: PatientData):
    tc_mgdl = patient.total_chol if patient.total_chol >= 30 else patient.total_chol / 0.02586
    hdl_mgdl = patient.hdl if patient.hdl >= 10 else patient.hdl / 0.02586

    # 4. حواجز الحماية السريرية (Guardrails)
    if not (30 <= patient.age <= 79):
        raise HTTPException(status_code=400, detail="(العمر خارج النطاق المدعوم 30-79)")
    if not (90 <= patient.sbp <= 200):
        raise HTTPException(status_code=400, detail="(ضغط الدم الانقباضي خارج النطاق المدعوم 90-200)")
    if not (130 <= tc_mgdl <= 320):
        raise HTTPException(status_code=400, detail="(الكوليسترول الكلي خارج النطاق المدعوم 130-320)")
    if not (20 <= hdl_mgdl <= 100):
        raise HTTPException(status_code=400, detail="(كوليسترول HDL خارج النطاق المدعوم 20-100)")
    if not (15 <= patient.egfr <= 140):
        raise HTTPException(status_code=400, detail="(معدل ترشيح الكلى خارج النطاق المدعوم 15-140)")
    if not (18.5 <= patient.bmi <= 39.9):
        raise HTTPException(status_code=400, detail="(مؤشر كتلة الجسم خارج النطاق المدعوم 18.5-39.9)")
    if patient.hba1c is not None and not (3 <= patient.hba1c <= 15):
        raise HTTPException(status_code=400, detail="(السكر التراكمي خارج النطاق المدعوم 3-15)")

    try:
        return compute_all_risks(patient)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
