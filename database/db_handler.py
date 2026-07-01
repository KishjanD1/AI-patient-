import sqlite3
from typing import List, Dict, Any
import os
from contextlib import contextmanager

DB_NAME = "appointments.db"

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_available_doctors() -> List[Dict[str, str]]:
    """Returns a list of all doctors and their specialties."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, specialty FROM doctors")
        return [{"name": row['name'], "specialty": row['specialty']} for row in cursor.fetchall()]

def get_all_appointments() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, doctor_id, date, time, patient_name, email, status FROM appointments")
        rows = cursor.fetchall()
        
        appointments = []
        for row in rows:
            appointments.append({
                "id": row['id'],
                "doctor_id": row['doctor_id'],
                "date": row['date'],
                "time": row['time'],
                "patient_name": row['patient_name'],
                "email": row['email'],
                "status": row['status']
            })
        return appointments

def get_appointments_by_patient(patient_id: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, doctor_id, date, time, patient_name, email, status FROM appointments WHERE email = ?", (patient_id,))
        rows = cursor.fetchall()
        
        appointments = []
        for row in rows:
            appointments.append({
                "id": row['id'],
                "doctor_id": row['doctor_id'],
                "date": row['date'],
                "time": row['time'],
                "patient_name": row['patient_name'],
                "email": row['email'],
                "status": row['status']
            })
        return appointments

def setup_database():
    """Initializes the database schema and populates mock data if empty."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create doctors table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                specialty TEXT NOT NULL
            )
        ''')
        
        # Create available slots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS available_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id INTEGER,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                is_booked INTEGER DEFAULT 0,
                FOREIGN KEY (doctor_id) REFERENCES doctors (id)
            )
        ''')
        
        # Create appointments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id INTEGER,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                patient_name TEXT,
                email TEXT,
                status TEXT DEFAULT 'CONFIRMED',
                FOREIGN KEY (doctor_id) REFERENCES doctors (id)
            )
        ''')
        
        # Ensure email column exists if upgrading old DB
        try:
            cursor.execute('ALTER TABLE appointments ADD COLUMN email TEXT')
        except sqlite3.OperationalError:
            pass
            
        # Create episodic memories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS episodic_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                fact TEXT NOT NULL
            )
        ''')
        
        # Populate initial data if empty
        cursor.execute("SELECT COUNT(*) FROM doctors")
        if cursor.fetchone()[0] == 0:
            print("Populating initial database with mock doctors and slots...")
            # Insert Doctors
            cursor.execute("INSERT INTO doctors (name, specialty) VALUES (?, ?)", ("Dr. Smith", "Cardiology"))
            smith_id = cursor.lastrowid
            cursor.execute("INSERT INTO doctors (name, specialty) VALUES (?, ?)", ("Dr. Jones", "Dermatology"))
            jones_id = cursor.lastrowid
            cursor.execute("INSERT INTO doctors (name, specialty) VALUES (?, ?)", ("Dr. Adams", "Neurology"))
            adams_id = cursor.lastrowid
            
            # Insert Slots for Dr. Smith
            smith_slots = [
                ("2026-07-01", "09:00 AM"), ("2026-07-01", "10:30 AM"), ("2026-07-01", "11:15 AM"),
                ("2026-07-02", "14:00 PM"), ("2026-07-02", "15:30 PM")
            ]
            for date, time in smith_slots:
                cursor.execute("INSERT INTO available_slots (doctor_id, date, time) VALUES (?, ?, ?)", (smith_id, date, time))
                
            # Insert Slots for Dr. Jones
            jones_slots = [
                ("2026-07-01", "10:00 AM"), ("2026-07-01", "13:00 PM"),
                ("2026-07-03", "09:30 AM"), ("2026-07-03", "11:00 AM")
            ]
            for date, time in jones_slots:
                cursor.execute("INSERT INTO available_slots (doctor_id, date, time) VALUES (?, ?, ?)", (jones_id, date, time))
                
            # Insert Slots for Dr. Adams (Neurology)
            adams_slots = [
                ("2026-07-01", "09:00 AM"), ("2026-07-01", "14:00 PM"),
                ("2026-07-02", "10:00 AM"), ("2026-07-02", "11:30 AM")
            ]
            for date, time in adams_slots:
                cursor.execute("INSERT INTO available_slots (doctor_id, date, time) VALUES (?, ?, ?)", (adams_id, date, time))
                
        conn.commit()

def check_doctor_exists(doctor_name: str) -> bool:
    """Checks if a doctor exists in the database by partial name match."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM doctors WHERE LOWER(name) LIKE ?", (f"%{doctor_name.lower()}%",))
        return cursor.fetchone() is not None

def check_slot_availability(doctor_name: str, date: str, time: str):
    """
    Checks if a slot is available in SQLite. 
    Returns (is_available, alternative_slots_list).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Find doctor
        cursor.execute("SELECT id FROM doctors WHERE LOWER(name) LIKE ?", (f"%{doctor_name.lower()}%",))
        doctor = cursor.fetchone()
        if not doctor:
            return False, []
        doctor_id = doctor['id']
        
        # Check specific slot
        cursor.execute('''
            SELECT id FROM available_slots 
            WHERE doctor_id = ? AND date = ? AND time = ? AND is_booked = 0
        ''', (doctor_id, date, time))
        
        if cursor.fetchone():
            return True, []
            
        # If not available, fetch 3 alternatives for that doctor on that date (or future dates)
        cursor.execute('''
            SELECT date, time FROM available_slots 
            WHERE doctor_id = ? AND date >= ? AND is_booked = 0
            ORDER BY date ASC, time ASC LIMIT 3
        ''', (doctor_id, date))
        
        alternatives = [f"{row['date']} at {row['time']}" for row in cursor.fetchall()]
        return False, alternatives

