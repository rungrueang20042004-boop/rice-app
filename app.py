import streamlit as st
import datetime
from datetime import timedelta
import pandas as pd
import requests
import os

st.set_page_config(page_title="ระบบสนับสนุนที่ปรึกษาเกษตร จ.ฉะเชิงเทรา", page_icon="🌾", layout="wide")

DB_FILE = "rice_records.csv"

# 📍 1. ฐานข้อมูลพิกัดรายอำเภอ
district_coords = {
    'เมืองฉะเชิงเทรา': {'lat': 13.690, 'lon': 101.070},
    'บางคล้า': {'lat': 13.723, 'lon': 101.208},
    'บางน้ำเปรี้ยว': {'lat': 13.847, 'lon': 100.970},
    'บางปะกง': {'lat': 13.548, 'lon': 100.993},
    'บ้านโพธิ์': {'lat': 13.599, 'lon': 101.077},
    'พนมสารคาม': {'lat': 13.745, 'lon': 101.346},
    'ราชสาส์น': {'lat': 13.780, 'lon': 101.288},
    'สนามชัยเขต': {'lat': 13.658, 'lon': 101.438},
    'แปลงยาว': {'lat': 13.583, 'lon': 101.283},
    'ท่าตะเกียบ': {'lat': 13.417, 'lon': 101.678},
    'คลองเขื่อน': {'lat': 13.792, 'lon': 101.162}
}

# 🌾 2. แคตตาล็อกพันธุ์ข้าว
rice_catalog = {
    'เบอร์ 5451': 'พันธุ์เบา',
    'กข41': 'พันธุ์เบา',
    'กข107': 'พันธุ์เบา',
    'กข91': 'พันธุ์หนัก',
    'กข85': 'พันธุ์หนัก',
    'กข43': 'พันธุ์เบา',
    'หอมปทุม': 'พันธุ์ปานกลาง',
    'พิษณุโลก 2': 'พันธุ์ปานกลาง'
}

# 🌾 3. ตัวเลือกวิธีการปลูก
planting_methods = ['นาหว่านน้ำตม', 'นาหว่านแห้ง / หว่านสำรวย', 'ปักดำ / นาดำ']

# ☀️ 4. สถิติภูมิอากาศฉะเชิงเทรา (เปอร์เซ็นต์ฝนรายเดือน)
chachoengsao_climatology = {
    1: 10, 2: 15, 3: 25, 4: 35, 5: 60, 6: 65,
    7: 70, 8: 75, 9: 85, 10: 70, 11: 30, 12: 10
}

