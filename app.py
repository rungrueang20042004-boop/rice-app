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

rice_catalog = {
    'เบอร์ 5451': 'พันธุ์เบา',
    'กข41': 'พันธุ์เบา',
    'กข107': 'พันธุ์เบา',
    'กข91': 'พันธุ์หนัก',
    'กข85': 'พันธุ์หนัก'
}
planting_methods = ['หว่านน้ำตม', 'หว่านแห้ง / หว่านสำรวย', 'ปักดำ / ดำนา']

activity_rules = {
    'พันธุ์เบา': [
        {"day": 0, "activity": "🌾 วันเริ่มเพาะปลูก/หว่านข้าว", "is_spray": False},
        {"day": 2, "activity": "💧 ระยะคุมเลน (0-4 วัน)", "is_spray": True},
        {"day": 9, "activity": "🌿 ระยะคุมฆ่า (7-12 วัน)", "is_spray": True},
        {"day": 16, "activity": "🌱 หว่านปุ๋ยรอบที่ 1 (15-18 วัน)", "is_spray": False},
        {"day": 21, "activity": "🐛 พ่นยาหลังปุ๋ยรอบที่ 1 (20-23 วัน)", "is_spray": True},
        {"day": 32, "activity": "🌾 หว่านปุ๋ยรอบที่ 2 (30-35 วัน)", "is_spray": False},
        {"day": 35, "activity": "🐛 พ่นยาหลังปุ๋ยรอบที่ 2 (33-38 วัน)", "is_spray": True},
        {"day": 47, "activity": "🌾 หว่านปุ๋ยรอบที่ 3 (45-50 วัน)", "is_spray": False},
        {"day": 52, "activity": "🌸 ระยะกัดหางปลาทู (50-55 วัน)", "is_spray": False},
        {"day": 70, "activity": "🌾 ระยะข้าวก้ม (70 วัน)", "is_spray": False},
        {"day": 95, "activity": "🚜 วันเก็บเกี่ยวโดยประมาณ", "is_spray": False}
    ],
    'พันธุ์หนัก': [
        {"day": 0, "activity": "🌾 วันเริ่มเพาะปลูก/หว่านข้าว", "is_spray": False},
        {"day": 2, "activity": "💧 ระยะคุมเลน (0-4 วัน)", "is_spray": True},
        {"day": 9, "activity": "🌿 ระยะคุมฆ่า (7-12 วัน)", "is_spray": True},
        {"day": 22, "activity": "🌱 หว่านปุ๋ยรอบที่ 1 (20-25 วัน)", "is_spray": False},
        {"day": 26, "activity": "🐛 พ่นยาหลังปุ๋ยรอบที่ 1 (25-28 วัน)", "is_spray": True},
        {"day": 47, "activity": "🌾 หว่านปุ๋ยรอบที่ 2 (45-50 วัน)", "is_spray": False},
        {"day": 50, "activity": "🐛 พ่นยาหลังปุ๋ยรอบที่ 2 (48-53 วัน)", "is_spray": True},
        {"day": 72, "activity": "🌾 หว่านปุ๋ยรอบที่ 3 (70-75 วัน)", "is_spray": False},
        {"day": 80, "activity": "🌸 ระยะกัดหางปลาทู (75-85 วัน)", "is_spray": False},
        {"day": 100, "activity": "🌾 ระยะข้าวก้ม (100 วัน)", "is_spray": False},
        {"day": 120, "activity": "🚜 วันเก็บเกี่ยวโดยประมาณ", "is_spray": False}
    ]
}

chachoengsao_climatology = {1:10, 2:15, 3:25, 4:40, 5:60, 6:55, 7:60, 8:65, 9:75, 10:60, 11:30, 12:10}

def fetch_district_weather(district_name):
    coords = district_coords.get(district_name, {'lat': 13.690, 'lon': 101.070})
    url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&daily=precipitation_probability_max&forecast_days=14&timezone=Asia%2FBangkok"
    try:
        res = requests.get(url, timeout=5).json()
        return {res['daily']['time'][i]: res['daily']['precipitation_probability_max'][i] for i in range(len(res['daily']['time']))}
    except:
        return {}

