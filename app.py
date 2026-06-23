import streamlit as st
import requests
from datetime import datetime
import os

# --- SECURE CLOUD CONFIGURATION ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except (KeyError, FileNotFoundError):
    st.error("🔑 **Missing Database Configuration!** Please add `SUPABASE_URL` and `SUPABASE_KEY` to your Streamlit Cloud Secrets dashboard.")
    st.stop()

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# --- DATABASE ENGINE FUNCTIONS ---
def fetch_all_active(ministry="All", wing="All"):
    url = f"{SUPABASE_URL}/rest/v1/atns?is_closed=eq.0"
    if ministry != "All":
        url += f"&ministry_dept=eq.{ministry}"
    if wing != "All":
        url += f"&assigned_wing=eq.{wing}"
    response = requests.get(url, headers=HEADERS)
    return response.json() if response.status_code == 200 else []

def get_counts():
    res = requests.get(f"{SUPABASE_URL}/rest/v1/atns?is_closed=eq.0", headers=HEADERS).json()
    if not isinstance(res, list): 
        return {"total": 0, "wings": 0, "fa": 0, "go": 0, "fc": 0, "hq": 0}
    return {
        "total": len(res),
        "wings": len([x for x in res if not x.get('date_sent_to_fa')]),
        "fa": len([x for x in res if x.get('date_sent_to_fa') and not x.get('date_sent_to_go')]),
        "go": len([x for x in res if x.get('date_sent_to_go') and not x.get('date_sent_external')]),
        "fc": len([x for x in res if x.get('date_sent_external') and x.get('external_destination') == "F&C"]),
        "hq": len([x for x in res if x.get('date_sent_external') and x.get('external_destination') == "HQ"])
    }

def authenticate_user(uid, pwd):
    url = f"{SUPABASE_URL}/rest/v1/users?username=eq.{uid}&password=eq.{pwd}"
    res = requests.get(url, headers=HEADERS).json()
    return res[0] if res else None

def update_password(uid, new_pwd):
    url = f"{SUPABASE_URL}/rest/v1/users?username=eq.{uid}"
    requests.patch(url, headers=HEADERS, json={"password": new_pwd})

