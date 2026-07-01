from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import json

import os
from database.db_handler import setup_database, get_all_appointments, cancel_appointment, reschedule_appointment, get_episodic_memories, get_appointments_by_patient
from core.session_manager import session_manager
from core.security import security_manager

app = FastAPI(title="AI Patient Appointment API", description="REST API for the appointment booking system")

app.mount("/static", StaticFiles(directory="static"), name="static")
from pathlib import Path

# Request Models
class ChatRequest(BaseModel):
    patient_id: str
    message: str = Field(..., max_length=500, description="The user's message, limited to 500 chars to prevent buffer attacks.")

class ChatResponse(BaseModel):
    reply: str
    state: str

class RescheduleRequest(BaseModel):
    date: str
    time: str

@app.on_event("startup")
def on_startup():
    print("Initializing Database...")
    setup_database()

@app.get("/", response_class=HTMLResponse)
async def chat_ui(request: Request):
    return HTMLResponse(Path("templates/index.html").read_text())

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_ui(request: Request):
    return HTMLResponse(Path("templates/dashboard.html").read_text())

@app.get("/api/appointments")
def fetch_appointments():
    return {"appointments": get_all_appointments()}

@app.delete("/api/appointments/{id}")
def delete_appointment(id: int):
    if cancel_appointment(id):
        return {"status": "success", "message": "Appointment cancelled"}
    raise HTTPException(status_code=404, detail="Appointment not found or already cancelled")

@app.put("/api/appointments/{id}")
def update_appointment(id: int, request: RescheduleRequest):
    if reschedule_appointment(id, request.date, request.time):
        return {"status": "success", "message": "Appointment rescheduled"}
    raise HTTPException(status_code=400, detail="Failed to reschedule. Slot might be unavailable or appointment not found.")

@app.get("/api/logs")
def get_logs(patient_id: str = ""):
    log_path = "logs/agent_observability.log"
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if patient_id:
                target = f"[{patient_id}]"
                lines = [line for line in lines if target in line]
            return {"logs": "".join(lines[-50:])}
    return {"logs": "No logs found."}

@app.get("/api/db_state")
def get_db_state(patient_id: str = "guest@example.com"):
    appointments = get_appointments_by_patient(patient_id)
    memories = get_episodic_memories(patient_id)
    return {"appointments": appointments, "memories": memories}

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    patient_id = request.patient_id
    user_input = request.message
    
    # Layer 1.5: Semantic Firewall Check
    if not security_manager.is_safe(user_input):
        raise HTTPException(status_code=403, detail="Security violation detected. Request blocked.")
    
    # Let LLM agent handle the turn
    from agents.llm_service import chat_with_agent
    reply = chat_with_agent(patient_id, user_input)
    
    return ChatResponse(reply=reply, state="CHAT")

if __name__ == "__main__":
    import uvicorn
    print("=========================================")
    print("   AI Patient Appointment System (API)   ")
    print("=========================================")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