def save_to_db(farmer, district, field, rice, method, date_start):
    new_data = pd.DataFrame([{
        "ชื่อเกษตรกร": farmer,
        "อำเภอ": district,
        "ชื่อแปลง/ที่ตั้ง": field,
        "สายพันธุ์ข้าว": rice,
        "วิธีการปลูก": method,
        "วันที่เริ่มเพาะปลูก": date_start.strftime("%Y-%m-%d"),
        "วันบันทึกข้อมูล": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "สถานะ/ปัญหาที่พบ": "ปกติ",
        "จำนวนวันที่ปรับเลื่อนสะสม": 0,
        "กิจกรรมล่าสุดที่เลื่อน": "ไม่มี",
        "วันที่อัปเดตล่าสุด": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }])
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        if not ((df['ชื่อเกษตรกร'] == farmer) & (df['ชื่อแปลง/ที่ตั้ง'] == field) & (df['วันที่เริ่มเพาะปลูก'] == date_start.strftime("%Y-%m-%d"))).any():
            df = pd.concat([df, new_data], ignore_index=True)
            df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
    else:
        new_data.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

def update_field_status(record_idx, new_status, delayed_act_name="ไม่มี", extra_shift_days=0):
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        df.at[record_idx, "สถานะ/ปัญหาที่พบ"] = new_status
        
        raw_shift = df.at[record_idx, "จำนวนวันที่ปรับเลื่อนสะสม"] if "จำนวนวันที่ปรับเลื่อนสะสม" in df.columns else 0
        current_shift = 0 if pd.isna(raw_shift) else int(raw_shift)
        
        df.at[record_idx, "จำนวนวันที่ปรับเลื่อนสะสม"] = current_shift + int(extra_shift_days)
        if extra_shift_days != 0:
            df.at[record_idx, "กิจกรรมล่าสุดที่เลื่อน"] = delayed_act_name
        df.at[record_idx, "วันที่อัปเดตล่าสุด"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
        return True
    return False

def delete_field_record(record_idx):
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        df = df.drop(index=record_idx).reset_index(drop=True)
        df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
        return True
    return False

def load_db():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        cols_to_check = {
            "อำเภอ": "เมืองฉะเชิงเทรา",
            "สถานะ/ปัญหาที่พบ": "ปกติ",
            "จำนวนวันที่ปรับเลื่อนสะสม": 0,
            "กิจกรรมล่าสุดที่เลื่อน": "ไม่มี",
            "วันที่อัปเดตล่าสุด": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "วันบันทึกข้อมูล": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        for col, default_val in cols_to_check.items():
            if col not in df.columns:
                df[col] = default_val
            df[col] = df[col].fillna(default_val)
            
        df["จำนวนวันที่ปรับเลื่อนสะสม"] = df["จำนวนวันที่ปรับเลื่อนสะสม"].astype(int)
        return df
    return pd.DataFrame(columns=["ชื่อเกษตรกร", "อำเภอ", "ชื่อแปลง/ที่ตั้ง", "สายพันธุ์ข้าว", "วิธีการปลูก", "วันที่เริ่มเพาะปลูก", "วันบันทึกข้อมูล", "สถานะ/ปัญหาที่พบ", "จำนวนวันที่ปรับเลื่อนสะสม", "กิจกรรมล่าสุดที่เลื่อน", "วันที่อัปเดตล่าสุด"])

# 🎯 คำนวณปฏิทิน
def get_rice_schedule_advanced(sow_date, rice_name, district_name="เมืองฉะเชิงเทรา", base_accum_shift=0, delayed_act_name="ไม่มี", new_delay_days=0):
    rice_type = rice_catalog[rice_name]
    rules = activity_rules[rice_type]
    weather_forecast = fetch_district_weather(district_name)
    schedule = []
    
    # ค้นหาตำแหน่งของกิจกรรมที่เลื่อน
    all_act_names = [r['activity'] for r in rules]
    target_idx = all_act_names.index(delayed_act_name) if delayed_act_name in all_act_names else -1

    for idx, rule in enumerate(rules):
        original_act_date = sow_date + timedelta(days=rule['day'])
        
        # กิจกรรมตั้งแต่จุดที่เลื่อนเป็นต้นไปจะโดนเลื่อนวัน
        if target_idx != -1 and idx >= target_idx:
            active_shift = base_accum_shift + new_delay_days
            is_shifted = True
        else:
            active_shift = 0 if target_idx != -1 else base_accum_shift
            is_shifted = (active_shift > 0)

        act_date = sow_date + timedelta(days=rule['day'] + active_shift)
        date_str = act_date.strftime("%Y-%m-%d")
        
        shift_note = "ตรงตามกำหนดเดิม" if active_shift == 0 else f"+{active_shift} วัน"
        if is_shifted and active_shift > 0:
            shift_note += f" (เริ่มเลื่อนที่: {delayed_act_name if target_idx != -1 else 'ขยับวัน'})"

        # เช็คฝน
        if date_str in weather_forecast:
            rain_chance = weather_forecast[date_str]
            if rule['is_spray'] and rain_chance > 60:
                act_date = act_date + timedelta(days=2)
                active_shift += 2
                shift_note = f"+{active_shift} วัน (เลื่อนหลบฝน +2 วัน)"
                status_text = f"⚡ ฝนสด {rain_chance}% ({district_name}) ⚠️ ฝนตกหนัก เลื่อนหลบฝน"
                schedule.append({
                    "กิจกรรม": rule['activity'],
                    "วันตามกำหนดเดิม": original_act_date.strftime("%d/%m/%Y"),
                    "วันที่ปรับใหม่": act_date.strftime("%d/%m/%Y"),
                    "การปรับเปลี่ยน": shift_note,
                    "โอกาสเกิดฝนและการประเมิน": status_text,
                    "_danger": True,
                    "_shifted": is_shifted or active_shift > 0
                })
                continue
            else:
                status_text = f"⚡ {rain_chance}% [พยากรณ์สด อ.{district_name}]"
        else:
            rain_chance = chachoengsao_climatology[act_date.month]
            status_text = f"📊 {rain_chance}% (สถิติรายเดือน)"
            if rule['is_spray'] and rain_chance > 60:
                status_text += " ⚠️ ช่วงนี้ฝนชุก"
                schedule.append({
                    "กิจกรรม": rule['activity'],
                    "วันตามกำหนดเดิม": original_act_date.strftime("%d/%m/%Y"),
                    "วันที่ปรับใหม่": act_date.strftime("%d/%m/%Y"),
                    "การปรับเปลี่ยน": shift_note,
                    "โอกาสเกิดฝนและการประเมิน": status_text,
                    "_danger": True,
                    "_shifted": is_shifted or active_shift > 0
                })
                continue
                
        schedule.append({
            "กิจกรรม": rule['activity'],
            "วันตามกำหนดเดิม": original_act_date.strftime("%d/%m/%Y"),
            "วันที่ปรับใหม่": act_date.strftime("%d/%m/%Y"),
            "การปรับเปลี่ยน": shift_note,
            "โอกาสเกิดฝนและการประเมิน": status_text,
            "_danger": False,
            "_shifted": is_shifted or active_shift > 0
        })
    return pd.DataFrame(schedule)

def is_alert_status(status_val):
    status_str = str(status_val).strip()
    return status_str != "" and "ปกติ" not in status_str and "None" not in status_str and status_str.lower() != "nan"

def calculate_rice_age(sow_date_str):
    try:
        sow_date = datetime.datetime.strptime(str(sow_date_str), "%Y-%m-%d").date()
        today = datetime.date.today()
        age_days = (today - sow_date).days
        if age_days < 0:
            return f"ยังไม่ถึงวันปลูก (อีก {-age_days} วัน)"
        return f"{age_days} วัน"
    except:
        return "-"

# ─── หน้าหลักแอปพลิเคชัน ───
st.markdown("<h1 style='text-align: center; color: #1e7e34;'>🌾 ระบบสนับสนุนการตัดสินใจและวางแผนตรวจเยี่ยมแปลงนา จ.ฉะเชิงเทรา</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555;'>เครื่องมือส่วนกลางสำหรับเจ้าหน้าที่และที่ปรึกษาทางการเกษตรประจำแผนก</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📝 ขึ้นทะเบียนแปลงในความดูแล", "⚠️ อัปเดตสถานะ/ปรับเลื่อนวันทำกิจกรรม", "📊 แดชบอร์ดวางแผนตรวจเยี่ยม"])

# --- TAB 1 ---
with tab1:
    st.subheader("บันทึกข้อมูลแปลงนาเกษตรกรรายใหม่")
    col_a, col_b = st.columns(2)
    with col_a:
        farmer_name = st.text_input("👤 ชื่อเกษตรกรผู้รับคำปรึกษา:", placeholder="ตัวอย่าง: นายสมศักดิ์ รักดี")
        selected_district = st.selectbox("📍 อำเภอ (จ.ฉะเชิงเทรา):", list(district_coords.keys()))
        rice_name = st.selectbox("สายพันธุ์ข้าวในแปลง:", list(rice_catalog.keys()))
    with col_b:
        field_name = st.text_input("📍 ชื่อแปลง / ตำบล / หมู่บ้าน:", placeholder="ตัวอย่าง: แปลงบางขนาก A (หมู่ 3)")
        planting_method = st.selectbox("🚜 วิธีการปลูกข้าว:", planting_methods)
        sow_date = st.date_input("วันที่เริ่มเพาะปลูก (วันหว่าน):", datetime.date.today())
    
    if st.button("📅 คำนวณปฏิทินและบันทึกข้อมูลลงระบบ", type="primary"):
        if not farmer_name or not field_name:
            st.error("⚠️ กรุณากรอก 'ชื่อเกษตรกร' และ 'ชื่อแปลง' ก่อนกดบันทึก")
        else:
            save_to_db(farmer_name, selected_district, field_name, rice_name, planting_method, sow_date)
            st.success(f"💾 บันทึกและขึ้นทะเบียนแปลงในระบบเรียบร้อย! (อ.{selected_district})")
            
            df = get_rice_schedule_advanced(sow_date, rice_name, district_name=selected_district)
            st.markdown(f"### 📋 ปฏิทินแนะนำสำหรับผู้ใช้: {farmer_name} | {field_name} (อ.{selected_district})")
            
            show_df = df.drop(columns=['_danger', '_shifted'])
            def highlight_rows(row):
                return ['background-color: #ffebee; font-weight: bold' if df.loc[row.name, '_danger'] else '' for _ in row]
            st.dataframe(show_df.style.apply(highlight_rows, axis=1), use_container_width=True, hide_index=True)

# โหลดข้อมูล
history_df = load_db()

# --- TAB 2 ---
with tab2:
    st.subheader("⚠️ บันทึกผลการตรวจแปลง และ ปรับเลื่อนวันทำกิจกรรม")
    if history_df.empty:
        st.info("ℹ️ ยังไม่มีข้อมูลแปลงในระบบ กรุณาขึ้นทะเบียนแปลงในแท็บแรกก่อน")
    else:
        record_options = {idx: f"{row['ชื่อเกษตรกร']} - อ.{row['อำเภอ']} - {row['ชื่อแปลง/ที่ตั้ง']} (ข้าว: {row['สายพันธุ์ข้าว']})" for idx, row in history_df.iterrows()}
        selected_idx = st.selectbox("เลือกแปลงนาที่ต้องการอัปเดตข้อมูล:", options=list(record_options.keys()), format_func=lambda x: record_options[x], key="tab2_select")
        
        target_field = history_df.iloc[selected_idx]
        current_status = target_field["สถานะ/ปัญหาที่พบ"]
        raw_shift_val = target_field["จำนวนวันที่ปรับเลื่อนสะสม"]
        current_shift = 0 if pd.isna(raw_shift_val) else int(raw_shift_val)
        last_delayed_act = target_field.get("กิจกรรมล่าสุดที่เลื่อน", "ไม่มี")
        
        st.info(f"📌 **สถานะล่าสุด:** {current_status} | ⏱️ **วันเลื่อนสะสม:** +{current_shift} วัน (กิจกรรมล่าช้าล่าสุด: `{last_delayed_act}`)")
        
        try:
            sow_d = datetime.datetime.strptime(str(target_field["วันที่เริ่มเพาะปลูก"]), "%Y-%m-%d").date()
        except:
            sow_d = datetime.date.today()
            
        rice_type = rice_catalog[target_field["สายพันธุ์ข้าว"]]
        available_activities = [item['activity'] for item in activity_rules[rice_type]]
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            new_status = st.text_area("✍️ บันทึกอาการ ปัญหา หรือข้อสังเกตการตรวจแปลง:", value=current_status)
        with col_t2:
            delayed_activity = st.selectbox("📌 เลือกกิจกรรมที่เริ่มล่าช้ากว่ากำหนด:", options=available_activities, index=1)
            shift_days = st.number_input("🔄 ปรับขยับวันเพิ่มเฉพาะกิจกรรมนี้และกิจกรรมถัดไป (วัน):", min_value=-30, max_value=60, value=0, help="เช่น ใส่เลข 2 จะทำให้กิจกรรมที่เลือกและกิจกรรมถัดไปเลื่อนช้าออกไป 2 วัน")
        
        preview_df = get_rice_schedule_advanced(
            sow_d, 
            target_field["สายพันธุ์ข้าว"], 
            district_name=target_field["อำเภอ"], 
            base_accum_shift=current_shift,
            delayed_act_name=delayed_activity if shift_days != 0 else last_delayed_act,
            new_delay_days=shift_days
        )
        
        st.markdown("---")
        if shift_days != 0:
            st.warning(f"🔍 **ตัวอย่างผลกระทบจากการเลื่อนกิจกรรม '{delayed_activity}' ออกไป +{shift_days} วัน:**")
        else:
            st.markdown(f"📋 **ปฏิทินกิจกรรมปัจจุบัน:**")
            
        show_preview = preview_df[["กิจกรรม", "วันตามกำหนดเดิม", "วันที่ปรับใหม่", "การปรับเปลี่ยน", "โอกาสเกิดฝนและการประเมิน"]]
        
        def highlight_preview(row):
            is_shifted = preview_df.loc[row.name, '_shifted']
            if is_shifted and (shift_days != 0 or current_shift > 0):
                return ['background-color: #fff9c4; font-weight: bold' for _ in row]
            return ['' for _ in row]
            
        st.dataframe(show_preview.style.apply(highlight_preview, axis=1), use_container_width=True, hide_index=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 บันทึกการอัปเดตและปรับเลื่อนแผนงาน", type="primary"):
            if update_field_status(selected_idx, new_status, delayed_activity if shift_days != 0 else last_delayed_act, shift_days):
                st.success(f"🔄 บันทึกเรียบร้อย! (บันทึกการเลื่อนกิจกรรม '{delayed_activity}' ออกไปอีก +{shift_days} วัน)")
                st.rerun()

# --- TAB 3 ---
with tab3:
    st.subheader("📊 แดชบอร์ดภาพรวมเพื่อการจัดลำดับความสำคัญในการลงพื้นที่")
    
    if history_df.empty:
        st.info("ℹ️ ปัจจุบันยังไม่มีข้อมูลแปลงนาในฐานข้อมูลส่วนกลาง")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("👥 จำนวนเกษตรกรในความดูแล", len(history_df["ชื่อเกษตรกร"].unique()))
        m2.metric("🚜 จำนวนแปลงนาลงทะเบียนทั้งหมด", len(history_df))
        
        alert_count = sum(history_df["สถานะ/ปัญหาที่พบ"].apply(is_alert_status))
        m3.metric("🚨 แปลงวิกฤต/ต้องเข้าตรวจเยี่ยมเร่งด่วน", alert_count)
        
        st.markdown("---")
        st.write("📋 **ตารางสรุปผลสถานะแปลงนาทั้งหมด**")
        
        display_df = history_df.copy()
        display_df["อายุข้าวปัจจุบัน (วัน)"] = display_df["วันที่เริ่มเพาะปลูก"].apply(calculate_rice_age)
        
        ordered_cols = [
            "ชื่อเกษตรกร", "อำเภอ", "ชื่อแปลง/ที่ตั้ง", "สายพันธุ์ข้าว", "วิธีการปลูก", 
            "วันที่เริ่มเพาะปลูก", "อายุข้าวปัจจุบัน (วัน)", "จำนวนวันที่ปรับเลื่อนสะสม",
            "กิจกรรมล่าสุดที่เลื่อน", "สถานะ/ปัญหาที่พบ", "วันที่อัปเดตล่าสุด"
        ]
        display_df = display_df[ordered_cols]
        
        def highlight_alerts(row):
            return ['background-color: #fff3cd;' if is_alert_status(row["สถานะ/ปัญหาที่พบ"]) else '' for _ in row]
            
        st.dataframe(display_df.style.apply(highlight_alerts, axis=1), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        col_select, col_action = st.columns([3, 1])
        
        with col_select:
            selected_record = st.selectbox(
                "🔎 เลือกแปลงนาเพื่อเรียกดูปฏิทินกิจกรรมที่ถูกเลื่อนวัน:", 
                options=[f"{row['ชื่อเกษตรกร']} - อ.{row['อำเภอ']} - {row['ชื่อแปลง/ที่ตั้ง']} ({row['สายพันธุ์ข้าว']})" for idx, row in history_df.iterrows()],
                key="dashboard_select"
            )
            
        if selected_record:
            selected_dashboard_idx = [f"{row['ชื่อเกษตรกร']} - อ.{row['อำเภอ']} - {row['ชื่อแปลง/ที่ตั้ง']} ({row['สายพันธุ์ข้าว']})" for idx, row in history_df.iterrows()].index(selected_record)
            target_row = history_df.iloc[selected_dashboard_idx]
            
            with col_action:
                st.write("") 
                st.write("") 
                if st.button("🗑️ ลบแปลงนานี้ออกจากระบบ", type="secondary", use_container_width=True):
                    if delete_field_record(selected_dashboard_idx):
                        st.toast(f"❌ ลบแปลงของ {target_row['ชื่อเกษตรกร']} เรียบร้อยแล้ว")
                        st.rerun()
            
            try:
                old_sow_date = datetime.datetime.strptime(str(target_row["วันที่เริ่มเพาะปลูก"]), "%Y-%m-%d").date()
            except:
                old_sow_date = datetime.date.today()
                
            old_rice = target_row["สายพันธุ์ข้าว"]
            old_district = target_row.get("อำเภอ", "เมืองฉะเชิงเทรา")
            accumulated_shift = int(target_row.get("จำนวนวันที่ปรับเลื่อนสะสม", 0))
            delayed_act_saved = str(target_row.get("กิจกรรมล่าสุดที่เลื่อน", "ไม่มี"))
            
            old_df = get_rice_schedule_advanced(
                old_sow_date, 
                old_rice, 
                district_name=old_district, 
                base_accum_shift=accumulated_shift,
                delayed_act_name=delayed_act_saved
            )
            
            # 📢 สรุปแสดงความเปลี่ยนแปลงอย่างชัดเจนบน แดชบอร์ด
            st.markdown("### 🔔 รายงานกิจกรรมที่เกิดการเลื่อนล่าช้า")
            if accumulated_shift > 0 and delayed_act_saved != "ไม่มี":
                st.warning(f"""
                ⚠️ **แปลงนี้มีการแจ้งปรับเลื่อนปฏิทิน!**
                - **จุดตั้งต้นที่เกิดการล่าช้า:** กิจกรรม **"{delayed_act_saved}"**
                - **จำนวนวันที่ขยับเลื่อน:** **+{accumulated_shift} วัน**
                - **ผลกระทบ:** กิจกรรมตั้งแต่ *"{delayed_act_saved}"* เป็นต้นไป ถูกปรับเลื่อนวันทำกิจกรรมออกไปทั้งหมด (ไฮไลต์ด้วยสีเหลืองด้านล่าง)
                """)
            elif accumulated_shift > 0:
                st.warning(f"⚠️ แปลงนี้มีการขยับวันเลื่อนรวม **+{accumulated_shift} วัน**")
            else:
                st.success("✅ **แปลงนี้ดำเนินกิจกรรมตรงตามกำหนดเดิมทุกขั้นตอน (ไม่มีกิจกรรมเลื่อนวัน)**")
            
            st.markdown(f"🔮 **ตารางปฏิทินกิจกรรมปัจจุบัน (อำเภอ: {old_district})**")
            
            show_old_df = old_df.drop(columns=['_danger', '_shifted'])
            def highlight_rows(row):
                is_danger = old_df.loc[row.name, '_danger']
                is_shifted = old_df.loc[row.name, '_shifted']
                if is_danger:
                    return ['background-color: #ffebee; font-weight: bold' for _ in row]
                elif is_shifted and accumulated_shift > 0:
                    return ['background-color: #fff9c4; font-weight: bold' for _ in row] # ไฮไลต์สีเหลืองกิจกรรมที่เลื่อนวัน
                return ['' for _ in row]
                
            st.dataframe(show_old_df.style.apply(highlight_rows, axis=1), use_container_width=True, hide_index=True)
