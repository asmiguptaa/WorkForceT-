# Work ForceT - Employee Management System

A **Streamlit-based HR dashboard** to manage employees with secure login, CRUD operations, filters, and analytics.

---

## Features

- **Authentication:** Login/Register with password hashing  
- **Employee Management:** Add, view, update, promote, delete  
- **Filters & Search:** By name, role, department, salary, performance, joining year  
- **Analytics Dashboard:**  
  - Total employees, avg salary, avg performance, total promotions  
  - Department-wise employee count & salary  
  - Salary distribution & performance vs salary charts  
- **CSV Export:** Download filtered employee data  
- **Demo Credentials:** `admin` / `admin123`

---

## Installation

```bash
git clone https://github.com/yourusername/work-forcet.git
cd work-forcet
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
