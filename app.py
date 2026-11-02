import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime

DB = "attendance_demo.db"
st.set_page_config(page_title="Institute Attendance System", page_icon="📚", layout="wide")

def conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS departments(id INTEGER PRIMARY KEY, name TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS faculty(id INTEGER PRIMARY KEY, name TEXT, role TEXT, department_id INTEGER);
        CREATE TABLE IF NOT EXISTS divisions(id INTEGER PRIMARY KEY, name TEXT, department_id INTEGER);
        CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY, roll TEXT UNIQUE, name TEXT, division_id INTEGER, tg_id INTEGER);
        CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY, code TEXT, name TEXT, division_id INTEGER, teacher_id INTEGER);
        CREATE TABLE IF NOT EXISTS lectures(id INTEGER PRIMARY KEY, course_id INTEGER, lecture_date TEXT, topic TEXT, status TEXT DEFAULT 'completed', UNIQUE(course_id, lecture_date, topic));
        CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY, lecture_id INTEGER, student_id INTEGER, status TEXT, marked_by INTEGER, marked_at TEXT, UNIQUE(lecture_id, student_id));
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, attendance_id INTEGER, old_status TEXT, new_status TEXT, changed_by INTEGER, changed_at TEXT, reason TEXT);
        """)
        if c.execute("SELECT COUNT(*) FROM departments").fetchone()[0] == 0:
            depts = ["Computer Engineering","Information Technology","Mechanical Engineering","Civil Engineering","Electronics Engineering","Electrical Engineering"]
            for d in depts: c.execute("INSERT INTO departments(name) VALUES(?)",(d,))
            faculty = []
            for i in range(1, 7):
                c.execute("INSERT INTO faculty(name,role,department_id) VALUES(?,?,?)",(f"Head {i}","HOD",i))
                hod = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                c.execute("INSERT INTO faculty(name,role,department_id) VALUES(?,?,?)",(f"Class Teacher {i}","Class Teacher",i))
                ct = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                c.execute("INSERT INTO faculty(name,role,department_id) VALUES(?,?,?)",(f"Course Teacher {i}","Course Teacher",i))
                teacher = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                c.execute("INSERT INTO faculty(name,role,department_id) VALUES(?,?,?)",(f"Teacher Guardian {i}","TG",i))
                tg = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                c.execute("INSERT INTO divisions(name,department_id) VALUES(?,?)",(f"SE-A",i))
                div = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                for j in range(1, 11):
                    c.execute("INSERT INTO students(roll,name,division_id,tg_id) VALUES(?,?,?,?)",(f"{i}A{j:02d}",f"Student {i}-{j}",div,tg))
                for k, course in enumerate(["Database Management","Data Structures","Mathematics","Operating Systems","Programming"],1):
                    c.execute("INSERT INTO courses(code,name,division_id,teacher_id) VALUES(?,?,?,?)",(f"D{i}C{k}",course,div,teacher))
                    course_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                    for day in range(1, 6):
                        c.execute("INSERT INTO lectures(course_id,lecture_date,topic) VALUES(?,?,?)",(course_id,f"2026-10-{day:02d}",f"Lecture {day}"))
                        lecture_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                        students = c.execute("SELECT id FROM students WHERE division_id=?",(div,)).fetchall()
                        for (sid,) in students:
                            status = "Present" if (sid + day + k) % 5 != 0 else "Absent"
                            c.execute("INSERT INTO attendance(lecture_id,student_id,status,marked_by,marked_at) VALUES(?,?,?,?,?)",(lecture_id,sid,status,teacher,datetime.now().isoformat(timespec="seconds")))
        c.commit()

init_db()

def df(query, params=()):
    with conn() as c:
        return pd.read_sql_query(query, c, params=params)

def run(query, params=()):
    with conn() as c:
        cur = c.execute(query, params)
        c.commit()
        return cur.lastrowid

st.title("📚 Centralized Attendance Management System")
st.caption("Engineering Institute | Six-department demonstration")

accounts = {
    "Admin": ("admin", "admin123"),
    "Course Teacher": ("teacher", "teacher123"),
    "Teacher Guardian": ("tg", "tg123"),
    "Class Teacher": ("classteacher", "class123"),
    "HOD": ("hod", "hod123"),
    "Student": ("student", "student123")
}
with st.sidebar:
    st.header("Demo Login")
    role = st.selectbox("Login as", list(accounts))
    username = st.text_input("Username", value=accounts[role][0])
    password = st.text_input("Password", value=accounts[role][1], type="password")
    st.caption("Demo credentials are shown above for convenience.")
    login = st.button("Login", type="primary", use_container_width=True)

    if "logged_role" not in st.session_state:
        st.session_state.logged_role = None
    if login:
        if (username, password) == accounts[role]:
            st.session_state.logged_role = role
            st.success("Login successful")
        else:
            st.error("Invalid demo credentials")
    active_role = st.session_state.logged_role
    if active_role:
        st.success(f"Active role: {active_role}")
        if st.button("Logout"):
            st.session_state.logged_role = None
            st.rerun()

if not st.session_state.get("logged_role"):
    st.info("Choose a demo role and click Login. The database is preloaded with six departments and sample attendance.")
    a,b,c = st.columns(3)
    a.metric("Departments", 6)
    b.metric("Sample students", 60)
    c.metric("Sample courses", 30)
    st.subheader("Available modules")
    st.write("Admin • Course Teacher • Teacher Guardian • Class Teacher • HOD • Student")
    st.stop()

role = st.session_state.logged_role
fac = df("SELECT * FROM faculty ORDER BY id")
depts = df("SELECT * FROM departments")
students = df("""SELECT s.*, d.name AS division, dep.name AS department
                 FROM students s JOIN divisions d ON s.division_id=d.id
                 JOIN departments dep ON d.department_id=dep.id ORDER BY s.roll""")
if role == "Admin":
    st.subheader("Administrator Dashboard")
    x,y,z = st.columns(3)
    x.metric("Departments", len(depts))
    y.metric("Students", len(students))
    z.metric("Attendance records", int(df("SELECT COUNT(*) n FROM attendance").iloc[0,0]))
    st.dataframe(depts, use_container_width=True, hide_index=True)
    st.subheader("Student directory")
    st.dataframe(students[["roll","name","division","department"]], use_container_width=True, hide_index=True)
    st.subheader("Faculty directory")
    st.dataframe(fac, use_container_width=True, hide_index=True)

elif role == "Course Teacher":
    st.subheader("Course Teacher – Mark Attendance")
    teacher_id = int(df("SELECT id FROM faculty WHERE role='Course Teacher' ORDER BY id LIMIT 1").iloc[0,0])
    courses = df("""SELECT c.id,c.code,c.name,d.name division FROM courses c
                    JOIN divisions d ON c.division_id=d.id WHERE c.teacher_id=?""",(teacher_id,))
    if courses.empty:
        st.warning("No course allocation found.")
    else:
        selected = st.selectbox("Select course", courses["id"], format_func=lambda v: courses.loc[courses.id==v,"code"].iloc[0]+" – "+courses.loc[courses.id==v,"name"].iloc[0])
        lecture_day = st.date_input("Lecture date", value=date.today())
        topic = st.text_input("Lecture/topic", "Regular lecture")
        roster = df("SELECT id,roll,name FROM students WHERE division_id=(SELECT division_id FROM courses WHERE id=?) ORDER BY roll",(int(selected),))
        st.write(f"**Student roster: {len(roster)} students**")
        key = f"attendance_{selected}_{lecture_day}"
        if key not in st.session_state:
            st.session_state[key] = {int(r.id): "Present" for r in roster.itertuples()}
        marked = []
        for r in roster.itertuples():
            val = st.selectbox(f"{r.roll} — {r.name}", ["Present","Absent","Late"], key=f"{key}_{r.id}", index=0)
            marked.append((int(r.id),val))
        if st.button("Submit attendance", type="primary"):
            try:
                with conn() as c:
                    cur = c.execute("INSERT INTO lectures(course_id,lecture_date,topic) VALUES(?,?,?)",(int(selected),str(lecture_day),topic))
                    lid = cur.lastrowid
                    for sid,status in marked:
                        c.execute("INSERT INTO attendance(lecture_id,student_id,status,marked_by,marked_at) VALUES(?,?,?,?,?)",(lid,sid,status,teacher_id,datetime.now().isoformat(timespec="seconds")))
                    c.commit()
                st.success("Attendance submitted successfully.")
            except sqlite3.IntegrityError:
                st.error("A lecture with this course, date and topic already exists. Change the topic or date to avoid duplicate submission.")
    st.subheader("Recent submissions")
    st.dataframe(df("""SELECT l.lecture_date,c.code,c.name,l.topic,COUNT(a.id) students
                       FROM lectures l JOIN courses c ON c.id=l.course_id
                       LEFT JOIN attendance a ON a.lecture_id=l.id
                       WHERE c.teacher_id=? GROUP BY l.id ORDER BY l.lecture_date DESC LIMIT 20""",(teacher_id,)),use_container_width=True,hide_index=True)

elif role in ("Teacher Guardian","Class Teacher","HOD","Student"):
    if role == "Teacher Guardian":
        st.subheader("Teacher Guardian – Assigned Students")
        tg_id = int(df("SELECT id FROM faculty WHERE role='TG' ORDER BY id LIMIT 1").iloc[0,0])
        scope = students[students.tg_id == tg_id]
    elif role == "Class Teacher":
        st.subheader("Class Teacher – Division Monitoring")
        ct_id = int(df("SELECT id FROM faculty WHERE role='Class Teacher' ORDER BY id LIMIT 1").iloc[0,0])
        scope = students[students.department == "Computer Engineering"]
    elif role == "HOD":
        st.subheader("HOD – Department Analytics")
        hod_dept = st.selectbox("Department", depts.name.tolist())
        scope = students[students.department == hod_dept]
    else:
        st.subheader("Student – My Attendance")
        student_pick = st.selectbox("Select demo student", students.name.tolist())
        scope = students[students.name == student_pick]

    if not scope.empty:
        ids = tuple(int(x) for x in scope.id.tolist())
        placeholders = ",".join("?" for _ in ids)
        report = df(f"""SELECT s.roll,s.name,c.code,c.name course,
                    COUNT(a.id) total,
                    SUM(CASE WHEN a.status IN ('Present','Late') THEN 1 ELSE 0 END) attended,
                    ROUND(100.0*SUM(CASE WHEN a.status IN ('Present','Late') THEN 1 ELSE 0 END)/NULLIF(COUNT(a.id),0),2) percentage
                    FROM students s JOIN attendance a ON a.student_id=s.id
                    JOIN lectures l ON l.id=a.lecture_id JOIN courses c ON c.id=l.course_id
                    WHERE s.id IN ({placeholders})
                    GROUP BY s.id,c.id ORDER BY percentage ASC""",ids)
        if role == "Student":
            report = report[report.name == student_pick]
        st.metric("Students in scope", len(scope))
        if not report.empty:
            avg = report.percentage.mean()
            st.metric("Average course attendance", f"{avg:.1f}%")
            low = report[report.percentage < 75]
            st.metric("Below 75% course records", len(low))
            st.dataframe(report,use_container_width=True,hide_index=True)
            if not low.empty:
                st.warning("Students requiring attention: attendance below 75%.")
        else:
            st.info("No attendance data available for this selection.")

st.divider()
st.caption("Academic demo only. Sample identities and records are fictional. For real deployment, add secure authentication, per-user authorization, persistent managed storage, and institutional data protection.")
