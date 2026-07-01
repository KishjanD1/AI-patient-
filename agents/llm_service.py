import json
import logging
import os
import time
from datetime import datetime
from pydantic import BaseModel, ValidationError
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL
from core.session_manager import session_manager
from database.db_handler import (
    get_available_doctors,
    get_doctor_schedule,
    check_slot_availability,
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
    save_episodic_memory
)

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/agent_observability.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)
logger = logging.getLogger("agent_observability")

class CheckSlotSchema(BaseModel):
    doctor_name: str
    date: str
    time: str

class GetDoctorScheduleSchema(BaseModel):
    doctor_name: str
    date: str

class BookAppointmentSchema(BaseModel):
    doctor_name: str
    date: str
    time: str
    patient_name: str
    email: str

class CancelAppointmentSchema(BaseModel):
    appointment_id: int

class RescheduleAppointmentSchema(BaseModel):
    appointment_id: int
    new_date: str
    new_time: str

class SaveEpisodicMemorySchema(BaseModel):
    fact: str

client = Groq(api_key=GROQ_API_KEY)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_available_doctors",
            "description": "Returns a list of all doctors and their specialties.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_doctor_schedule",
            "description": "Returns a list of all available time slots for a specific doctor on a specific date. Use this when the user asks for a doctor's availability on a certain day without specifying a time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"}
                },
                "required": ["doctor_name", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_slot_availability",
            "description": "Checks if a specific slot is available. DO NOT call this tool unless the user has explicitly provided a specific time. Do not guess or invent a time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time": {"type": "string", "description": "HH:MM AM/PM"}
                },
                "required": ["doctor_name", "date", "time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Books an appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "patient_name": {"type": "string"},
                    "email": {"type": "string"}
                },
                "required": ["doctor_name", "date", "time", "patient_name", "email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancels an appointment by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "integer"}
                },
                "required": ["appointment_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_appointment",
            "description": "Reschedules an appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "integer"},
                    "new_date": {"type": "string"},
                    "new_time": {"type": "string"}
                },
                "required": ["appointment_id", "new_date", "new_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_episodic_memory",
            "description": "Saves an important fact about the patient for long-term memory across sessions. Use this when the patient mentions personal preferences, recurring symptoms, or their email address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {"type": "string", "description": "The fact to remember."}
                },
                "required": ["fact"]
            }
        }
    }
]

def execute_function(name: str, args: dict, patient_id: str):
    try:
        if name == "get_available_doctors":
            return get_available_doctors()
        elif name == "get_doctor_schedule":
            return get_doctor_schedule(args["doctor_name"], args["date"])
        elif name == "check_slot_availability":
            is_avail, alts = check_slot_availability(args["doctor_name"], args["date"], args["time"])
            return {"is_available": is_avail, "alternatives": alts}
        elif name == "book_appointment":
            appt_id = book_appointment(args["doctor_name"], args["date"], args["time"], args.get("patient_name", "Patient"), args.get("email"))
            return {"status": "success", "appointment_id": appt_id, "message": "Appointment booked successfully"}
        elif name == "cancel_appointment":
            res = cancel_appointment(args["appointment_id"])
            return {"status": "success" if res else "failed"}
        elif name == "reschedule_appointment":
            res = reschedule_appointment(args["appointment_id"], args["new_date"], args["new_time"])
            return {"status": "success" if res else "failed"}
        elif name == "save_episodic_memory":
            save_episodic_memory(patient_id, args["fact"])
            return {"status": "success", "message": "Fact saved to long-term memory."}
        return {"error": "Unknown function"}
    except Exception as e:
        return {"error": str(e)}

def chat_with_agent(patient_id: str, user_message: str) -> str:
    messages = session_manager.get_or_create_session(patient_id)
    messages.append({"role": "user", "content": user_message})
    
    logger.info(f"[{patient_id}] {'='*40}")
    logger.info(f"[{patient_id}] 📥 USER: {user_message}")
    
    # --- HITL Check ---
    pending_action = session_manager.get_pending_action(patient_id)
    if pending_action:
        if user_message.strip().upper() == "APPROVE":
            func_name = pending_action["name"]
            func_args = pending_action["args"]
            tool_call_id = pending_action["tool_call_id"]
            
            logger.info(f"[{patient_id}] HITL Approved - Executing {func_name} with {func_args}")
            func_res = execute_function(func_name, func_args, patient_id)
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": func_name,
                "content": json.dumps(func_res)
            })
            session_manager.clear_pending_action(patient_id)
        else:
            tool_call_id = pending_action["tool_call_id"]
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": pending_action["name"],
                "content": json.dumps({"error": "User did not explicitly approve the action. The booking is cancelled."})
            })
            session_manager.clear_pending_action(patient_id)
            
    # --- Dynamic Time Injection ---
    current_time_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    time_message = {"role": "system", "content": f"Real-time update: It is currently {current_time_str}. If the user asks for the time, answer it directly."}
            
    for _ in range(5):
        payload = messages.copy()
        payload.insert(-1, time_message)
        
        start_time = time.time()
        response = client.chat.completions.create(
            model=MODEL,
            messages=payload,
            tools=tools,
            tool_choice="auto",
            temperature=0.0
        )
        latency = time.time() - start_time
        tokens = response.usage.total_tokens if response.usage else 0
        logger.info(f"[{patient_id}]    🧠 LLM Call - Latency: {latency:.2f}s, Tokens: {tokens}")
        
        response_message = response.choices[0].message
        
        if not response_message.tool_calls:
            logger.info(f"[{patient_id}] 📤 AGENT: {response_message.content}")
            messages.append({"role": "assistant", "content": response_message.content})
            return response_message.content
            
        messages.append({
            "role": "assistant",
            "content": response_message.content,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                } for tool_call in response_message.tool_calls
            ]
        })
        
        for tool_call in response_message.tool_calls:
            func_name = tool_call.function.name
            try:
                func_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": json.dumps({"error": "Invalid JSON format"})
                })
                continue
            
            # --- Pydantic Validation ---
            try:
                if func_name == "get_doctor_schedule":
                    GetDoctorScheduleSchema(**func_args)
                elif func_name == "check_slot_availability":
                    CheckSlotSchema(**func_args)
                elif func_name == "book_appointment":
                    BookAppointmentSchema(**func_args)
                elif func_name == "cancel_appointment":
                    CancelAppointmentSchema(**func_args)
                elif func_name == "reschedule_appointment":
                    RescheduleAppointmentSchema(**func_args)
                elif func_name == "save_episodic_memory":
                    SaveEpisodicMemorySchema(**func_args)
            except ValidationError as e:
                logger.warning(f"[{patient_id}] Validation Error for {func_name}: {e.errors()}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": json.dumps({"error": "Validation Error", "details": str(e.errors())})
                })
                continue
                
            # --- HITL Intercept ---
            if func_name == "book_appointment":
                session_manager.set_pending_action(patient_id, {
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "args": func_args
                })
                logger.info(f"[{patient_id}] HITL Paused - Pending Action: {func_name}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": json.dumps({"status": "pending", "message": "Action paused for Human-in-the-Loop approval. Ask the user to reply with exactly 'APPROVE' to authorize this booking."})
                })
                continue
                
            # Normal Execution
            logger.info(f"[{patient_id}]    🛠️ DECISION: Calling tool '{func_name}' with args: {func_args}")
            func_res = execute_function(func_name, func_args, patient_id)
            logger.info(f"[{patient_id}]    🟢 TOOL RESULT: {func_res}")
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": func_name,
                "content": json.dumps(func_res)
            })
            
    return "I'm sorry, I encountered an issue processing your request."
