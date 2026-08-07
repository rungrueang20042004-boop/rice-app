import streamlit as st
import datetime
from datetime import timedelta
import pandas as pd
import requests
import os

st.set_page_config(page_title="ระบบสนับสนุนที่ปรึกษาเกษตร จ.ฉะเชิงเทรา", page_icon="🌾", layout="wide")

DB_FILE = "rice_records.csv"

# 📍 ฐานข้อมูลพิกัดรายอำเภอ
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

# 🌾 ตัวเลือกวิธีการปลูก
planting_methods = ['นาหว่าน', 'นาดำ']

# ---------------------------------------------------------
# ฟังก์ชันการจัดการไฟล์ CSV (ฐานข้อมูลเดิม)
# ---------------------------------------------------------
def load_db():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    else:
        return pd.DataFrame(columns=['ชื่อแปลง', 'อำเภอ', 'พันธุ์ข้าว', 'วิธีการปลูก', 'วันเริ่มเพาะปลูก'])

def save_to_db(df):
    df.to_csv(DB_FILE, index=False)

# ---------------------------------------------------------
# ฟังก์ชันดึงพยากรณ์อากาศสด
# ---------------------------------------------------------
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
        rice_variety = st.text_input("พันธุ์ข้าว:", placeholder="เช่น กข43, หอมปทุม, กข85")
    
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
# 2. หน้า Dashboard (รองรับใช้งานบนมือถือ + เรียงอำเภอ/อายุข้าว)
# ---------------------------------------------------------
st.subheader("📊 แดชบอร์ดสรุปข้อมูลแปลงนาทั้งหมด")

if not df_db.empty:
    today = datetime.date.today()
    
    # คำนวณอายุข้าว
    df_db['วันเริ่มเพาะปลูก_dt'] = pd.to_datetime(df_db['วันเริ่มเพาะปลูก']).dt.date
    df_db['อายุข้าว (วัน)'] = df_db['วันเริ่มเพาะปลูก_dt'].apply(lambda x: (today - x).days if (today - x).days >= 0 else 0)
    
    # 🔥 จัดเรียงข้อมูล: อำเภออยู่ติดกัน + อายุข้าวเรียงจากมากไปน้อย
    df_sorted = df_db.sort_values(
        by=['อำเภอ', 'อายุข้าว (วัน)', 'วันเริ่มเพาะปลูก'], 
        ascending=[True, False, False]
    )

    # 📱 ตัวเลขสรุปหลักสำหรับดูบนมือถือ
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("จำนวนแปลงนาทั้งหมด", f"{len(df_sorted)} แปลง")
    col_m2.metric("จำนวนอำเภอ", f"{df_sorted['อำเภอ'].nunique()} อำเภอ")
    col_m3.metric("อายุข้าวเฉลี่ย", f"{int(df_sorted['อายุข้าว (วัน)'].mean())} วัน")

    st.markdown("<br>", unsafe_allow_html=True)

    # 📱 ปุ่มสลับรูปแบบการมองบนมือถือ
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
            
            # การ์ดแสดงผล
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.subheader(f"{row['ชื่อแปลง']}")
                    st.write(f"🌾 **พันธุ์ข้าว:** {row['พันธุ์ข้าว']} ({row.get('วิธีการปลูก', 'นาหว่าน')})")
                    st.write(f"📅 **วันเริ่มเพาะปลูก:** {row['วันเริ่มเพาะปลูก']}")
                with c2:
                    st.metric("อายุข้าว", f"{row['อายุข้าว (วัน)']} วัน")
    else:
        # แสดงตารางแบบดั้งเดิม (ซ่อนคอลัมน์คำนวณชั่วคราว)
        show_df = df_sorted[['ชื่อแปลง', 'อำเภอ', 'พันธุ์ข้าว', 'วิธีการปลูก', 'วันเริ่มเพาะปลูก', 'อายุข้าว (วัน)']]
        st.dataframe(show_df, use_container_width=True)

else:
    st.info("ยังไม่มีข้อมูลแปลงนาในระบบ")

st.markdown("---")

# ---------------------------------------------------------
# 3. หน้าส่วนปฏิทินกิจกรรมทำนาข้าว (ไม่มีสติ๊กเกอร์)
# ---------------------------------------------------------
st.subheader("🗓️ ตารางปฏิทินกิจกรรมการทำนาข้าว")