def append_remark(old_remarks, role, new_text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"[{role} - {timestamp}]: "
    if old_remarks and old_remarks.strip():
        return f"{old_remarks}\n{header}{new_text}"
    return f"{header}{new_text}"

# --- CONFIGURATION ARRAYS ---
WING_NAMES = ["Inspection", "EA", "Bangalore", "Mumbai", "Kolkata", "Chennai"]
MINISTRIES = ["MoES", "MNRE", "MoEFCC", "DBT", "DST", "DSIR", "DAE", "DoS"]
EXTERNAL_DESTINATIONS = ["DGA", "F&C", "HQ"]
PAC_OPTIONS = ["PAC", "Non PAC"]
JOURNEY_OPTIONS = ["1st Journey", "2nd Journey"]
YEARS_POOL = ["2022", "2023", "2024", "2025", "2026", "2027", "2028"]

# --- APP LAYOUT ---
st.set_page_config(page_title="ATN Tracking Portal", layout="wide")

st.title("🏛️ ATN Tracking Portal")
st.markdown("##### **DGA, CE (ESD)**")
st.markdown("---")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user_info"] = None
if "dg_sub_filter" not in st.session_state:
    st.session_state["dg_sub_filter"] = "All"

# --- SIDEBAR BRANDING & AUTHENTICATION ---
logo_path = "cag.png"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
else:
    st.sidebar.markdown("### **🏛️ CAG INDIA**")
    st.sidebar.caption("Institutional Repository Link Active")

st.sidebar.markdown("---")
st.sidebar.header("🔐 User Authentication")

if not st.session_state["authenticated"]:
    input_uid = st.sidebar.text_input("User ID / Account")
    input_pwd = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("🔑 Log In"):
        account = authenticate_user(input_uid, input_pwd)
        if account:
            st.session_state["authenticated"] = True
            st.session_state["user_info"] = {"username": account["username"], "role": account["role"]}
            st.rerun()
        else:
            st.sidebar.error("❌ Invalid ID or Password.")
    st.stop()
else:
    current_user = st.session_state["user_info"]["username"]
    user_role = st.session_state["user_info"]["role"]
    st.sidebar.info(f"User ID: **{current_user}**\n\nRole: **{user_role}**")
    
    with st.sidebar.expander("⚙️ Account Settings (Change Password)"):
        new_pwd = st.text_input("New Password", type="password")
        confirm_pwd = st.text_input("Confirm New Password", type="password")
        if st.button("Update Password"):
            if new_pwd == confirm_pwd and new_pwd.strip() != "":
                update_password(current_user, new_pwd.strip())
                st.success("Password modified in cloud database!")
            else:
                st.error("Passwords mismatch or empty value.")

    if st.sidebar.button("🚪 Log Out"):
        st.session_state["authenticated"] = False
        st.session_state["user_info"] = None
        st.rerun()

# --- ROLE-BASED DASHBOARD FILTER INITIALIZATION ---
filter_ministry = "All"
filter_wing = "All"

# --- 0. DG DASHBOARD ROLE ---
if user_role == "DG (Director General)":
    st.header("🦅 Director General (DG) Executive Overview")
    counts = get_counts()
    
    st.markdown("##### 🔍 Click on any segment badge to instantly focus the pipeline grid below:")
    m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)
    
    with m_col1:
        if st.button(f"📋 Total Active\n👉 {counts['total']}", use_container_width=True):
            st.session_state["dg_sub_filter"] = "All"
    with m_col2:
        if st.button(f"⏳ Pending Wings\n👉 {counts['wings']}", use_container_width=True):
            st.session_state["dg_sub_filter"] = "Pending Wings"
    with m_col3:
        if st.button(f"💼 In F&A Cell\n👉 {counts['fa']}", use_container_width=True):
            st.session_state["dg_sub_filter"] = "Pending F&A"
    with m_col4:
        if st.button(f"👑 With GO\n👉 {counts['go']}", use_container_width=True):
            st.session_state["dg_sub_filter"] = "Pending GO"
    with m_col5:
        if st.button(f"🏢 With F&C\n👉 {counts['fc']}", use_container_width=True):
            st.session_state["dg_sub_filter"] = "With F&C"
    with m_col6:
        if st.button(f"🏢 With HQ\n👉 {counts['hq']}", use_container_width=True):
            st.session_state["dg_sub_filter"] = "With HQ"

    st.markdown(f"Current Dashboard Context Filter Focus: **📊 {st.session_state['dg_sub_filter']}**")
    
    st.markdown("---")
    st.subheader("🔍 Secondary Dropdown Explorers")
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        filter_ministry = st.selectbox("Filter by Ministry/Dept", ["All"] + MINISTRIES)
    with f_col2:
        filter_wing = st.selectbox("Filter by Handling Wing", ["All"] + WING_NAMES)
        
    st.markdown("---")
    st.subheader("📊 Executive Pipeline Grid")
    
    all_active = fetch_all_active(ministry=filter_ministry, wing=filter_wing)
    if all_active and isinstance(all_active, list):
        dg_display_data = []
        for row in all_active:
            is_wing = not row.get('date_sent_to_fa')
            is_fa = row.get('date_sent_to_fa') and not row.get('date_sent_to_go')
            is_go = row.get('date_sent_to_go') and not row.get('date_sent_external')
            is_fc_dest = row.get('date_sent_external') and row.get('external_destination') == "F&C"
            is_hq_dest = row.get('date_sent_external') and row.get('external_destination') == "HQ"
            
            sf = st.session_state["dg_sub_filter"]
            if sf == "Pending Wings" and not is_wing: continue
            if sf == "Pending F&A" and not is_fa: continue
            if sf == "Pending GO" and not is_go: continue
            if sf == "With F&C" and not is_fc_dest: continue
            if sf == "With HQ" and not is_hq_dest: continue

            status = f"🌐 With {row['external_destination']}" if row.get('date_sent_external') else ("👑 With GO" if row.get('date_sent_to_go') else ("💼 With F&A Cell" if row.get('date_sent_to_fa') else f"⏳ With Wing ({row['assigned_wing']})"))
            date_wing_fwd = row.get('date_sent_to_fa') if row.get('date_sent_to_fa') else "Pending"
            
            date_sent_fc = row.get('date_sent_external') if is_fc_dest else "N/A"
            date_sent_hq = row.get('date_sent_external') if is_hq_dest else "N/A"
            
            dg_display_data.append({
                "Year": row['year'], 
                "Report No": row['report_no'], 
                "Ministry Dept": row['ministry_dept'],
                "Para No": row['chapter_number'], 
                "Subject": row['subject'],
                "Target Date for Wings": row['target_date_wing'],
                "Target Date for F&A": row['target_date_fa'],
                "Target Date of Uploading on APMS": row.get('target_date_upload', 'N/A'),
                "Journey": row.get('journey_status', '1st Journey'),
                "PAC/Non-PAC": row.get('pac_status', 'Non PAC'),
                "Handling Branch": row['assigned_wing'],
                "Date Wing Forwarded to F&A": date_wing_fwd,
                "Date Sent to F&C": date_sent_fc,
                "Date Sent to HQ": date_sent_hq,
                "Current Station Status": status
            })
            
        if dg_display_data:
            st.table(dg_display_data)
        else:
            st.info("No records match the active segment filters.")
    else:
        st.info("No data available.")

