import streamlit as st
import sqlite3
from datetime import datetime

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('atn_tracking.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # 1. Create ATN Table if it doesn't exist at all
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS atns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year TEXT,
            report_no TEXT,
            chapter_number TEXT,
            ministry_dept TEXT,
            subject TEXT,
            assigned_wing TEXT,
            target_date_wing TEXT,
            target_date_fa TEXT,
            date_sent_to_fa TEXT,
            date_sent_to_go TEXT,
            date_sent_external TEXT,
            external_destination TEXT,
            is_closed INTEGER DEFAULT 0
        )
    ''')
    conn.commit()

    # 2. SAFETY MIGRATION: Forcefully inject 'remarks' column if missing from an old DB file
    try:
        cursor.execute("ALTER TABLE atns ADD COLUMN remarks TEXT DEFAULT '';")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    return conn

conn = init_db()
cursor = conn.cursor()

# --- CONFIG DATA MATRICES ---
WING_NAMES = ["Inspection", "EA", "Bangalore", "Mumbai", "Kolkata", "Chennai"]
MINISTRIES = ["MoES", "MNRE", "MoEFCC", "DBT", "DST", "DSIR", "DAE", "DoS"]
EXTERNAL_DESTINATIONS = ["DGA", "F&C", "HQ"]

# --- STREAMLIT UI CONFIG ---
st.set_page_config(page_title="ATN Milestone Portal", layout="wide")
st.title("🏛️ Real-Time ATN Milestone Tracking Portal")
st.markdown("---")

# --- USER ROLE SELECTION ---
st.sidebar.header("🔐 User Authentication")
user_role = st.sidebar.selectbox(
    "Select Your Role / Office:",
    ["DG (Director General)", "F&A Cell (Nodal)", "Group Officer (GO)"] + WING_NAMES
)
st.sidebar.info(f"Logged in as: **{user_role}**")

# --- HELPER FUNCTION FOR REMARKS ---
def append_remark(old_remarks, role, new_text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"[{role} - {timestamp}]: "
    if old_remarks and old_remarks.strip():
        return f"{old_remarks}\n{header}{new_text}"
    return f"{header}{new_text}"

# --- APP LOGIC BY ROLE ---

# 0. DIRECTOR GENERAL (DG) DASHBOARD
if user_role == "DG (Director General)":
    st.header("🦅 Director General (DG) Executive Overview")
    
    cursor.execute("SELECT COUNT(*) FROM atns WHERE is_closed=0")
    total_active = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM atns WHERE date_sent_to_fa IS NULL AND is_closed=0")
    with_wings = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM atns WHERE date_sent_to_fa IS NOT NULL AND date_sent_to_go IS NULL AND is_closed=0")
    with_fa = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM atns WHERE date_sent_to_go IS NOT NULL AND date_sent_external IS NULL AND is_closed=0")
    with_go = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM atns WHERE date_sent_external IS NOT NULL AND is_closed=0")
    with_ext = cursor.fetchone()[0]

    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
    m_col1.metric("📌 Total Active Files", total_active)
    m_col2.metric("⏳ Pending with Wings", with_wings)
    m_col3.metric("💼 In F&A Cell Review", with_fa)
    m_col4.metric("👑 With Group Officer", with_go)
    m_col5.metric("🌐 Sent Externally", with_ext)
    
    st.markdown("---")
    st.subheader("🔍 Interactive Pipeline Explorer")
    
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        filter_ministry = st.selectbox("Filter by Ministry/Dept", ["All"] + MINISTRIES)
    with f_col2:
        filter_wing = st.selectbox("Filter by Handling Wing", ["All"] + WING_NAMES)

# 1. F&A CELL (TRACKING NODAL): COMBINED UPLOAD & SCRUTINY QUEUE
if user_role == "F&A Cell (Nodal)":
    # SECTION A: NODAL UPLOAD CAPABILITY
    st.header("📋 Upload New Audit Action Taken Note (ATN)")
    with st.form("atn_upload_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            year = st.text_input("Year", placeholder="e.g., 2025-26")
            report_no = st.text_input("Report No.", placeholder="e.g., 05 of 2026")
        with col2:
            chapter = st.text_input("Chapter Number", placeholder="e.g., Chapter IV")
            ministry = st.selectbox("Ministry / Department", MINISTRIES)
        with col3:
            wing = st.selectbox("Assign to Wing/Branch", WING_NAMES)
            
        subject = st.text_area("Subject / Audit Paragraph Description")
        nodal_remark = st.text_input("Initial Entry Remarks / Special Instructions")
        
        col4, col5 = st.columns(2)
        with col4:
            t_wing = st.date_input("Target Date for Wing Submission")
        with col5:
            t_fa = st.date_input("Target Date for F&A Verification")
            
        submit_btn = st.form_submit_button("🚀 Upload & Dispatch to Wing/Branch")
        
        if submit_btn and year and report_no and subject:
            formatted_remark = ""
            if nodal_remark.strip():
                formatted_remark = append_remark("", "F&A Cell (Nodal Entry)", nodal_remark)
                
            cursor.execute('''
                INSERT INTO atns (year, report_no, chapter_number, ministry_dept, subject, assigned_wing, target_date_wing, target_date_fa, remarks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (year, report_no, chapter, ministry, subject, wing, str(t_wing), str(t_fa), formatted_remark))
            conn.commit()
            st.success(f"Successfully registered and sent ATN to {wing} branch!")
            st.rerun()

    # SECTION B: VERIFICATION / SCRUTINY WORKFLOW
    st.markdown("---")
    st.header("📥 F&A Verification & Scrutiny Queue")
    cursor.execute("SELECT id, report_no, assigned_wing, subject, target_date_fa, ministry_dept, remarks FROM atns WHERE date_sent_to_fa IS NOT NULL AND date_sent_to_go IS NULL AND is_closed=0")
    fa_items = cursor.fetchall()
    
    if not fa_items:
        st.success("🎉 Clear desk! No pending files received back from Wings for verification right now.")
    else:
        for item in fa_items:
            with st.expander(f"🟡 Reviewing: Report {item[1]} [{item[5]}] (Returned by {item[2]} | Deadline: {item[4]})", expanded=True):
                st.write(f"**Subject:** {item[3]}")
                
                if item[6]:
                    st.text_area("📜 Audit Trail Remarks History", value=item[6], disabled=True, key=f"fa_hist_{item[0]}")
                
                sent_date = st.date_input("Select Date Forwarded to GO", key=f"fa_date_{item[0]}")
                fa_remark = st.text_input("Add F&A Verification / Audit Remarks", key=f"fa_rem_{item[0]}")
                
                if st.button("Forward to Group Officer (GO)", key=f"fa_btn_{item[0]}"):
                    updated_remarks = append_remark(item[6], "F&A Cell (Scrutiny)", fa_remark) if fa_remark.strip() else item[6]
                    cursor.execute("UPDATE atns SET date_sent_to_go=?, remarks=? WHERE id=?", (str(sent_date), updated_remarks, item[0]))
                    conn.commit()
                    st.success("Scrutinized and forwarded up to Group Officer successfully!")
                    st.rerun()

