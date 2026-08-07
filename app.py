import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบแนะนำการทำนาข้าว", page_icon="🌾", layout="wide")

st.title("🌾 ระบบสนับสนุนการตัดสินใจในการทำนาข้าว")
st.caption("ระบบแนะนำการเพาะปลูกและจัดปฏิทินกิจกรรมการทำนาข้าวเรียลไทม์ (ฉะเชิงเทรา)")

# ---------------------------------------------------------
# 1. ข้อมูลพิกัดอำเภอในจังหวัดฉะเชิงเทรา
# ---------------------------------------------------------
district_coords = {
    'เมืองฉะเชิงเทรา': {'lat': 13.690, 'lon': 101.070},
    'บางคล้า': {'lat': 13.721, 'lon': 101.208},
    'บางน้ำเปรี้ยว': {'lat': 13.845, 'lon': 100.970},
    'บางปะกง': {'lat': 13.543, 'lon': 100.993},
    'บ้านโพธิ์': {'lat': 13.597, 'lon': 101.076},
    'พนมสารคาม': {'lat': 13.745, 'lon': 101.347},
    'ราชสาส์น': {'lat': 13.782, 'lon': 101.282},
    'สนามชัยเขต': {'lat': 13.658, 'lon': 101.438},
    'แปลงยาว': {'lat': 13.582, 'lon': 101.282},
    'ท่าตะเกียบ': {'lat': 13.435, 'lon': 101.670},
    'คลองเขื่อน': {'lat': 13.793, 'lon': 101.162}
}

# ---------------------------------------------------------
# 2. ฟังก์ชันดึงข้อมูลพยากรณ์อากาศสด (16 วัน)
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
# 3. จำลองฐานข้อมูลแปลงนา (เริ่มต้น)
# ---------------------------------------------------------
if 'farms' not in st.session_state:
    st.session_state.farms = [
        {'แปลง': 'แปลงที่ 1', 'อำเภอ': 'บางน้ำเปรี้ยว', 'วิธีการปลูก': 'นาหว่าน', 'วันเริ่มเพาะปลูก': '2026-07-01', 'พันธุ์ข้าว': 'กข43'},
        {'แปลง': 'แปลงที่ 2', 'อำเภอ': 'บางน้ำเปรี้ยว', 'วิธีการปลูก': 'นาดำ', 'วันเริ่มเพาะปลูก': '2026-06-15', 'พันธุ์ข้าว': 'หอมปทุม'},
        {'แปลง': 'แปลงที่ 3', 'อำเภอ': 'เมืองฉะเชิงเทรา', 'วิธีการปลูก': 'นาหว่าน', 'วันเริ่มเพาะปลูก': '2026-07-10', 'พันธุ์ข้าว': 'กข85'},
        {'แปลง': 'แปลงที่ 4', 'อำเภอ': 'บางคล้า', 'วิธีการปลูก': 'นาดำ', 'วันเริ่มเพาะปลูก': '2026-05-20', 'พันธุ์ข้าว': 'พิษณุโลก 2'},
        {'แปลง': 'แปลงที่ 5', 'อำเภอ': 'เมืองฉะเชิงเทรา', 'วิธีการปลูก': 'นาหว่าน', 'วันเริ่มเพาะปลูก': '2026-06-01', 'พันธุ์ข้าว': 'กข43'},
    ]

# ---------------------------------------------------------
# 4. ฟอร์มลงทะเบียนข้อมูลแปลงนาใหม่ (Input)
# ---------------------------------------------------------
st.subheader("📝 ลงทะเบียนข้อมูลแปลงนาใหม่")

with st.form("add_farm_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        farm_name = st.text_input("ชื่อแปลงนา:", placeholder="เช่น แปลงนาพี่สมชาย 1")
        district = st.selectbox("อำเภอ:", list(district_coords.keys()))
        rice_variety = st.text_input("พันธุ์ข้าว:", placeholder="เช่น กข43, หอมปทุม, กข85")
    
    with col2:
        planting_method = st.radio(
            "วิธีการปลูกข้าว:",
            options=["นาหว่าน", "นาดำ"],
            horizontal=True
        )
        plant_date = st.date_input("วันเริ่มเพาะปลูก/วันหว่าน/วันปักดำ:")
        
    submit_button = st.form_submit_button("➕ บันทึกข้อมูลแปลงนา", use_container_width=True)

if submit_button:
    if farm_name and rice_variety:
        st.session_state.farms.append({
            'แปลง': farm_name,
            'อำเภอ': district,
            'วิธีการปลูก': planting_method,
            'วันเริ่มเพาะปลูก': plant_date.strftime('%Y-%m-%d'),
            'พันธุ์ข้าว': rice_variety
        })
        st.success(f"บันทึกข้อมูล {farm_name} ({planting_method}) เรียบร้อยแล้ว!")
        st.rerun()
    else:
        st.warning("กรุณากรอกข้อมูลให้ครบถ้วน")

st.markdown("---")

# ---------------------------------------------------------
# 5. หน้า Dashboard (แดชบอร์ดสรุปข้อมูล)
# ---------------------------------------------------------
st.subheader("📊 แดชบอร์ดสรุปข้อมูลแปลงนาทั้งหมด")

if st.session_state.farms:
    data_list = []
    today = datetime.now().date()
    
    for farm in st.session_state.farms:
        start_date = datetime.strptime(farm['วันเริ่มเพาะปลูก'], '%Y-%m-%d').date()
        age_days = (today - start_date).days
        
        data_list.append({
            'ชื่อแปลง': farm['แปลง'],
            'อำเภอ': farm['อำเภอ'],
            'วิธีการปลูก': farm.get('วิธีการปลูก', 'นาหว่าน'),
            'พันธุ์ข้าว': farm['พันธุ์ข้าว'],
            'วันเริ่มเพาะปลูก': farm['วันเริ่มเพาะปลูก'],
            'อายุข้าว (วัน)': age_days if age_days >= 0 else 0
        })
    
    df = pd.DataFrame(data_list)
    
    df_sorted = df.sort_values(
        by=['อำเภอ', 'อายุข้าว (วัน)', 'วันเริ่มเพาะปลูก'], 
        ascending=[True, False, False]
    )
    
    st.dataframe(df_sorted, use_container_width=True)

else:
    st.info("ยังไม่มีข้อมูลแปลงนาในระบบ")

st.markdown("---")

# ---------------------------------------------------------
# 6. หน้าส่วนปฏิทินกิจกรรมทำนาข้าว
# ---------------------------------------------------------
st.subheader("🗓️ ตารางปฏิทินกิจกรรมการทำนาข้าว")

farm_names = [f['แปลง'] for f in st.session_state.farms]
selected_farm_name = st.selectbox("เลือกแปลงนาเพื่อดูตารางกิจกรรม:", farm_names)

selected_farm = next(f for f in st.session_state.farms if f['แปลง'] == selected_farm_name)
district = selected_farm['อำเภอ']
method = selected_farm.get('วิธีการปลูก', 'นาหว่าน')
start_date_str = selected_farm['วันเริ่มเพาะปลูก']
start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

st.info(f"📍 **ข้อมูลแปลง:** {selected_farm_name} | **อำเภอ:** {district} | **รูปแบบ:** {method} | **พันธุ์ข้าว:** {selected_farm['พันธุ์ข้าว']}")

weather_data = fetch_district_weather(district)

# 🚫 เอาสติ๊กเกอร์ออกจากรายการกิจกรรมทั้งหมดแล้ว
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