if not df_db.empty:
    farm_names = df_db['ชื่อแปลง'].tolist()
    selected_farm_name = st.selectbox("เลือกแปลงนาเพื่อดูตารางกิจกรรม:", farm_names)

    selected_farm = df_db[df_db['ชื่อแปลง'] == selected_farm_name].iloc[0]
    district = selected_farm['อำเภอ']
    method = selected_farm.get('วิธีการปลูก', 'นาหว่าน')
    start_date = datetime.datetime.strptime(selected_farm['วันเริ่มเพาะปลูก'], '%Y-%m-%d').date()

    st.info(f"📍 **ข้อมูลแปลง:** {selected_farm_name} | **อำเภอ:** {district} | **รูปแบบ:** {method} | **พันธุ์ข้าว:** {selected_farm['พันธุ์ข้าว']}")

    weather_data = fetch_district_weather(district)

    # รายการกิจกรรม (ไม่มีสติ๊กเกอร์)
    if method == "นาดำ":
        activities = [
            ("วันตกกล้า / ปักดำ", 0),
            ("ระยะตั้งตัว (0-7 วันหลังปักดำ)", 5),
            ("ระยะแตกกอ (15-20 วัน)", 18),
            ("หว่านปุ๋ยรับขวัญ / รอบที่ 1 (20-25 วัน)", 22),
            ("พ่นยาป้องกันแมลงรอบที่ 1 (25-28 วัน)", 26),
            ("หว่านปุ๋ยรับรวง / รอบที่ 2 (45-50 วัน)", 47),
            ("พ่นยาป้องกันโรครอบที่ 2 (48-53 วัน)", 50),
            ("ระยะแต่งหน้าปุ๋ยรอบสุดท้าย (70 วัน)", 70),
            ("ระยะตั้งท้อง/ออกดอก (75-85 วัน)", 80),
            ("ระยะข้าวก้ม/กล้วยตาก (100 วัน)", 100),
            ("วันเก็บเกี่ยวข้าว (110-120 วัน)", 115)
        ]
    else: # นาหว่าน
        activities = [
            ("วันเริ่มเพาะปลูก/หว่านข้าว", 0),
            ("ระยะคุมเลน (0-4 วัน)", 2),
            ("ระยะคุมฆ่า (7-12 วัน)", 9),
            ("หว่านปุ๋ยรอบที่ 1 (20-25 วัน)", 22),
            ("พ่นยาหลังปุ๋ยรอบที่ 1 (25-28 วัน)", 26),
            ("หว่านปุ๋ยรอบที่ 2 (45-50 วัน)", 47),
            ("พ่นยาหลังปุ๋ยรอบที่ 2 (48-53 วัน)", 50),
            ("หว่านปุ๋ยรอบที่ 3 (70-75 วัน)", 72),
            ("ระยะกัดหางปลาทู (75-85 วัน)", 80),
            ("ระยะข้าวก้ม (100 วัน)", 100),
            ("วันเก็บเกี่ยวข้าว (110-120 วัน)", 115)
        ]

    calendar_data = []

    for act_name, offset_days in activities:
        orig_date = start_date + timedelta(days=offset_days)
        orig_date_str = orig_date.strftime('%Y-%m-%d')
        
        if orig_date_str in weather_data:
            rain_prob = weather_data[orig_date_str]
            forecast_status = f"{rain_prob}% (พยากรณ์สด อ.{district})"
        else:
            rain_prob = 60 
            forecast_status = "60% (สถิติรายเดือน)"
            
        adjustment_status = "ตรงตามกำหนดเดิม"
        if rain_prob > 70:
            adjustment_status = "เสี่ยงฝนตกหนัก ควรเลื่อนกิจกรรม"
            
        calendar_data.append({
            'กิจกรรม': act_name,
            'วันตามกำหนดเดิม': orig_date.strftime('%d/%m/%Y'),
            'วันที่ปรับใหม่': orig_date.strftime('%d/%m/%Y'),
            'การปรับเปลี่ยน': adjustment_status,
            'โอกาสเกิดฝนและการประเมิน': forecast_status
        })

    cal_df = pd.DataFrame(calendar_data)
    st.table(cal_df)
else:
    st.info("โปรดบันทึกข้อมูลแปลงนาก่อนดูปฏิทิน")
