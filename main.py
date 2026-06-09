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

# الهيكل المعماري
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

# دالة تحليل الأسماء بدقة فائقة لتفادي إزاحة الصفوف
def parse_row_name(name):
    name = name.lower()
    if "constant" in name or "intercept" in name: return "const"
    if "squared" in name: return "age_sq"
    if "age per 10" in name and not any(x in name for x in ["non-hdl", "hdl", "sbp", "diabetes", "smoking", "bmi", "egfr"]): return "age"
    if "treated" in name and "sbp" in name: return "treated_sbp_high"
    if "treated" in name and "non-hdl" in name: return "treated_non_hdl"
    if "age" in name and "non-hdl" in name: return "age_non_hdl"
    if "age" in name and "hdl" in name: return "age_hdl"
    if "age" in name and "sbp" in name: return "age_sbp_high"
    if "age" in name and "diabetes" in name: return "age_dm"
    if "age" in name and "smoking" in name: return "age_smoker"
    if "age" in name and "bmi" in name: return "age_bmi"
    if "age" in name and "egfr" in name: return "age_egfr_low"
    if "non-hdl" in name: return "non_hdl"
    if "hdl" in name: return "hdl"
    if "sbp <" in name or "sbp <110" in name: return "sbp_low"
    if "sbp \u2265" in name or "sbp >=110" in name or "sbp >=" in name or "sbp >= 110" in name: return "sbp_high"
    if "diabetes" in name: return "dm"
    if "smoking" in name or "smoker" in name: return "smoker"
    if "bmi <30" in name or "bmi < 30" in name: return "bmi_low"
    if "bmi 30+" in name or "bmi >= 30" in name: return "bmi_high"
    if "egfr <60" in name or "egfr < 60" in name: return "egfr_low"
    if "egfr 60+" in name or "egfr >= 60" in name: return "egfr_high"
    if "anti-hypertensive" in name or "bp med" in name: return "bp_med"
    if "statin" in name: return "statin"
    if "hba1c in dm" in name or ("hba1c" in name and "no dm" not in name): return "hba1c_dm"
    if "hba1c no dm" in name or ("hba1c" in name and "no dm" in name): return "hba1c_no_dm"
    return None

def get_val(row, idx):
    try:
        val = str(row[idx]).strip().replace(',', '')
        if not val or val.lower() in ['na', 'none', '-', '']: return 0.0
        return float(val)
    except:
        return 0.0

def load_csv_coefs():
    file_mapping = {
        "10yr": {"base": "base_10.csv", "hba1c": "hba1c_10.csv"},
        "30yr": {"base": "base_30.csv", "hba1c": "hba1c_30.csv"}
    }
    
    # التوزيع الدقيق للأعمدة بناءً على مستندات AHA
    col_map = {
        "total_cvd": {"female": 1, "male": 2},
        "ascvd":     {"female": 3, "male": 4},
        "hf":        {"female": 5, "male": 6},
        "chd":       {"female": 7, "male": 8},
        "stroke":    {"female": 9, "male": 10}
    }

    for period, models in file_mapping.items():
        for model_type, filename in models.items():
            if not os.path.exists(filename):
                continue
            try:
                with open(filename, mode='r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if not row or not str(row[0]).strip(): continue
                        
                        key = parse_row_name(row[0])
                        if not key: continue
                        
                        for outcome, genders in col_map.items():
                            for gender, col_idx in genders.items():
                                if col_idx < len(row):
                                    val = get_val(row, col_idx)
                                    COEFS[period][outcome][gender][model_type][key] = val
            except Exception as e:
                print(f"Error parsing {filename}: {str(e)}")

load_csv_coefs()

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
    
    bmi_low = (min(data.bmi, 30.0) - 25.0) / 5.0
    bmi_high = (max(data.bmi, 30.0) - 30.0) / 5.0
    
    is_dm = 1 if data.diabetes else 0
    is_smoker = 1 if data.smoker else 0
    is_bp_med = 1 if data.bp_med else 0
    is_statin = 1 if data.statin else 0
    hba1c_c = (data.hba1c - 5.3) if use_hba1c else 0

    results = {}

    for period in ["10yr", "30yr"]:
        # حماية العمر لـ 30 سنة (حسب توصيات AHA فقط من 30 إلى 59)
        if period == "30yr" and not (30 <= data.age <= 59):
            for outcome in ["total_cvd", "ascvd", "hf", "chd", "stroke"]:
                results[f"prevent_{period}_{outcome}"] = None
            continue

        for outcome in ["total_cvd", "ascvd", "hf", "chd", "stroke"]:
            key = f"prevent_{period}_{outcome}"
            c = COEFS[period][outcome][sex].get(model_type, {})
            
            if not c or "const" not in c:
                results[key] = None
                continue

            log_odds = c.get("const", 0)
            log_odds += c.get("age", 0) * age_c
            log_odds += c.get("age_sq", 0) * (age_c ** 2)
            log_odds += c.get("non_hdl", 0) * non_hdl_c
            log_odds += c.get("hdl", 0) * hdl_c
            log_odds += c.get("sbp_low", 0) * sbp_low
            log_odds += c.get("sbp_high", 0) * sbp_high
            log_odds += c.get("dm", 0) * is_dm
            log_odds += c.get("smoker", 0) * is_smoker
            log_odds += c.get("bmi_low", 0) * bmi_low
            log_odds += c.get("bmi_high", 0) * bmi_high
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
            log_odds += c.get("age_bmi", 0) * age_c * bmi_high
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
