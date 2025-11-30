# app.py
import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, date
import plotly.express as px

# -------------------------
# Helper: DB connection
# -------------------------
DB_PATH = "employee.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# -------------------------
# Password hashing & auth
# -------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash

def create_user(username: str, password: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hash_password(password))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(username: str, password: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if row:
        return verify_password(password, row[0])
    return False

# -------------------------
# Employee CRUD operations
# -------------------------
def add_employee_db(name, age, gender, role, department, salary, doj, perf_score=3):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO employees 
        (name, age, gender, role, department, salary, date_of_joining, performance_score, promotion_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (name, age, gender, role, department, salary, doj, perf_score))
    conn.commit()
    conn.close()

def get_all_employees_df():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM employees", conn, parse_dates=['date_of_joining'])
    conn.close()
    return df

def update_employee_db(emp_id, name, age, gender, role, department, salary, doj, perf_score, promo_count):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE employees SET 
        name=?, age=?, gender=?, role=?, department=?, salary=?, date_of_joining=?, performance_score=?, promotion_count=?
        WHERE id=?
    """, (name, age, gender, role, department, salary, doj, perf_score, promo_count, emp_id))
    conn.commit()
    conn.close()

def delete_employee_db(emp_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM employees WHERE id=?", (emp_id,))
    conn.commit()
    conn.close()

def promote_employee_db(emp_id, new_salary):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE employees SET salary=?, promotion_count = promotion_count + 1 WHERE id=?", (new_salary, emp_id))
    conn.commit()
    conn.close()

# -------------------------
# Utility: search & filters
# -------------------------
def filter_employees(df, name_role_search="", departments=None, salary_min=None, salary_max=None, perf_min=None, perf_max=None, doj_years=None):
    if name_role_search:
        mask = df['name'].str.contains(name_role_search, case=False, na=False) | df['role'].str.contains(name_role_search, case=False, na=False)
        df = df[mask]
    if departments:
        df = df[df['department'].isin(departments)]
    if salary_min is not None:
        df = df[df['salary'] >= salary_min]
    if salary_max is not None:
        df = df[df['salary'] <= salary_max]
    if perf_min is not None:
        df = df[df['performance_score'] >= perf_min]
    if perf_max is not None:
        df = df[df['performance_score'] <= perf_max]
    if doj_years:
        df['doj_year'] = pd.to_datetime(df['date_of_joining'], errors='coerce').dt.year
        df = df[df['doj_year'].between(doj_years[0], doj_years[1])]
        df = df.drop(columns=['doj_year'])
    return df

# -------------------------
# DB initialization / migration
# -------------------------
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            role TEXT,
            department TEXT,
            salary REAL,
            date_of_joining TEXT,
            performance_score INTEGER DEFAULT 3,
            promotion_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()

    # ensure columns exist (for older DBs)
    cur.execute("PRAGMA table_info(employees)")
    cols = [r[1] for r in cur.fetchall()]
    if 'performance_score' not in cols:
        cur.execute("ALTER TABLE employees ADD COLUMN performance_score INTEGER DEFAULT 3")
    if 'promotion_count' not in cols:
        cur.execute("ALTER TABLE employees ADD COLUMN promotion_count INTEGER DEFAULT 0")
    if 'date_of_joining' not in cols:
        cur.execute("ALTER TABLE employees ADD COLUMN date_of_joining TEXT")
    conn.commit()

    # Create default admin if no users
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        admin_user = "admin"
        admin_pass = "admin123"
        hashed = hash_password(admin_pass)
        try:
            cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (admin_user, hashed))
            conn.commit()
        except Exception:
            pass

    # Seed sample employees if table empty
    cur.execute("SELECT COUNT(*) FROM employees")
    if cur.fetchone()[0] == 0:
        sample = [
            ("Aarav Sharma", 28, "M", "Developer", "IT", 55000, "2021-06-15", 4, 1),
            ("Meera Patel", 32, "F", "HR Executive", "HR", 48000, "2019-03-20", 3, 0),
            ("Rohan Singh", 40, "M", "Finance Manager", "Finance", 70000, "2017-11-05", 5, 2),
            ("Priya Mehta", 25, "F", "Marketing Specialist", "Marketing", 45000, "2022-01-10", 3, 0),
            ("Arjun Desai", 30, "M", "Ops Lead", "Operations", 52000, "2020-09-01", 4, 1)
        ]
        cur.executemany("""
            INSERT INTO employees 
            (name, age, gender, role, department, salary, date_of_joining, performance_score, promotion_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample)
        conn.commit()
    conn.close()

# -------------------------
# Rerun helper
# -------------------------
def rerun_app():
    st.session_state['rerun_trigger'] = not st.session_state.get('rerun_trigger', False)
    st.stop()

# -------------------------
# Initialize DB & Session
# -------------------------
init_db()
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'rerun_trigger' not in st.session_state:
    st.session_state['rerun_trigger'] = False


# -------------------------
# Streamlit UI – Perfect centered header
# -------------------------
import streamlit as st

st.set_page_config(page_title="Work ForceT", layout="wide")

# ---------- Centered Header Section ----------
st.markdown(
    """
    <style>
        .header-container {
            text-align: center;
            margin-top: -30px;
            margin-bottom: 0px;
        }
        .header-title {
            font-size: 45px;
            font-weight: 700;
        }
        .header-tagline {
            font-size: 18px;
            color: #bbbbbb;
            margin-top: -10px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

with st.container():
    st.markdown('<div class="header-container">', unsafe_allow_html=True)

    # Load the logo properly using Streamlit
    st.image("logo.png", width=120)

    st.markdown('<div class="header-title">Work ForceT</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-tagline">A Dashboard That Thinks Like a Manager!</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)






# --- Authentication Panel
def login_panel():
    st.sidebar.header("🔐 Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if authenticate_user(username, password):
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            rerun_app()
        else:
            st.sidebar.error("Invalid credentials")
    st.sidebar.markdown("---")
    st.sidebar.write("New user? Register below")
    new_user = st.sidebar.text_input("New username")
    new_pass = st.sidebar.text_input("New password", type="password")
    if st.sidebar.button("Register"):
        if new_user.strip() == "" or new_pass.strip() == "":
            st.sidebar.error("Provide username & password")
        else:
            ok = create_user(new_user.strip(), new_pass.strip())
            if ok:
                st.sidebar.success("User created — please login")
            else:
                st.sidebar.error("Username taken")

def logout():
    st.session_state['logged_in'] = False
    st.session_state['username'] = None
    rerun_app()

if not st.session_state['logged_in']:
    login_panel()
    st.stop()
else:
    st.sidebar.success(f"Logged in as {st.session_state['username']}")
    if st.sidebar.button("Logout"):
        logout()

# -------------------------
# Main menu
# -------------------------
menu = ["Dashboard", "Add Employee", "View / Search Employees", "Update Employee", "Promote Employee", "Delete Employee"]
choice = st.sidebar.radio("Menu", menu)

# -------------------------
# -------------------------
# Dashboard Page (Modern & Interactive)
# -------------------------
if choice == "Dashboard":
    st.header("📊 HR Analytics Dashboard")
    
    df = get_all_employees_df()
    if df.empty:
        st.info("No employee data available.")
    else:
        # Sidebar filters for Dashboard
        st.sidebar.markdown("### Filter Dashboard")
        departments = st.sidebar.multiselect(
            "Departments",
            options=sorted(df['department'].dropna().unique()),
            default=sorted(df['department'].dropna().unique())
        )
        df_filtered = df[df['department'].isin(departments)]
        
        # KPIs
        total_emp = len(df_filtered)
        avg_salary = df_filtered['salary'].mean()
        avg_perf = df_filtered['performance_score'].mean()
        total_promotions = df_filtered['promotion_count'].sum()

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("👥 Total Employees", total_emp, delta=f"{total_emp - len(df)} change")
        kpi2.metric("💰 Average Salary", f"₹{avg_salary:,.0f}", delta="+3%")
        kpi3.metric("🏆 Avg Performance", f"{avg_perf:.2f}/5", delta="-0.2")
        kpi4.metric("🎉 Total Promotions", int(total_promotions), delta="+1")
        st.markdown("---")
        
        # Employees by Department
        fig_dept = px.bar(
            df_filtered, 
            x='department', 
            y='id', 
            color='department',
            labels={'id':'Number of Employees'},
            title="👔 Employees by Department"
        )
        st.plotly_chart(fig_dept, use_container_width=True)

        # Average Salary by Department
        avg_by_dept_df = df_filtered.groupby('department')['salary'].mean().reset_index()
        fig_salary = px.bar(
            avg_by_dept_df,
            x='department',
            y='salary',
            color='salary',
            color_continuous_scale='Blues',
            labels={'salary':'Avg Salary'},
            title="💵 Average Salary by Department"
        )
        st.plotly_chart(fig_salary, use_container_width=True)

        # Salary Distribution
        fig_salary_dist = px.histogram(
            df_filtered,
            x='salary',
            nbins=10,
            labels={'salary':'Salary'},
            title="📈 Salary Distribution"
        )
        st.plotly_chart(fig_salary_dist, use_container_width=True)

        # Performance vs Salary Bubble Chart
        fig_perf = px.scatter(
            df_filtered,
            x='performance_score',
            y='salary',
            size='promotion_count',
            color='department',
            hover_data=['name','role'],
            title="⚡ Performance vs Salary (Bubble = Promotions)"
        )
        st.plotly_chart(fig_perf, use_container_width=True)

# -------------------------
# Add Employee Page
# -------------------------
elif choice == "Add Employee":
    st.header("➕ Add New Employee")
    with st.form("add_form"):
        name = st.text_input("Full name")
        age = st.number_input("Age", min_value=18, max_value=70, value=25)
        gender = st.selectbox("Gender", options=["M","F","Other"])
        role = st.text_input("Role / Title")
        department = st.text_input("Department")
        salary = st.number_input("Salary", min_value=0.0, value=30000.0)
        doj = st.date_input("Date of Joining", value=date.today()).isoformat()
        perf = st.slider("Performance Score", 1, 5, value=3)
        submitted = st.form_submit_button("Add Employee")
    if submitted:
        if name.strip() == "" or department.strip() == "":
            st.error("Name and Department are required")
        else:
            add_employee_db(name.strip(), age, gender, role.strip(), department.strip(), salary, doj, perf)
            st.success(f"Employee {name} added")
            rerun_app()

# -------------------------
# View / Search Employees Page
# -------------------------
elif choice == "View / Search Employees":
    st.header("🔎 View & Search Employees")
    df = get_all_employees_df()
    if df.empty:
        st.info("No data")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            search_text = st.text_input("Search by name or role")
            depts = sorted(df['department'].dropna().unique().tolist())
            dept_filter = st.multiselect("Department", options=depts, default=depts)
        with col2:
            min_salary = float(df['salary'].min())
            max_salary = float(df['salary'].max())
            salary_range = st.slider("Salary Range", min_value=min_salary, max_value=max_salary, value=(min_salary, max_salary))
        with col3:
            perf_range = st.slider("Performance Score", 1, 5, value=(1,5))
            doj_years = st.slider("Joining Year Range", int(pd.to_datetime(df['date_of_joining'], errors='coerce').dt.year.min()), int(pd.to_datetime(df['date_of_joining'], errors='coerce').dt.year.max()), value=(2015, datetime.now().year))

        filtered = filter_employees(df.copy(),
                                    name_role_search=search_text,
                                    departments=dept_filter,
                                    salary_min=salary_range[0],
                                    salary_max=salary_range[1],
                                    perf_min=perf_range[0],
                                    perf_max=perf_range[1],
                                    doj_years=doj_years)

        st.write(f"Showing {len(filtered)} records")
        st.dataframe(filtered.reset_index(drop=True))

        csv = filtered.to_csv(index=False)
        st.download_button(label="Download filtered CSV", data=csv, file_name="employees_filtered.csv", mime="text/csv")

# -------------------------
# Update Employee Page
# -------------------------
elif choice == "Update Employee":
    st.header("✏️ Update Employee")
    df = get_all_employees_df()
    if df.empty:
        st.info("No data")
    else:
        options = df.apply(lambda row: f"{row['id']} - {row['name']}", axis=1).tolist()
        selection = st.selectbox("Select Employee", options)
        emp_id = int(selection.split(" - ")[0])
        emp = df[df['id'] == emp_id].iloc[0]

        with st.form("update_form"):
            name = st.text_input("Name", value=emp['name'])
            age = st.number_input("Age", min_value=18, max_value=70, value=int(emp['age']))
            gender = st.selectbox("Gender", options=["M","F","Other"], index=0 if emp.get('gender','M')=="M" else 1)
            role = st.text_input("Role", value=emp.get('role',''))
            department = st.text_input("Department", value=emp.get('department',''))
            salary = st.number_input("Salary", min_value=0.0, value=float(emp.get('salary',0.0)))
            doj_val = emp.get('date_of_joining', date.today().isoformat())
            try:
                doj_default = datetime.fromisoformat(doj_val).date()
            except Exception:
                doj_default = date.today()
            doj = st.date_input("Date of Joining", value=doj_default)
            perf = st.slider("Performance Score", 1, 5, value=int(emp.get('performance_score',3)))
            promo = st.number_input("Promotion Count", min_value=0, value=int(emp.get('promotion_count',0)))
            submitted = st.form_submit_button("Update")

        if submitted:
            update_employee_db(emp_id, name.strip(), age, gender, role.strip(), department.strip(), salary, doj.isoformat(), perf, promo)
            st.success("Employee updated")
            rerun_app()

# -------------------------
# Promote Employee Page
# -------------------------
elif choice == "Promote Employee":
    st.header("🚀 Promote Employee")
    df = get_all_employees_df()
    if df.empty:
        st.info("No data")
    else:
        options = df.apply(lambda row: f"{row['id']} - {row['name']} ({row['department']}) - ₹{row['salary']}", axis=1).tolist()
        selection = st.selectbox("Choose Employee", options)
        emp_id = int(selection.split(" - ")[0])
        current_salary = float(df[df['id']==emp_id]['salary'].iloc[0])
        st.write(f"Current salary: ₹{current_salary:,.0f}")
        new_salary = st.number_input("New Salary", min_value=current_salary, value=current_salary+5000.0)
        if st.button("Promote"):
            promote_employee_db(emp_id, new_salary)
            st.success("Operation completed successfully!", icon="✅")
# -------------------------
# Delete Employee Page
# -------------------------
elif choice == "Delete Employee":
    st.header("🗑️ Delete Employee")
    df = get_all_employees_df()
    if df.empty:
        st.info("No data")
    else:
        options = df.apply(lambda row: f"{row['id']} - {row['name']}", axis=1).tolist()
        selection = st.selectbox("Select Employee to delete", options)
        emp_id = int(selection.split(" - ")[0])
        if st.button("Delete"):
            delete_employee_db(emp_id)
            st.success("Employee deleted")
            st.experimental_rerun()