# --- 1. F&A CELL (TRACKING NODAL) ROLE (UPGRADED THREE-TAB DECK) ---
if user_role == "F&A Cell (Nodal)":
    # FIXED: Restructured F&A screen to incorporate a standalone queue tab for items received back from wings
    tab_upload, tab_received, tab_edit = st.tabs([
        "📋 Upload New ATN Record", 
        "📥 ATNs Received Back From Wings Queue",
        "✏️ Edit Existing ATN Records"
    ])
    
    with tab_upload:
        st.subheader("Register a New Audit Paragraph")
        with st.form("atn_upload_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                year = st.selectbox("Year", YEARS_POOL)
                report_no = st.text_input("Report No.", placeholder="e.g., 05 of 2026")
                para_no = st.text_input("Para Number", placeholder="e.g., Para 4.1")
            with col2:
                ministry = st.selectbox("Ministry / Department", MINISTRIES)
                wing = st.selectbox("Assign to Wing/Branch", WING_NAMES)
                pac_status = st.selectbox("PAC/Non-PAC", PAC_OPTIONS)
            with col3:
                journey_status = st.selectbox("Journey", JOURNEY_OPTIONS)
                t_wing = st.date_input("Target Date for Wing Submission")
                t_fa = st.date_input("Target Date for F&A Verification")
                
            col_extra1, col_extra2 = st.columns(2)
            with col_extra1:
                t_upload = st.date_input("Target Date for Uploading on APMS")
            with col_extra2:
                nodal_remark = st.text_input("Initial Entry Remarks / Special Instructions")
                
            subject = st.text_area("Subject / Audit Paragraph Description")
            
            if st.form_submit_button("🚀 Upload & Dispatch to Wing/Branch") and year and report_no and subject:
                formatted_remark = append_remark("", "F&A Cell (Nodal Entry)", nodal_remark) if nodal_remark.strip() else ""
                payload = {
                    "year": year, "report_no": report_no, "chapter_number": para_no, "ministry_dept": ministry,
                    "subject": subject, "assigned_wing": wing, "target_date_wing": str(t_wing), "target_date_fa": str(t_fa), 
                    "remarks": formatted_remark, "pac_status": pac_status, "journey_status": journey_status, "target_date_upload": str(t_upload)
                }
                requests.post(f"{SUPABASE_URL}/rest/v1/atns", headers=HEADERS, json=payload)
                st.success("Successfully registered and sent ATN to wing branch!")
                st.rerun()

    # FIXED: Standalone Tab 2 logic explicitly trapping items sent by operational units awaiting processing
    with tab_received:
        st.subheader("⚖️ Verification & Scrutiny Queue")
        fa_items = requests.get(f"{SUPABASE_URL}/rest/v1/atns?date_sent_to_fa=not.is.null&date_sent_to_go=is.null&is_closed=eq.0", headers=HEADERS).json()
        if fa_items and isinstance(fa_items, list):
            for item in fa_items:
                fa_header = f"🟡 Received Back from {item.get('assigned_wing', 'Wing')} ➔ Para No: {item.get('chapter_number', 'N/A')} | Report No: {item.get('report_no', 'N/A')} | Dept: {item.get('ministry_dept', 'N/A')}"
                with st.expander(fa_header, expanded=True):
                    st.write(f"**Subject:** {item['subject']}")
                    st.caption(f"🛡️ **Type:** {item.get('pac_status', 'Non PAC')} | 🛤️ **Journey:** {item.get('journey_status', '1st Journey')} | 📅 **Target Upload Date on APMS:** {item.get('target_date_upload', 'N/A')}")
                    if item['remarks']: 
                        st.text_area("📜 Audit Trail History", value=item['remarks'], disabled=True, key=f"fa_hist_{item['id']}")
                    
                    st.markdown("##### 🚀 Route Forward to Group Officer")
                    sent_date = st.date_input("Select Date Forwarded to GO", key=f"fa_date_{item['id']}")
                    fa_remark = st.text_input("Add F&A Verification Scrutiny Remarks", key=f"fa_rem_{item['id']}")
                    if st.button("Forward to Group Officer (GO)", key=f"fa_btn_{item['id']}"):
                        updated_remarks = append_remark(item['remarks'], "F&A Cell (Scrutiny Check)", fa_remark) if fa_remark.strip() else item['remarks']
                        requests.patch(f"{SUPABASE_URL}/rest/v1/atns?id=eq.{item['id']}", headers=HEADERS, json={"date_sent_to_go": str(sent_date), "remarks": updated_remarks})
                        st.success("Forwarded to GO! File cleared from this tab.")
                        st.rerun()
        else:
            st.info("🎉 Clear queue! No records currently forwarded back from wings awaiting F&A processing.")

    with tab_edit:
        st.subheader("Modify Live Pipeline Entries")
        active_items = fetch_all_active()
        
        if not active_items:
            st.info("No active records available to edit.")
        else:
            item_options = {f"ID {x['id']} | Rep: {x['report_no']} | Para: {x['chapter_number']} | Wing: {x['assigned_wing']}": x for x in active_items}
            selected_label = st.selectbox("Select ATN Entry to Correct:", list(item_options.keys()))
            target_item = item_options[selected_label]
            
            with st.form("atn_edit_form"):
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    e_year = st.selectbox("Year", YEARS_POOL, index=YEARS_POOL.index(target_item['year']) if target_item['year'] in YEARS_POOL else 0)
                    e_report = st.text_input("Report No.", value=target_item['report_no'])
                    e_para = st.text_input("Para Number", value=target_item['chapter_number'])
                with ec2:
                    e_ministry = st.selectbox("Ministry / Department", MINISTRIES, index=MINISTRIES.index(target_item['ministry_dept']) if target_item['ministry_dept'] in MINISTRIES else 0)
                    e_wing = st.selectbox("Assigned Wing", WING_NAMES, index=WING_NAMES.index(target_item['assigned_wing']) if target_item['assigned_wing'] in WING_NAMES else 0)
                    e_pac = st.selectbox("PAC/Non-PAC", PAC_OPTIONS, index=PAC_OPTIONS.index(target_item.get('pac_status', 'Non PAC')) if target_item.get('pac_status') in PAC_OPTIONS else 0)
                with ec3:
                    e_journey = st.selectbox("Journey", JOURWAY_OPTIONS, index=JOURNEY_OPTIONS.index(target_item.get('journey_status', '1st Journey')) if target_item.get('journey_status') in JOURNEY_OPTIONS else 0) if 'JOURWAY_OPTIONS' not in globals() else st.selectbox("Journey", JOURNEY_OPTIONS, index=JOURNEY_OPTIONS.index(target_item.get('journey_status', '1st Journey')) if target_item.get('journey_status') in JOURNEY_OPTIONS else 0)
                    
                    def parse_dt(dt_str):
                        try: return datetime.strptime(dt_str, "%Y-%m-%d").date()
                        except: return datetime.today().date()
                        
                    e_t_wing = st.date_input("Target Date for Wings", value=parse_dt(target_item['target_date_wing']))
                    e_t_fa = st.date_input("Target Date for F&A", value=parse_dt(target_item['target_date_fa']))
            
                ec_extra1, ec_extra2 = st.columns(2)
                with ec_extra1:
                    e_t_upload = st.date_input("Target Date for Uploading on APMS", value=parse_dt(target_item.get('target_date_upload')))
                with ec_extra2:
                    correction_reason = st.text_input("Reason for Modification (Appends to Log history)")

                e_subject = st.text_area("Subject Description", value=target_item['subject'])
                
                if st.form_submit_button("💾 Save & Overwrite Cloud Record"):
                    log_text = correction_reason.strip() if correction_reason.strip() else "Record details modified by Nodal Officer."
                    updated_remarks = append_remark(target_item['remarks'], "F&A Cell (Data Correction)", log_text)
                    
                    update_payload = {
                        "year": e_year, "report_no": e_report, "chapter_number": e_para, "ministry_dept": e_ministry,
                        "assigned_wing": e_wing, "pac_status": e_pac, "journey_status": e_journey,
                        "target_date_wing": str(e_t_wing), "target_date_fa": str(e_t_fa), "target_date_upload": str(e_t_upload),
                        "subject": e_subject, "remarks": updated_remarks
                    }
                    
                    patch_url = f"{SUPABASE_URL}/rest/v1/atns?id=eq.{target_item['id']}"
                    requests.patch(patch_url, headers=HEADERS, json=update_payload)
                    st.success("Cloud record updated successfully!")
                    st.rerun()

# --- 2. OPERATIONAL WINGS ROLE ---
if user_role in WING_NAMES:
    st.header(f"📥 Action Queue for {user_role} Branch")
    wing_items = requests.get(f"{SUPABASE_URL}/rest/v1/atns?assigned_wing=eq.{user_role}&date_sent_to_fa=is.null&is_closed=eq.0", headers=HEADERS).json()
    if wing_items and isinstance(wing_items, list):
        for item in wing_items:
            wing_header = f"🔴 Para No: {item.get('chapter_number', 'N/A')} | Report No: {item.get('report_no', 'N/A')} | Dept: {item.get('ministry_dept', 'N/A')}"
            with st.expander(wing_header, expanded=True):
                st.write(f"**Subject:** {item['subject']}")
                st.caption(f"🛡️ **PAC/Non-PAC:** {item.get('pac_status', 'Non PAC')} | 🛤️ **Journey:** {item.get('journey_status', '1st Journey')} | 📅 **Target Upload on APMS:** {item.get('target_date_upload', 'N/A')}")
                if item['remarks']: 
                    st.text_area("📜 Audit Trail History", value=item['remarks'], disabled=True, key=f"wing_hist_{item['id']}")
                sent_date = st.date_input("Select Date Sent to F&A Cell", key=f"wing_date_{item['id']}")
                wing_remark = st.text_input("Add Wing Action Remarks", key=f"wing_rem_{item['id']}")
                if st.button("Forward back to F&A Cell", key=f"wing_btn_{item['id']}"):
                    updated_remarks = append_remark(item['remarks'], f"{user_role} Wing", wing_remark) if wing_remark.strip() else item['remarks']
                    requests.patch(f"{SUPABASE_URL}/rest/v1/atns?id=eq.{item['id']}", headers=HEADERS, json={"date_sent_to_fa": str(sent_date), "remarks": updated_remarks})
                    st.rerun()
    else:
        st.info("🎉 Clear queue! No files currently assigned to your wing.")

# --- 3. GROUP OFFICER (GO) ROLE ---
if user_role == "Group Officer (GO)":
    st.header("👑 Group Officer Desk")
    
    go_tab_action, go_tab_edit = st.tabs([
        "📥 Pending Actions & Trackers", 
        "✏️ Universal ATN Data Correction Deck"
    ])
    
    with go_tab_action:
        st.subheader("Awaiting Initial Dispatch Signatures")
        go_items = requests.get(f"{SUPABASE_URL}/rest/v1/atns?date_sent_to_go=not.is.null&date_sent_external=is.null&is_closed=eq.0", headers=HEADERS).json()
        if go_items and isinstance(go_items, list):
            for item in go_items:
                go_header = f"🔵 Pending Dispatch ➔ Para No: {item.get('chapter_number', 'N/A')} | Report No: {item.get('report_no', 'N/A')} | Dept: {item.get('ministry_dept', 'N/A')} | Origin: {item.get('assigned_wing', 'N/A')}"
                with st.expander(go_header, expanded=True):
                    st.write(f"**Subject Description:** {item['subject']}")
                    st.caption(f"🛡️ **PAC/Non-PAC:** {item.get('pac_status', 'Non PAC')} | 🛤️ **Journey:** {item.get('journey_status', '1st Journey')} | 📅 **Year:** {item.get('year')}")
                    
                    if item['remarks']: 
                        st.text_area("📜 Audit Trail History", value=item['remarks'], disabled=True, key=f"go_action_hist_{item['id']}")
                    
                    st.markdown("##### 🚀 Log External Dispatch")
                    col_d1, col_d2 = st.columns(2)
                    with col_d1: ext_date = st.date_input("Date Dispatched Outward", key=f"go_date_{item['id']}")
                    with col_d2: dest = st.selectbox("External Destination", EXTERNAL_DESTINATIONS, key=f"go_dest_{item['id']}")
                    go_remark = st.text_input("Add GO Approval Remarks", key=f"go_rem_{item['id']}")
                    
                    if st.button("Log Dispatch & Route Outward", key=f"go_btn_{item['id']}"):
                        updated_remarks = append_remark(item['remarks'], "Group Officer (Dispatch Sign-off)", go_remark) if go_remark.strip() else item['remarks']
                        dispatch_payload = {
                            "date_sent_external": str(ext_date), 
                            "external_destination": dest, 
                            "remarks": updated_remarks
                        }
                        requests.patch(f"{SUPABASE_URL}/rest/v1/atns?id=eq.{item['id']}", headers=HEADERS, json=dispatch_payload)
                        st.success("Dispatched! Removed from pending signature stage.")
                        st.rerun()
        else:
            st.info("🎉 No files awaiting fresh processing signatures.")

        st.markdown("---")
        st.subheader("🌐 Active External Trackers (Awaiting Closure)")
        ext_items = requests.get(f"{SUPABASE_URL}/rest/v1/atns?date_sent_external=not.is.null&is_closed=eq.0", headers=HEADERS).json()
        if ext_items and isinstance(ext_items, list):
            for item in ext_items:
                ext_header = f"📌 Outward Tracker ➔ Para No: {item.get('chapter_number', 'N/A')} | Report No: {item.get('report_no', 'N/A')} | Dept: {item.get('ministry_dept', 'N/A')} ➔ Handed to: {item['external_destination']}"
                with st.expander(ext_header, expanded=False):
                    if item['remarks']: 
                        st.text_area("📜 Audit Trail History", value=item['remarks'], disabled=True, key=f"ext_hist_{item['id']}")
                    
                    col_up1, col_up2 = st.columns([2, 2])
                    with col_up1:
                        new_dest = st.selectbox("Switch Destination Status To:", EXTERNAL_DESTINATIONS, index=EXTERNAL_DESTINATIONS.index(item['external_destination']), key=f"change_dest_val_{item['id']}")
                        status_remark = st.text_input("Status Transition Note", key=f"status_note_{item['id']}")
                    with col_up2:
                        st.write(" ")
                        st.write(" ")
                        if st.button(f"Update Status to {new_dest}", key=f"update_status_btn_{item['id']}"):
                            transition_msg = status_remark if status_remark.strip() else f"Status manually redirected to {new_dest}."
                            updated_remarks = append_remark(item['remarks'], "Group Officer (Status Re-route)", transition_msg)
                            requests.patch(f"{SUPABASE_URL}/rest/v1/atns?id=eq.{item['id']}", headers=HEADERS, json={"external_destination": new_dest, "remarks": updated_remarks})
                            st.rerun()
                    
                    st.markdown("---")
                    final_remark = st.text_input("Add Final Closure Note (Optional)", key=f"close_rem_{item['id']}")
                    if st.button("🔒 Permanently Archive & Close File", key=f"close_btn_{item['id']}"):
                        updated_remarks = append_remark(item['remarks'], "Group Officer (Closure)", final_remark) if final_remark.strip() else item['remarks']
                        requests.patch(f"{SUPABASE_URL}/rest/v1/atns?id=eq.{item['id']}", headers=HEADERS, json={"is_closed": 1, "remarks": updated_remarks})
                        st.rerun()

    with go_tab_edit:
        st.subheader("Administrative Metadata Modification Panel")
        all_active_items = fetch_all_active()
        if not all_active_items:
            st.info("No active pipeline files available to correct.")
        else:
            go_edit_options = {f"Para: {x['chapter_number']} | Rep: {x['report_no']} | Dept: {x.get('ministry_dept', 'N/A')} | Wing: {x['assigned_wing']} (ID: {x['id']})": x for x in all_active_items}
            selected_edit_label = st.selectbox("Select Target File for Correction:", list(go_edit_options.keys()), key="go_universal_select")
            go_target_item = go_edit_options[selected_edit_label]
            
            with st.form("go_universal_edit_form"):
                gov_c1, gov_c2, gov_c3 = st.columns(3)
                with gov_c1:
                    go_opt_year = st.selectbox("Year", YEARS_POOL, index=YEARS_POOL.index(go_target_item['year']) if go_target_item['year'] in YEARS_POOL else 0)
                    go_opt_rep = st.text_input("Report No.", value=go_target_item['report_no'])
                with gov_c2:
                    go_opt_para = st.text_input("Para Number", value=go_target_item['chapter_number'])
                    go_opt_pac = st.selectbox("PAC/Non-PAC", PAC_OPTIONS, index=PAC_OPTIONS.index(go_target_item.get('pac_status', 'Non PAC')) if go_target_item.get('pac_status') in PAC_OPTIONS else 0)
                with gov_c3:
                    go_opt_journ = st.selectbox("Journey", JOURNEY_OPTIONS, index=JOURNEY_OPTIONS.index(go_target_item.get('journey_status', '1st Journey')) if go_target_item.get('journey_status') in JOURNEY_OPTIONS else 0)
                
                go_opt_sub = st.text_area("Subject Description", value=go_target_item['subject'])
                go_correction_reason = st.text_input("Modification Log Summary Note", placeholder="Explain the reason for changing these parameters...")
                
                if st.form_submit_button("💾 Save Changes & Update Audit Logs"):
                    log_reason_text = go_correction_reason.strip() if go_correction_reason.strip() else "Record details modified by Group Officer."
                    meta_log = append_remark(go_target_item['remarks'], "Group Officer (Metadata Correction)", log_reason_text)
                    
                    meta_payload = {
                        "year": go_opt_year, "report_no": go_opt_rep, "chapter_number": go_opt_para,
                        "pac_status": go_opt_pac, "journey_status": go_opt_journ, "subject": go_opt_sub,
                        "remarks": meta_log
                    }
                    requests.patch(f"{SUPABASE_URL}/rest/v1/atns?id=eq.{go_target_item['id']}", headers=HEADERS, json=meta_payload)
                    st.success("Metadata updates saved and updated in comments history logs!")
                    st.rerun()

# --- 4. GLOBAL DASHBOARD (MASTER BOARD FOR OTHER ROLES) ---
if user_role != "DG (Director General)":
    st.markdown("---")
    st.header("📊 Live Active Pipeline (Master Board)")

    all_active = fetch_all_active(ministry=filter_ministry, wing=filter_wing)
    if all_active and isinstance(all_active, list):
        display_data = []
        for row in all_active:
            status = f"🌐 With {row['external_destination']}" if row.get('date_sent_external') else ("👑 With GO" if row.get('date_sent_to_go') else ("💼 With F&A Cell" if row.get('date_sent_to_fa') else "⏳ With Wing"))
            display_data.append({
                "Year": row['year'], 
                "Report No": row['report_no'], 
                "Ministry Dept": row['ministry_dept'],
                "Para No": row['chapter_number'], 
                "Subject": row['subject'],
                "Target Date for Wings": row['target_date_wing'],
                "Target Date for F&A": row['target_date_fa'],
                "Target Date of Uploading on APMS": row.get('target_date_upload', 'N/A'),
                "Journey": row.get('journey_status', '1st Journey'),
                "PAC/Non-PAC": row.get('pac_status', 'Non PAC'),
                "Handling Branch": row['assigned_wing'], 
                "Current Station Status": status, 
                "Latest Remarks Log": row['remarks']
            })
        st.table(display_data)
    else:
        st.info("The monitoring grid is currently empty. No active items match the search filters.")
