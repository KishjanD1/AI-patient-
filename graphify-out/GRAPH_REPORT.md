# Graph Report - .  (2026-06-30)

## Corpus Check
- Corpus is ~3,316 words - fits in a single context window. You may not need a graph.

## Summary
- 53 nodes · 62 edges · 16 communities (8 shown, 8 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 9 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Database Operations|Database Operations]]
- [[_COMMUNITY_State Machine Orchestrator|State Machine Orchestrator]]
- [[_COMMUNITY_Session Management|Session Management]]
- [[_COMMUNITY_Web API Endpoints|Web API Endpoints]]
- [[_COMMUNITY_Security Management|Security Management]]
- [[_COMMUNITY_State Machine Defs|State Machine Defs]]
- [[_COMMUNITY_Intent Parsing|Intent Parsing]]
- [[_COMMUNITY_Response Formatting|Response Formatting]]
- [[_COMMUNITY_Chat UI Javascript|Chat UI Javascript]]
- [[_COMMUNITY_API Request Models|API Request Models]]

## God Nodes (most connected - your core abstractions)
1. `AppointmentOrchestrator` - 10 edges
2. `SessionManager` - 6 edges
3. `get_db_connection()` - 5 edges
4. `ChatResponse` - 4 edges
5. `setup_database()` - 4 edges
6. `check_slot_availability()` - 4 edges
7. `book_appointment()` - 4 edges
8. `ChatRequest` - 3 edges
9. `chat_endpoint()` - 3 edges
10. `IntentSchema` - 3 edges

## Surprising Connections (you probably didn't know these)
- `ChatRequest` --uses--> `State`  [INFERRED]
  main.py → core/orchestrator.py
- `ChatResponse` --uses--> `State`  [INFERRED]
  main.py → core/orchestrator.py
- `fetch_appointments()` --calls--> `get_all_appointments()`  [INFERRED]
  main.py → database/db_handler.py
- `on_startup()` --calls--> `setup_database()`  [INFERRED]
  main.py → database/db_handler.py
- `chat_endpoint()` --calls--> `llm_response_formatter()`  [INFERRED]
  main.py → agents/llm_service.py

## Communities (16 total, 8 thin omitted)

### Community 0 - "Database Operations"
Cohesion: 0.29
Nodes (9): on_startup(), book_appointment(), check_slot_availability(), get_all_appointments(), get_db_connection(), Checks if a slot is available in SQLite.      Returns (is_available, alternative, Executes the booking deterministically by updating the DB., Initializes the database schema and populates mock data if empty. (+1 more)

### Community 7 - "Response Formatting"
Cohesion: 0.67
Nodes (3): llm_response_formatter(), chat_endpoint(), ChatResponse

## Knowledge Gaps
- **4 isolated node(s):** `Deterministic Pure Python State Machine for Triage and SQLite Booking.`, `Initializes the database schema and populates mock data if empty.`, `Checks if a slot is available in SQLite.      Returns (is_available, alternative`, `Executes the booking deterministically by updating the DB.`
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppointmentOrchestrator` connect `State Machine Orchestrator` to `Session Management`, `State Machine Defs`?**
  _High betweenness centrality (0.271) - this node is a cross-community bridge._
- **Why does `State` connect `State Machine Defs` to `API Request Models`, `Response Formatting`?**
  _High betweenness centrality (0.142) - this node is a cross-community bridge._
- **Why does `SessionManager` connect `Session Management` to `State Machine Orchestrator`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `AppointmentOrchestrator` (e.g. with `SessionManager` and `.get_or_create_session()`) actually correct?**
  _`AppointmentOrchestrator` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Deterministic Pure Python State Machine for Triage and SQLite Booking.`, `Initializes the database schema and populates mock data if empty.`, `Checks if a slot is available in SQLite.      Returns (is_available, alternative` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._