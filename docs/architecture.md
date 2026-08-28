User → Streamlit UI (main.py)
→ Authentication
	↳ Face Recognition (OpenCV + Dlib)
	↳ Aadhaar + Ration ID Fallback
→ Dashboards
	↳ Customer Dashboard
	↳ Shopkeeper Dashboard
	↳ Government Dashboard (Aakash)
→ Registration Module
	↳ Save user details + embeddings
	↳ Store in SQLite DB
→ Billing Module
	↳ Commodity Input → Bill PDF
	↳ Save in /bills
→ Fraud Engine
	↳ Sachin’s ANN model (fraud\_model.pkl)
	↳ fraud\_predictor.py (ML layer)
	↳ fraud\_rules.py (rule-based checks)
	↳ Final decision (Fraud / Safe)
→ Database Layer (SQLite)
	↳ db\_ops.py handles CRUD
→ Alerts Engine
	↳ 30% ration remaining alert
	↳ notifications.py

