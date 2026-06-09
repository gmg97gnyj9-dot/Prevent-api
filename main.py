import math
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PREVENT API (Ultimate Hardcoded Engine)")
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

# =====================================================================
# الجداول الطبية (Raw Data) كما نُشرت من AHA لضمان الدقة وتفادي الهلوسة
# =====================================================================

RAW_S12A = """
Age, per 10 years	0.7939329	0.7688528	0.719883	0.7099847	0.8998235	0.8972642	0.7587146	0.7423283	0.6907849	0.722513
non-HDL-C per 1 mmol/L	0.0305239	0.0736174	0.1176967	0.1658663			0.1810949	0.2572109	0.0534279	0.0263348
HDL-C per 0.3 mmol/L	-0.1606857	-0.0954431	-0.151185	-0.1144285			-0.2014507	-0.1820374	-0.1055109	-0.0248959
SBP <110 per 20 mmHg	-0.2394003	-0.4347345	-0.0835358	-0.2837212	-0.4559771	-0.6811466	-0.0881827	-0.3174515	-0.113078	-0.268104
SBP ≥110 per 20 mmHg	0.3600781	0.3362658	0.3592852	0.3239977	0.3576505	0.3634461	0.3547731	0.312778	0.3665217	0.3474634
Diabetes	0.8667604	0.7692857	0.8348585	0.7189597	1.038346	0.923776	0.9045358	0.7485249	0.8013721	0.684699
Current smoking	0.5360739	0.4386871	0.4831078	0.3956973	0.583916	0.5023736	0.5410917	0.3912047	0.4187039	0.3874844
BMI <30, per 5 kg/m2					-0.0072294	-0.0485841					
BMI 30+, per 5 kg/m2					0.2997706	0.3726929					
eGFR <60, per -15 ml	0.6045917	0.5378979	0.4864619	0.3690075	0.7451638	0.6926917	0.5198725	0.376487	0.4539767	0.3877827
eGFR 60+, per -15 ml	0.0433769	0.0164827	0.0397779	0.0203619	0.0557087	0.0251827	0.0325935	0.0193687	0.0515087	0.0201965
Anti-hypertensive use	0.3151672	0.288879	0.2265309	0.2036522	0.3534442	0.2980922	0.2010642	0.1588199	0.2494624	0.232963
Statin use	-0.1477655	-0.1337349	-0.0592374	-0.0865581			-0.036195	-0.0494555	-0.0798829	-0.1178935
Treated SBP ≥110 mm Hg per 20 mm Hg	-0.0663612	-0.0475924	-0.0395762	-0.0322916	-0.0981511	-0.0497731	-0.0891238	-0.0577851	-0.0079039	0.0120926
Treated non-HDL-C	0.1197879	0.150273	0.0844423	0.114563			0.0750716	0.0809765	0.0833101	0.155739
Age per 10yr * non-HDL-C per 1 mmol/L	-0.0819715	-0.0517874	-0.0567839	-0.0300005			-0.0683256	-0.0517872	-0.0409242	0.0141928
Age per 10yr * HDL-C per 1 mml/L	0.0306769	0.0191169	0.0325692	0.0232747			0.0484755	0.0489033	0.016994	-0.0111745
Age per 10yr * SBP ≥110 mm Hg per 20 mmHg	-0.0946348	-0.1049477	-0.1035985	-0.0927024	-0.0946663	-0.1289201	-0.0898086	-0.0850404	-0.1191213	-0.1155391
Age per 10yr * diabetes	-0.27057	-0.2251948	-0.2417542	-0.2018525	-0.3581041	-0.3040924	-0.2569041	-0.2107552	-0.2480549	-0.2123743
Age per 10yr * current smoking	-0.078715	-0.0895067	-0.0791142	-0.0970527	-0.1159453	-0.1401688	-0.0786607	-0.1206397	-0.0998063	-0.0824133
Age per 10yr * BMI 30+ per 5 kg/m2					-0.003878	0.0068126					
Age per 10yr * eGFR <60, per -15 ml	-0.1637806	-0.1543702	-0.1671492	-0.1217081	-0.1884289	-0.1797778	-0.1597513	-0.07795	-0.1759075	-0.180789
Constant	-3.307728	-3.031168	-3.819975	-3.500655	-4.310409	-3.946391	-4.608751	-4.156753	-4.409199	-4.20881
"""