def get_doctor_schedule(doctor_name: str, date: str) -> List[str]:
    """Returns all available time slots for a doctor on a specific date."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Find doctor
        cursor.execute("SELECT id FROM doctors WHERE LOWER(name) LIKE ?", (f"%{doctor_name.lower()}%",))
        doctor = cursor.fetchone()
        if not doctor:
            return []
        doctor_id = doctor['id']
        
        cursor.execute('''
            SELECT time FROM available_slots 
            WHERE doctor_id = ? AND date = ? AND is_booked = 0
            ORDER BY time ASC
        ''', (doctor_id, date))
        
        return [row['time'] for row in cursor.fetchall()]

def book_appointment(doctor_name: str, date: str, time: str, patient_name: str = "Test Patient", email: str = None):
    """
    Executes the booking deterministically by updating the DB.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Find doctor
        cursor.execute("SELECT id FROM doctors WHERE LOWER(name) LIKE ?", (f"%{doctor_name.lower()}%",))
        doctor = cursor.fetchone()
        if not doctor:
            raise ValueError(f"Doctor {doctor_name} not found.")
        doctor_id = doctor['id']
        
        # Mark slot as booked
        cursor.execute('''
            UPDATE available_slots SET is_booked = 1
            WHERE doctor_id = ? AND date = ? AND time = ?
        ''', (doctor_id, date, time))
        
        # Insert appointment record
        cursor.execute('''
            INSERT INTO appointments (doctor_id, date, time, patient_name, email, status)
            VALUES (?, ?, ?, ?, ?, 'CONFIRMED')
        ''', (doctor_id, date, time, patient_name, email))
        
        appointment_id = cursor.lastrowid
        conn.commit()
        return appointment_id

def get_appointment_details(appointment_id: int) -> Dict[str, Any]:
    """Returns appointment details including the doctor's name."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, a.date, a.time, a.status, d.name as doctor_name 
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.id = ?
        ''', (appointment_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)

def cancel_appointment(appointment_id: int) -> bool:
    """Cancels an appointment and frees the slot."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get appointment details
        cursor.execute("SELECT doctor_id, date, time, status FROM appointments WHERE id = ?", (appointment_id,))
        appt = cursor.fetchone()
        if not appt or appt['status'] == 'CANCELLED':
            return False
            
        # Update appointment status
        cursor.execute("UPDATE appointments SET status = 'CANCELLED' WHERE id = ?", (appointment_id,))
        
        # Free slot
        cursor.execute('''
            UPDATE available_slots SET is_booked = 0
            WHERE doctor_id = ? AND date = ? AND time = ?
        ''', (appt['doctor_id'], appt['date'], appt['time']))
        
        conn.commit()
        return True

def reschedule_appointment(appointment_id: int, new_date: str, new_time: str) -> bool:
    """Reschedules an appointment by changing slot and time."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get current appointment
        cursor.execute("SELECT doctor_id, date, time, status FROM appointments WHERE id = ?", (appointment_id,))
        appt = cursor.fetchone()
        if not appt or appt['status'] == 'CANCELLED':
            return False
            
        doctor_id = appt['doctor_id']
        old_date = appt['date']
        old_time = appt['time']
        
        # Check if new slot is available
        cursor.execute('''
            SELECT id FROM available_slots 
            WHERE doctor_id = ? AND date = ? AND time = ? AND is_booked = 0
        ''', (doctor_id, new_date, new_time))
        
        if not cursor.fetchone():
            return False # Slot not available
            
        # Free old slot
        cursor.execute('''
            UPDATE available_slots SET is_booked = 0
            WHERE doctor_id = ? AND date = ? AND time = ?
        ''', (doctor_id, old_date, old_time))
        
        # Book new slot
        cursor.execute('''
            UPDATE available_slots SET is_booked = 1
            WHERE doctor_id = ? AND date = ? AND time = ?
        ''', (doctor_id, new_date, new_time))
        
        # Update appointment
        cursor.execute('''
            UPDATE appointments SET date = ?, time = ? WHERE id = ?
        ''', (new_date, new_time, appointment_id))
        
        conn.commit()
        return True

if __name__ == "__main__":
    setup_database()
    print("Database setup complete.")

def save_episodic_memory(patient_id: str, fact: str):
    """Saves a fact into the episodic memory for a session/user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO episodic_memories (patient_id, fact) VALUES (?, ?)", (patient_id, fact))
        conn.commit()

def get_episodic_memories(patient_id: str) -> List[str]:
    """Retrieves all episodic memories for a session/user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT fact FROM episodic_memories WHERE patient_id = ?", (patient_id,))
        return [row['fact'] for row in cursor.fetchall()]