# 📋 5. กฎกิจกรรมตามประเภทพันธุ์ข้าว
activity_rules = {
    'นาหว่าน': [
        {"day": 0, "activity": "วันเริ่มเพาะปลูก/หว่านข้าว", "is_spray": False},
        {"day": 2, "activity": "ระยะคุมเลน (0-4 วัน)", "is_spray": True},
        {"day": 9, "activity": "ระยะคุมฆ่า (7-12 วัน)", "is_spray": True},
        {"day": 22, "activity": "หว่านปุ๋ยรอบที่ 1 (20-25 วัน)", "is_spray": False},
        {"day": 26, "activity": "พ่นยาหลังปุ๋ยรอบที่ 1 (25-28 วัน)", "is_spray": True},
        {"day": 47, "activity": "หว่านปุ๋ยรอบที่ 2 (45-50 วัน)", "is_spray": False},
        {"day": 50, "activity": "พ่นยาหลังปุ๋ยรอบที่ 2 (48-53 วัน)", "is_spray": True},
        {"day": 72, "activity": "หว่านปุ๋ยรอบที่ 3 (70-75 วัน)", "is_spray": False},
        {"day": 80, "activity": "ระยะกัดหางปลาทู (75-85 วัน)", "is_spray": False},
        {"day": 100, "activity": "ระยะข้าวก้ม (100 วัน)", "is_spray": False},
        {"day": 115, "activity": "วันเก็บเกี่ยวข้าว (110-120 วัน)", "is_spray": False}
    ],
    'นาดำ': [
        {"day": 0, "activity": "วันตกกล้า / ปักดำ", "is_spray": False},
        {"day": 5, "activity": "ระยะตั้งตัว (0-7 วันหลังปักดำ)", "is_spray": False},
        {"day": 18, "activity": "ระยะแตกกอ (15-20 วัน)", "is_spray": False},
        {"day": 22, "activity": "หว่านปุ๋ยรับขวัญ / รอบที่ 1 (20-25 วัน)", "is_spray": False},
        {"day": 26, "activity": "พ่นยาป้องกันแมลงรอบที่ 1 (25-28 วัน)", "is_spray": True},
        {"day": 47, "activity": "หว่านปุ๋ยรับรวง / รอบที่ 2 (45-50 วัน)", "is_spray": False},
        {"day": 50, "activity": "พ่นยาป้องกันโรครอบที่ 2 (48-53 วัน)", "is_spray": True},
        {"day": 70, "activity": "ระยะแต่งหน้าปุ๋ยรอบสุดท้าย (70 วัน)", "is_spray": False},
        {"day": 80, "activity": "ระยะตั้งท้อง/ออกดอก (75-85 วัน)", "is_spray": False},
        {"day": 100, "activity": "ระยะข้าวก้ม/กล้วยตาก (100 วัน)", "is_spray": False},
        {"day": 115, "activity": "วันเก็บเกี่ยวข้าว (110-120 วัน)", "is_spray": False}
    ]
}

# ---------------------------------------------------------
# ฟังก์ชันการจัดการไฟล์และระบบคำนวณ
# ---------------------------------------------------------
def load_db():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    else:
        return pd.DataFrame(columns=['ชื่อแปลง', 'อำเภอ', 'พันธุ์ข้าว', 'วิธีการปลูก', 'วันเริ่มเพาะปลูก'])

def save_to_db(df):
    df.to_csv(DB_FILE, index=False)

def fetch_district_weather(district_name):
    coords = district_coords.get(district_name, {'lat': 13.690, 'lon': 101.070})
    url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&daily=precipitation_probability_max&forecast_days=16&timezone=Asia%2FBangkok"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            res = response.json()
            if 'daily' in res and 'precipitation_probability_max' in res['daily']:
                return {res['daily']['time'][i]: res['daily']['precipitation_probability_max'][i] for i in range(len(res['daily']['time']))}
        return {}
    except Exception:
        return {}

def highlight_rows(row):
    if "เสี่ยงฝน" in str(row['การปรับเปลี่ยน']):
        return ['background-color: #ffcccc; color: #990000; font-weight: bold;'] * len(row)
    elif "เลื่อน" in str(row['การปรับเปลี่ยน']):
        return ['background-color: #fff3cd; color: #856404;'] * len(row)
    return [''] * len(row)

# ---------------------------------------------------------
# 1. ส่วนลงทะเบียนข้อมูลแปลงนาใหม่ (Input)
# ---------------------------------------------------------
st.title("🌾 ระบบสนับสนุนการตัดสินใจในการทำนาข้าว")
st.subheader("📝 ลงทะเบียนข้อมูลแปลงนาใหม่")

df_db = load_db()

