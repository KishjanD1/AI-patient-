from typing import Dict, List, Any
from datetime import datetime
from database.db_handler import get_episodic_memories

class SessionManager:
    def __init__(self):
        # In-memory dictionary mapping patient_id to a list of messages (chat history)
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}
        # In-memory dictionary for HITL pending actions
        self.pending_actions: Dict[str, Dict[str, Any]] = {}

    def get_or_create_session(self, patient_id: str) -> List[Dict[str, Any]]:
        if patient_id not in self.sessions:
            memories = get_episodic_memories(patient_id)
            memory_context = ""
            if memories:
                memory_context = "\n\nPAST PATIENT MEMORIES (Use these to personalize the interaction):\n" + "\n".join(f"- {m}" for m in memories)

            system_prompt = (
                "You are a friendly medical receptionist. Your job is to help the user book, reschedule, or cancel their appointments.\n"
                "CRITICAL RULES:\n"
                "1. If a user describes a symptom (like a headache), use the get_available_doctors tool to find a doctor whose specialty matches the symptom, recommend them with a reason, and ask if the user wants to book with them. Do NOT ask for dates or times yet.\n"
                "2. ALWAYS ask for the user's preferred date and time. Do NOT make up or guess a time. If the user says 'tomorrow' but doesn't specify a time, ask them for a time FIRST.\n"
                "3. Once you have both a date and an explicitly stated time from the user, use the check_slot_availability tool to verify it.\n"
                "4. ALWAYS collect the doctor, date, time, and email before calling book_appointment.\n"
                "5. If a booking requires approval, tell the user exactly to type 'APPROVE' to confirm it.\n"
                "6. Whenever an appointment is successfully booked, you MUST generate an 'Appointment Proof Card' in your response. This card must clearly display the exact Appointment ID, Doctor Name, Date, and Time. Format it visually so the user can easily take a screenshot or show it at the clinic."
                f"{memory_context}"
            )
            self.sessions[patient_id] = [
                {"role": "system", "content": system_prompt}
            ]
        return self.sessions[patient_id]

    def get_session(self, patient_id: str) -> List[Dict[str, Any]]:
        return self.sessions.get(patient_id, [])
        
    def delete_session(self, patient_id: str):
        if patient_id in self.sessions:
            del self.sessions[patient_id]
        if patient_id in self.pending_actions:
            del self.pending_actions[patient_id]

    def set_pending_action(self, patient_id: str, action: dict):
        self.pending_actions[patient_id] = action

    def get_pending_action(self, patient_id: str) -> dict:
        return self.pending_actions.get(patient_id)

    def clear_pending_action(self, patient_id: str):
        if patient_id in self.pending_actions:
            del self.pending_actions[patient_id]

# Singleton instance to be used across the application
session_manager = SessionManager()