RAW_S12C = """
Age, 10 years	0.7858178	0.7699177	0.7111831	0.7064146	0.8997391	0.911787	0.7559415	0.7223642	0.6854957	0.7244468
non-HDL-C per 1 mmol/L	0.0194438	0.0605093	0.106797	0.1532267			0.1663933	0.2443591	0.043261	0.0134286
HDL-C per 0.3 mmol/L	-0.1521964	-0.0888525	-0.1425745	-0.1082166			-0.1905004	-0.1755236	-0.0983793	-0.0204357
SBP <110 per 20 mmHg	-0.2296681	-0.417713	-0.0736824	-0.2675288	-0.4422749	-0.6568071	-0.0768509	-0.3025745	-0.1017197	-0.2506963
SBP ≥110 per 20 mmHg	0.3465777	0.3288657	0.3480844	0.3173809	0.3378691	0.3524645	0.339647	0.3056892	0.3565955	0.3408562
Diabetes	0.5366241	0.4759471	0.5112951	0.432604	0.681284	0.5849752	0.5632228	0.4874841	0.4609555	0.35355
Current smoking	0.5411682	0.4385663	0.4880292	0.3958842	0.5886005	0.5014014	0.5478	0.3942456	0.4198301	0.3854904
BMI <30, per 5 kg/m2					-0.0148657	-0.0512352				
BMI 30+, per 5 kg/m2					0.2958374	0.365294				
eGFR <60, per -15 ml	0.5931898	0.5334616	0.4754997	0.3665014	0.73447	0.6892219	0.5105085	0.3748008	0.4436518	0.3869787
eGFR 60+, per -15 ml	0.0472458	0.0206431	0.0438132	0.0250243	0.05926	0.0292377	0.0381344	0.0250407	0.0544989	0.0237663
Anti-hypertensive use	0.3158567	0.2917524	0.2259093	0.2061158	0.3543475	0.3038296	0.2023093	0.1616182	0.2493831	0.236159
Statin use	-0.1535174	-0.1383313	-0.0648872	-0.0899988			-0.0425927	-0.0513733	-0.0859775	-0.1241976
Treated SBP ≥110 mm Hg per 20 mm Hg	-0.0687752	-0.0482622	-0.0437645	-0.0334959	-0.1002139	-0.0515032	-0.0953791	-0.059131	-0.0114564	0.0095878
Treated non-HDL-C	0.1054746	0.1393796	0.0697082	0.1034168			0.0587372	0.0710909	0.0689079	0.1424174
Age per 10yr * non-HDL-C per 1 mmol/L	-0.0761119	-0.0463501	-0.0506382	-0.0255406			-0.0607664	-0.0476587	-0.036013	0.018922
Age per 10yr * HDL-C per 1 mml/L	0.0307469	0.0205926	0.0327475	0.0247538			0.0485765	0.0502694	0.0171809	-0.0093452
Age per 10yr * SBP ≥110 mm Hg per 20 mmHg	-0.0905966	-0.1037717	-0.0996442	-0.0917441	-0.0878765	-0.1262343	-0.0841698	-0.0838455	-0.115679	-0.1143576
Age per 10yr * diabetes	-0.2241857	-0.1737697	-0.1924338	-0.1499195	-0.303684	-0.2449514	-0.1986967	-0.1630679	-0.2025816	-0.1559808
Age per 10yr * current smoking	-0.080186	-0.0915839	-0.0803539	-0.098089	-0.1178943	-0.1392217	-0.0807069	-0.1220691	-0.1003882	-0.0824194
Age per 10yr * BMI 30+ per 5 kg/m2					-0.008345	0.0009592				
Age per 10yr * eGFR <60, per -15 ml	-0.1667286	-0.1637039	-0.1682586	-0.1305231	-0.1912183	-0.1917105	-0.1610913	-0.0859505	-0.1760082	-0.1890904
HbA1c in DM, per 1%	0.1338348	0.13159	0.1339055	0.1157161	0.1856442	0.1652857	0.1832739	0.1251064	0.0929695	0.1076023
HbA1c no DM, per 1%	0.1622409	0.1295185	0.1596461	0.1288303	0.1833083	0.1505859	0.1755465	0.1177006	0.1545054	0.1408596
Constant	-3.306162	-3.040901	-3.838746	-3.51835	-4.288225	-3.961954	-4.667457	-4.219654	-4.396448	-4.179346
"""