with st.form("add_farm_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        farm_name = st.text_input("ชื่อแปลงนา:", placeholder="เช่น แปลงนาพี่สมชาย 1")
        district = st.selectbox("อำเภอ:", list(district_coords.keys()))
        
        # เลือกพันธุ์ข้าวจาก Catalog หรือพิมพ์เพิ่ม
        rice_options = list(rice_catalog.keys()) + ["อื่นๆ"]
        selected_rice = st.selectbox("พันธุ์ข้าว:", rice_options)
        if selected_rice == "อื่นๆ":
            rice_variety = st.text_input("ระบุพันธุ์ข้าวอื่นๆ:")
        else:
            rice_variety = selected_rice
            
    with col2:
        planting_method = st.radio(
            "วิธีการปลูกข้าว:",
            options=planting_methods,
            horizontal=True
        )
        plant_date = st.date_input("วันเริ่มเพาะปลูก/วันหว่าน/วันปักดำ:", datetime.date.today())
        
    submit_button = st.form_submit_button("➕ บันทึกข้อมูลแปลงนา", use_container_width=True)

if submit_button:
    if farm_name and rice_variety:
        new_row = pd.DataFrame([{
            'ชื่อแปลง': farm_name,
            'อำเภอ': district,
            'พันธุ์ข้าว': rice_variety,
            'วิธีการปลูก': planting_method,
            'วันเริ่มเพาะปลูก': plant_date.strftime('%Y-%m-%d')
        }])
        df_db = pd.concat([df_db, new_row], ignore_index=True)
        save_to_db(df_db)
        st.success(f"บันทึกข้อมูล {farm_name} ({planting_method}) เรียบร้อยแล้ว!")
        st.rerun()
    else:
        st.warning("กรุณากรอกข้อมูลให้ครบถ้วน")

st.markdown("---")

# ---------------------------------------------------------
# 2. หน้า Dashboard (รองรับใช้งานบนมือถือ + ไฮไลต์สี + เรียงอำเภอ)
# ---------------------------------------------------------
st.subheader("📊 แดชบอร์ดสรุปข้อมูลแปลงนาทั้งหมด")

if not df_db.empty:
    today = datetime.date.today()
    
    # คำนวณอายุข้าว
    df_db['วันเริ่มเพาะปลูก_dt'] = pd.to_datetime(df_db['วันเริ่มเพาะปลูก']).dt.date
    df_db['อายุข้าว (วัน)'] = df_db['วันเริ่มเพาะปลูก_dt'].apply(lambda x: (today - x).days if (today - x).days >= 0 else 0)
    
    # จัดเรียงข้อมูล: อำเภออยู่ติดกัน + อายุข้าวเรียงจากมากไปน้อย
    df_sorted = df_db.sort_values(
        by=['อำเภอ', 'อายุข้าว (วัน)', 'วันเริ่มเพาะปลูก'], 
        ascending=[True, False, False]
    )

    # ตัวเลขสรุปหลักสำหรับดูบนมือถือ
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("จำนวนแปลงนาทั้งหมด", f"{len(df_sorted)} แปลง")
    col_m2.metric("จำนวนอำเภอ", f"{df_sorted['อำเภอ'].nunique()} อำเภอ")
    col_m3.metric("อายุข้าวเฉลี่ย", f"{int(df_sorted['อายุข้าว (วัน)'].mean())} วัน")

    st.markdown("<br>", unsafe_allow_html=True)

    # ปุ่มสลับรูปแบบการมองบนมือถือ
    view_mode = st.radio(
        "📱 เลือกรูปแบบการแสดงผล Dashboard:",
        options=["🎴 แสดงแบบการ์ด (อ่านง่ายบนมือถือ)", "📊 แสดงแบบตาราง"],
        horizontal=True
    )

    if "การ์ด" in view_mode:
        current_district = ""
        for _, row in df_sorted.iterrows():
            if row['อำเภอ'] != current_district:
                current_district = row['อำเภอ']
                st.markdown(f"### 📍 อ. {current_district}")
            
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.subheader(f"{row['ชื่อแปลง']}")
                    method_str = row.get('วิธีการปลูก', 'นาหว่านน้ำตม')
                    st.write(f"🌾 **พันธุ์ข้าว:** {row['พันธุ์ข้าว']} ({method_str})")
                    st.write(f"📅 **วันเริ่มเพาะปลูก:** {row['วันเริ่มเพาะปลูก']}")
                with c2:
                    st.metric("อายุข้าว", f"{row['อายุข้าว (วัน)']} วัน")
    else:
        show_df = df_sorted[['ชื่อแปลง', 'อำเภอ', 'พันธุ์ข้าว', 'วิธีการปลูก', 'วันเริ่มเพาะปลูก', 'อายุข้าว (วัน)']]
        st.dataframe(show_df, use_container_width=True)

else:
    st.info("ยังไม่มีข้อมูลแปลงนาในระบบ")

st.markdown("---")

# ---------------------------------------------------------
# 3. หน้าส่วนปฏิทินกิจกรรมทำนาข้าว (ตาราง + การแจ้งเตือนสภาพอากาศ)
# ---------------------------------------------------------
st.subheader("🗓️ ตารางปฏิทินกิจกรรมการทำนาข้าว")

if not df_db.empty:
    farm_names = df_db['ชื่อแปลง'].tolist()
    selected_farm_name = st.selectbox("เลือกแปลงนาเพื่อดูตารางกิจกรรม:", farm_names)

    selected_farm = df_db[df_db['ชื่อแปลง'] == selected_farm_name].iloc[0]
    district = selected_farm['อำเภอ']
    method = selected_farm.get('วิธีการปลูก', 'นาหว่านน้ำตม')
    start_date = datetime.datetime.strptime(selected_farm['วันเริ่มเพาะปลูก'], '%Y-%m-%d').date()

    st.info(f"📍 **ข้อมูลแปลง:** {selected_farm_name} | **อำเภอ:** {district} | **รูปแบบ:** {method} | **พันธุ์ข้าว:** {selected_farm['พันธุ์ข้าว']}")

    weather_data = fetch_district_weather(district)

    # เลือกชุดกิจกรรมตามประเภทการปลูก (นาดำ / นาหว่าน)
    rules_key = 'นาดำ' if 'ปักดำ' in method or 'นาดำ' in method else 'นาหว่าน'
    selected_rules = activity_rules[rules_key]

    calendar_data = []

    for rule in selected_rules:
        act_name = rule['activity']
        offset_days = rule['day']
        is_spray = rule['is_spray']
        
        orig_date = start_date + timedelta(days=offset_days)
        orig_date_str = orig_date.strftime('%Y-%m-%d')
        
        # เช็คพยากรณ์อากาศสด หรือใช้สถิติรายเดือน
        if orig_date_str in weather_data:
            rain_prob = weather_data[orig_date_str]
            forecast_status = f"{rain_prob}% (พยากรณ์สด อ.{district})"
        else:
            month_num = orig_date.month
            rain_prob = chachoengsao_climatology.get(month_num, 50)
            forecast_status = f"{rain_prob}% (สถิติรายเดือน)"
            
        adjustment_status = "ตรงตามกำหนดเดิม"
        adjusted_date_str = orig_date.strftime('%d/%m/%Y')
        
        # เงื่อนไขแจ้งเตือนเมื่อฉีดพ่นสารแล้วเสี่ยงฝนตก
        if is_spray and rain_prob > 60:
            adjustment_status = "⚠️ เสี่ยงฝนตกหนัก ควรเลื่อนกิจกรรมฉีดพ่น"
            # คำนวณวันใหม่ถัดไป 2 วัน
            adj_date = orig_date + timedelta(days=2)
            adjusted_date_str = adj_date.strftime('%d/%m/%Y')
            
        calendar_data.append({
            'กิจกรรม': act_name,
            'วันตามกำหนดเดิม': orig_date.strftime('%d/%m/%Y'),
            'วันที่ปรับใหม่': adjusted_date_str,
            'การปรับเปลี่ยน': adjustment_status,
            'โอกาสเกิดฝนและการประเมิน': forecast_status
        })

    cal_df = pd.DataFrame(calendar_data)
    
    # แสดงผลตารางพร้อมไฮไลต์สี
    st.dataframe(cal_df.style.apply(highlight_rows, axis=1), use_container_width=True)
else:
    st.info("โปรดบันทึกข้อมูลแปลงนาก่อนดูปฏิทิน")