# 2. WING / BRANCH DASHBOARD
if user_role in WING_NAMES:
    st.header(f"📥 Action Queue for {user_role} Branch")
    cursor.execute("SELECT id, report_no, subject, target_date_wing, ministry_dept, remarks FROM atns WHERE assigned_wing=? AND date_sent_to_fa IS NULL AND is_closed=0", (user_role,))
    wing_items = cursor.fetchall()
    
    if not wing_items:
        st.success(f"🎉 Clear desk! No pending ATNs requiring action from {user_role}.")
    else:
        for item in wing_items:
            with st.expander(f"🔴 Pending Action: Report {item[1]} [{item[4]}] (Target Deadline: {item[3]})", expanded=True):
                st.write(f"**Subject:** {item[2]}")
                
                if item[5]:
                    st.text_area("📜 Audit Trail Remarks History", value=item[5], disabled=True, key=f"wing_hist_{item[0]}")
                
                sent_date = st.date_input("Select Date Sent to F&A Cell", key=f"wing_date_{item[0]}")
                wing_remark = st.text_input("Add Wing Action/Drafting Remarks", key=f"wing_rem_{item[0]}")
                
                if st.button("Forward back to F&A Cell", key=f"wing_btn_{item[0]}"):
                    updated_remarks = append_remark(item[5], f"{user_role} Wing", wing_remark) if wing_remark.strip() else item[5]
                    cursor.execute("UPDATE atns SET date_sent_to_fa=?, remarks=? WHERE id=?", (str(sent_date), updated_remarks, item[0]))
                    conn.commit()
                    st.success("Passed back to F&A Cell successfully!")
                    st.rerun()