RAW_S12F = """
Age, 10 years	0.5503079	0.4627309	0.4669202	0.3994099	0.6254374	0.5681541	0.4912423	0.4171209	0.4366978	0.4003448
Age squared	-0.0928369	-0.0984281	-0.0893118	-0.0937484	-0.0983038	-0.1048388	-0.0917078	-0.0949994	-0.0873673	-0.0935927
non-HDL-C per 1 mmol/L	0.0409794	0.0836088	0.1256901	0.1744643			0.1878256	0.2651913	0.0586334	0.0309419
HDL-C per 0.3 mmol/L	-0.1663306	-0.1029824	-0.1542255	-0.120203			-0.2035703	-0.1879446	-0.1069016	-0.0280763
SBP <110 per 20 mmHg	-0.1628654	-0.2140352	-0.0018093	-0.0665117	-0.3919241	-0.4761564	-0.0030222	-0.0971746	-0.0317106	-0.047704
SBP ≥110 per 20 mmHg	0.3299505	0.2904325	0.322949	0.2753037	0.3142295	0.30324	0.3111757	0.258931	0.3272741	0.2925734
Diabetes	0.6793894	0.5331276	0.6296707	0.4790257	0.8330787	0.6840338	0.6803247	0.4956463	0.5841726	0.4236823
Current smoking	0.3196112	0.2141914	0.268292	0.1782635	0.3438651	0.2656273	0.3215313	0.1728844	0.2045681	0.1675238
BMI <30, per 5 kg/m2					0.0594874	0.0833107					
BMI 30+, per 5 kg/m2					0.2525536	0.26999					
eGFR <60, per -15 ml	0.1857101	0.1155556	0.100106	-0.0218789	0.2981642	0.2541805	0.1252615	-0.0091955	0.0765812	-0.0009216
eGFR 60+, per -15 ml	0.0553528	0.0603775	0.0499663	0.0602553	0.0667159	0.0638923	0.0414579	0.0578155	0.0603226	0.0575221
Anti-hypertensive use	0.2894	0.232714	0.1875292	0.1421182	0.333921	0.2583631	0.1561303	0.0939196	0.2087816	0.1685514
Statin use	-0.075688	-0.0272112	0.0152476	0.0135996			0.0384138	0.0508921	-0.0095137	-0.020829
Treated SBP ≥110 mm Hg per 20 mm Hg	-0.056367	-0.0384488	-0.0276123	-0.0218265	-0.0893177	-0.0391938	-0.0795531	-0.0486024	0.0014436	0.0230042
Treated non-HDL-C	0.1071019	0.134192	0.0736147	0.1013148			0.0635262	0.0669478	0.0720012	0.1413652
Age per 10yr * non-HDL-C per 1 mmol/L	-0.0751438	-0.0511759	-0.0521962	-0.0312619			-0.0637665	-0.0533361	-0.0361779	0.0145411
Age per 10yr * HDL-C per 1 mml/L	0.0301786	0.0165865	0.0316918	0.020673			0.0474074	0.0461425	0.015888	-0.0149606
Age per 10yr * SBP ≥110 mm Hg per 20 mmHg	-0.0998776	-0.1101437	-0.1046101	-0.0920935	-0.0974299	-0.1269124	-0.0876484	-0.0812234	-0.1179062	-0.1118468
Age per 10yr * diabetes	-0.3206166	-0.2585943	-0.2727793	-0.2159947	-0.404855	-0.3273572	-0.2803099	-0.216315	-0.2710221	-0.2152953
Age per 10yr * current smoking	-0.1607862	-0.1566406	-0.1530907	-0.1548811	-0.1982991	-0.2043019	-0.1513626	-0.1749197	-0.1702836	-0.1339295
Age per 10yr * BMI 30+ per 5 kg/m2					-0.0035619	-0.0182831					
Age per 10yr * eGFR <60, per -15 ml	-0.1450788	-0.1166776	-0.1299149	-0.0712547	-0.1564215	-0.1342618	-0.1130454	-0.0241467	-0.1320992	-0.1225081
Constant	-1.318827	-1.148204	-1.974074	-1.736444	-2.205379	-1.95751	-2.733866	-2.376762	-2.62078	-2.458022
"""

RAW_S12H = """
Age, 10 years	0.5343493	0.4519873	0.4555574	0.3883267	0.6210856	0.5703729	0.4853187	0.3944508	0.4296679	0.397402
Age squared	-0.0952314	-0.101624	-0.0903501	-0.0958114	-0.1000972	-0.1084544	-0.0929654	-0.0956857	-0.0883118	-0.0953425
non-HDL-C per 1 mmol/L	0.0298124	0.0700456	0.1148321	0.1613374			0.1733152	0.2519365	0.0487321	0.0180202
HDL-C per 0.3 mmol/L	-0.1578451	-0.0968005	-0.1458754	-0.1144418			-0.1929452	-0.181881	-0.1001406	-0.0242534
SBP <110 per 20 mmHg	-0.1504488	-0.1923527	0.0089323	-0.0474338	-0.3773697	-0.4471767	0.0092228	-0.0829203	-0.0199947	-0.0283414
SBP ≥110 per 20 mmHg	0.3173368	0.2827043	0.3139029	0.2691281	0.295316	0.2910152	0.298244	0.2534596	0.3198382	0.2870641
Diabetes	0.4314738	0.3417152	0.386281	0.2859773	0.5681692	0.4507242	0.4210289	0.3298202	0.3270964	0.1894407
Current smoking	0.3209399	0.2105272	0.2714309	0.1759553	0.3449139	0.259585	0.3254237	0.1773379	0.2039542	0.1632278
BMI <30, per 5 kg/m2					0.0540094	0.0850676				
BMI 30+, per 5 kg/m2					0.249767	0.2637222				
eGFR <60, per -15 ml	0.1771435	0.1113291	0.0930987	-0.0242898	0.2875781	0.2454706	0.1183472	-0.0059506	0.0699052	-0.0027618
eGFR 60+, per -15 ml	0.0582828	0.0640135	0.0532216	0.0644523	0.0692013	0.0675649	0.0462805	0.0625623	0.062555	0.0605617
Anti-hypertensive use	0.2888947	0.2334248	0.1862181	0.142874	0.3334936	0.2611991	0.1565331	0.0960268	0.2080978	0.1700368
Statin use	-0.0795886	-0.0299421	0.0106964	0.0115062			0.033512	0.0489115	-0.0142009	-0.0256155
Treated SBP ≥110 mm Hg per 20 mm Hg	-0.0600438	-0.0393204	-0.0329713	-0.02333	-0.0922339	-0.0408908	-0.0866143	-0.050231	-0.0029543	0.0201099
Treated non-HDL-C	0.0920598	0.1228854	0.0583609	0.0899664			0.0468497	0.0573554	0.0574525	0.1281684
Age per 10yr * non-HDL-C per 1 mmol/L	-0.0696108	-0.0463737	-0.0463273	-0.0275478			-0.0564555	-0.0498819	-0.0315382	0.0185524
Age per 10yr * HDL-C per 1 mml/L	0.0308807	0.0184599	0.0324717	0.022573			0.0481034	0.0479144	0.0166448	-0.0127335
Age per 10yr * SBP ≥110 mm Hg per 20 mmHg	-0.0954051	-0.1085744	-0.1004777	-0.090802	-0.0907885	-0.1241051	-0.0819801	-0.0796665	-0.114502	-0.1105848
Age per 10yr * diabetes	-0.2763408	-0.2208049	-0.2266944	-0.1771894	-0.3554646	-0.2849461	-0.2264933	-0.1822839	-0.2298924	-0.1744077
Age per 10yr * current smoking	-0.1623944	-0.1577978	-0.1541859	-0.1548847	-0.2008846	-0.2032308	-0.153584	-0.1744951	-0.170899	-0.1333941
Age per 10yr * BMI 30+ per 5 kg/m2					-0.0079611	-0.0239714				
Age per 10yr * eGFR <60, per -15 ml	-0.1430514	-0.1179375	-0.1286005	-0.0732754	-0.156803	-0.138301	-0.1122738	-0.0259456	-0.1307433	-0.1254591
HbA1c in DM, per 1%	0.0940543	0.0768169	0.0875827	0.0591089	0.1448336	0.1101184	0.134395	0.0695636	0.0457624	0.0500544
HbA1c no DM, per 1%	0.1116486	0.0777295	0.1126417	0.0821158	0.1277838	0.0949198	0.1270458	0.0707541	0.1056467	0.0917727
Constant	-1.341059	-1.180767	-2.011533	-1.777708	-2.193553	-1.974999	-2.802642	-2.48433	-2.618396	-2.438154
"""

# =====================================================================
# الهيكل المعماري (القاموس) لحفظ كل المعاملات الـ 800
# =====================================================================
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