# 3. GROUP OFFICER (GO) ACTION DISPATCH & CLOSURE
if user_role == "Group Officer (GO)":
    st.header("👑 GO Final Action & Closure Deck")
    
    cursor.execute("SELECT id, report_no, assigned_wing, subject, ministry_dept, remarks FROM atns WHERE date_sent_to_go IS NOT NULL AND date_sent_external IS NULL AND is_closed=0")
    go_items = cursor.fetchall()
    
    if not go_items:
        st.info("No incoming files awaiting external dispatch action right now.")
    else:
        for item in go_items:
            with st.expander(f"🔵 Action Required: Report {item[1]} [{item[4]}] (Submitted by F&A)", expanded=True):
                st.write(f"**Originating Wing:** {item[2]} | **Subject:** {item[3]}")
                
                if item[5]:
                    st.text_area("📜 Audit Trail Remarks History", value=item[5], disabled=True, key=f"go_hist_{item[0]}")
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    ext_date = st.date_input("Date Dispatched Outward", key=f"go_date_{item[0]}")
                with col_d2:
                    dest = st.selectbox("External Destination", EXTERNAL_DESTINATIONS, key=f"go_dest_{item[0]}")
                
                go_remark = st.text_input("Add GO Final Approval / Dispatch Remarks", key=f"go_rem_{item[0]}")
                
                if st.button("Log External Dispatch", key=f"go_btn_{item[0]}"):
                    updated_remarks = append_remark(item[5], "Group Officer", go_remark) if go_remark.strip() else item[5]
                    cursor.execute("UPDATE atns SET date_sent_external=?, external_destination=?, remarks=? WHERE id=?", (str(ext_date), dest, updated_remarks, item[0]))
                    conn.commit()
                    st.success("Dispatched outwards successfully!")
                    st.rerun()

    # Active External Trackers Configuration Section
    st.markdown("---")
    st.subheader("🌐 Active External Trackers (Awaiting Closure)")
    cursor.execute("SELECT id, report_no, assigned_wing, external_destination, date_sent_external, ministry_dept, remarks FROM atns WHERE date_sent_external IS NOT NULL AND is_closed=0")
    ext_items = cursor.fetchall()
    
    if not ext_items:
        st.caption("No files currently deployed with external branches (DGA/F&C/HQ).")
    else:
        for item in ext_items:
            current_dest = item[3]
            with st.expander(f"📌 Report No. {item[1]} [{item[5]}] ➔ Currently with **{current_dest}** (Dispatched: {item[4]})", expanded=False):
                if item[6]:
                    st.text_area("📜 Audit Trail Remarks History", value=item[6], disabled=True, key=f"ext_hist_{item[0]}")
                
                # Dynamic Inter-External Status Modification Panel (Update between DGA / F&C / HQ)
                st.markdown("🔄 **Update External Status Location**")
                col_up1, col_up2 = st.columns([2, 2])
                with col_up1:
                    new_dest = st.selectbox("Switch Destination Status To:", EXTERNAL_DESTINATIONS, index=EXTERNAL_DESTINATIONS.index(current_dest), key=f"change_dest_val_{item[0]}")
                    status_remark = st.text_input("Status Transition Note", placeholder="Reason for updating status...", key=f"status_note_{item[0]}")
                with col_up2:
                    st.write(" ") # Structural layout spacers
                    st.write(" ")
                    if st.button(f"Update Status to {new_dest}", key=f"update_status_btn_{item[0]}"):
                        if new_dest == current_dest:
                            st.warning("The file is already assigned to that station.")
                        else:
                            transition_msg = status_remark if status_remark.strip() else f"Status manually redirected from {current_dest} to {new_dest}."
                            updated_remarks = append_remark(item[6], "Group Officer (Status Re-route)", transition_msg)
                            cursor.execute("UPDATE atns SET external_destination=?, remarks=? WHERE id=?", (new_dest, updated_remarks, item[0]))
                            conn.commit()
                            st.success(f"File status successfully updated to: With {new_dest}!")
                            st.rerun()
                
                st.markdown("---")

                # Closure Block Configuration
                final_remark = st.text_input("Add Final Closure Note / Remarks (Optional)", key=f"close_rem_{item[0]}")
                if st.button("🔒 Permanently Archive & Close File", key=f"close_btn_{item[0]}"):
                    updated_remarks = item[6]
                    if final_remark.strip():
                        updated_remarks = append_remark(item[6], "Group Officer (Closure)", final_remark)
                    cursor.execute("UPDATE atns SET is_closed=1, remarks=? WHERE id=?", (updated_remarks, item[0]))
                    conn.commit()
                    st.success("File permanently archived and dropped from tracking pipeline!")
                    st.rerun()

# --- 4. GLOBAL MONITORING DASHBOARD (VISIBLE TO ALL USERS) ---
if user_role != "DG (Director General)":
    st.markdown("---")
    st.header("📊 Live Active Pipeline (Master Board)")

# Build dynamic query logic
query = '''
    SELECT year, report_no, chapter_number, ministry_dept, assigned_wing, 
    date_sent_to_fa, date_sent_to_go, date_sent_external, external_destination, remarks 
    FROM atns WHERE is_closed=0
'''
params = []

if user_role == "DG (Director General)":
    if filter_ministry != "All":
        query += " AND ministry_dept = ?"
        params.append(filter_ministry)
    if filter_wing != "All":
        query += " AND assigned_wing = ?"
        params.append(filter_wing)

cursor.execute(query, tuple(params))
all_active = cursor.fetchall()

if not all_active:
    st.info("The live board is currently empty or no entries match your selected criteria.")
else:
    display_data = []
    for row in all_active:
        if row[7]:
            status = f"🌐 With {row[8]}"
        elif row[6]:
            status = "👑 With GO (Group Officer)"
        elif row[5]:
            status = "💼 With F&A Cell"
        else:
            status = "⏳ With Wing"
            
        display_data.append({
            "Year": row[0], "Report No": row[1], "Chapter": row[2], 
            "Ministry/Dept": row[3], "Handling Branch": row[4], 
            "Current Station Status": status, "Latest Remarks Log": row[9]
        })
    st.table(display_data)