# =====================================================================
# محرك التفكيك الآلي الذكي للنصوص (Auto-Parser)
# يقرأ الأعمدة بذكاء ويتخطى الفراغات ليضع كل رقم في مكانه الصحيح
# =====================================================================
def parse_row_name(name):
    name = name.lower()
    if "constant" in name or "intercept" in name: return "const"
    if "squared" in name: return "age_sq"
    if "age" in name and "10" in name and "*" not in name and "non" not in name and "sbp" not in name and "bmi" not in name: return "age"
    if "treated" in name and "sbp" in name: return "treated_sbp_high"
    if "treated" in name and "non-hdl" in name: return "treated_non_hdl"
    if "age" in name and "*" in name and "non-hdl" in name: return "age_non_hdl"
    if "age" in name and "*" in name and "hdl" in name and "non" not in name: return "age_hdl"
    if "age" in name and "*" in name and "sbp" in name: return "age_sbp_high"
    if "age" in name and "*" in name and "diabetes" in name: return "age_dm"
    if "age" in name and "*" in name and "smoking" in name: return "age_smoker"
    if "age" in name and "*" in name and "bmi" in name: return "age_bmi"
    if "age" in name and "*" in name and "egfr" in name: return "age_egfr_low"
    if "non-hdl" in name and "*" not in name: return "non_hdl"
    if "hdl" in name and "non" not in name and "*" not in name: return "hdl"
    if "sbp <110" in name and "*" not in name: return "sbp_low"
    if "sbp ≥110" in name and "*" not in name: return "sbp_high"
    if "diabetes" in name and "*" not in name and "hba1c" not in name: return "dm"
    if "smoking" in name and "*" not in name: return "smoker"
    if "bmi <30" in name and "*" not in name: return "bmi_low"
    if "bmi 30+" in name and "*" not in name: return "bmi_high"
    if "egfr <60" in name and "*" not in name: return "egfr_low"
    if "egfr 60+" in name and "*" not in name: return "egfr_high"
    if "anti-hypertensive" in name: return "bp_med"
    if "statin" in name: return "statin"
    if "hba1c in dm" in name: return "hba1c_dm"
    if "hba1c no dm" in name: return "hba1c_no_dm"
    return None

def build_coefs_from_text(raw_text, period, model_type):
    col_map = {
        "total_cvd": {"female": 1, "male": 2},
        "ascvd":     {"female": 3, "male": 4},
        "hf":        {"female": 5, "male": 6},
        "chd":       {"female": 7, "male": 8},
        "stroke":    {"female": 9, "male": 10}
    }
    
    # قراءة النص سطر بسطر بناءً على التابات (\t) التي نسختها من الإكسل
    for line in raw_text.strip().split('\n'):
        cols = line.split('\t')
        if len(cols) < 2: continue
        
        name = cols[0].strip()
        key = parse_row_name(name)
        if not key: continue
        
        for outcome, genders in col_map.items():
            for gender, col_idx in genders.items():
                if col_idx < len(cols):
                    val_str = cols[col_idx].strip()
                    if val_str and val_str.lower() not in ['na', 'none', '-']:
                        try:
                            COEFS[period][outcome][gender][model_type][key] = float(val_str)
                        except ValueError:
                            pass

# تفريغ البيانات المعمارية داخل القاموس عند إقلاع السيرفر فقط (يعمل بلمح البصر)
build_coefs_from_text(RAW_S12A, "10yr", "base")
build_coefs_from_text(RAW_S12C, "10yr", "hba1c")
build_coefs_from_text(RAW_S12F, "30yr", "base")
build_coefs_from_text(RAW_S12H, "30yr", "hba1c")

# =====================================================================
# المحرك الحسابي الدقيق لجمعية القلب الأمريكية
# =====================================================================
def compute_all_risks(data: PatientData) -> dict:
    use_hba1c = data.hba1c is not None
    model_type = "hba1c" if use_hba1c else "base"
    sex = data.sex.lower()
    
    tc_mmol = data.total_chol if data.total_chol < 30 else data.total_chol * 0.02586
    hdl_mmol = data.hdl if data.hdl < 10 else data.hdl * 0.02586
    
    age_c = (data.age - 55.0) / 10.0
    non_hdl_c = (tc_mmol - hdl_mmol) - 3.5
    hdl_c = (hdl_mmol - 1.3) / 0.3
    
    # المعايير المقسمة (Splines) حسب توصيات AHA
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
        # الخطر لـ 30 سنة لا يُحسب إلا للأعمار من 30 إلى 59 (توجيهات AHA الصارمة)
        if period == "30yr" and not (30 <= data.age <= 59):
            for outcome in ["total_cvd", "ascvd", "hf", "chd", "stroke"]:
                results[f"prevent_{period}_{outcome}"] = None
            continue

        for outcome in ["total_cvd", "ascvd", "hf", "chd", "stroke"]:
            key = f"prevent_{period}_{outcome}"
            c = COEFS[period][outcome][sex].get(model_type, {})
            
            # في حال عدم وجود الخطر يتم تخطيه
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

    # حواجز الحماية السريرية (Guardrails)
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
