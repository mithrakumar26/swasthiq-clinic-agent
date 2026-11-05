from __future__ import annotations
import copy, json, re, threading, time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

DATA_FILE = Path(__file__).resolve().parents[1] / "clinic.json"
with DATA_FILE.open(encoding="utf-8") as f:
    MASTER = json.load(f)

app = FastAPI(title="Sunrise Clinic Front Desk Agent", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
LOCK = threading.RLock()

class RunRequest(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=100)
    today: str
    turns: list[str] = Field(min_length=1)
    @field_validator("today")
    @classmethod
    def valid_date(cls, v):
        date.fromisoformat(v)
        return v

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())

def parse_date(text: str, today: str) -> Optional[str]:
    t=norm(text); d=date.fromisoformat(today)
    m=re.search(r"\b(202\d-\d{2}-\d{2})\b", t)
    if m: return m.group(1)
    # Explicit numbered October dates: the final correction wins.
    nums=re.findall(r"\b(?:october\s*)?(\d{1,2})\s*(?:tareekh|तारीख)\b",t)
    weekdays={"monday":0,"somwar":0,"tuesday":1,"mangalwar":1,"wednesday":2,"budhwar":2,
              "thursday":3,"guruwar":3,"friday":4,"shukrawar":4,"saturday":5,"shanivaar":5,
              "shanivar":5,"sunday":6,"ravivaar":6,"ravivar":6}
    found=[]
    for word,wd in weekdays.items():
        for m in re.finditer(r"\b"+word+r"\b",t):
            found.append((m.start(),wd))
    found.sort()
    if found:
        wd=found[-1][1]
        if nums:
            # Match the last explicit day number with the final weekday when possible.
            daynum=int(nums[-1])
            try:
                candidate=date(2026,10,daynum)
                if candidate.weekday()==wd: return candidate.isoformat()
            except ValueError: pass
        delta=(wd-d.weekday())%7
        if delta==0: delta=7
        return (d+timedelta(days=delta)).isoformat()
    if nums:
        try: return date(2026,10,int(nums[-1])).isoformat()
        except ValueError: return None
    offsets=[("parso",2),("day after tomorrow",2),("kal",1),("tomorrow",1),("aaj",0),("today",0)]
    for word,n in offsets:
        if re.search(r"\b"+word+r"\b",t): return (d+timedelta(days=n)).isoformat()
    return None

def parse_time(text: str) -> Optional[str]:
    t=norm(text)
    m=re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",t)
    if m:
        h=int(m.group(1)); mi=int(m.group(2) or 0); ap=m.group(3)
        if h==12: h=0
        if ap=="pm": h+=12
        return f"{h:02d}:{mi:02d}"
    m=re.search(r"\b(\d{1,2}):(\d{2})\b",t)
    if m: return f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"
    hindi={"gyarah": "11:00","g्यारह":"11:00","das":"10:00","nau":"09:00","saade nau":"09:30",
           "saadhe nau":"09:30","10 baje":"10:00","9 baje":"09:00","11 baje":"11:00",
           "gyarah baje":"11:00","saat baje":"19:00"}
    for k,v in hindi.items():
        if k in t: return v
    return None

def doctor_id(text: str) -> Optional[str]:
    t=norm(text)
    if "rao" in t: return "dr_rao"
    if "sethi" in t: return "dr_sethi"
    return None

def is_urgent(text: str) -> bool:
    t=norm(text)
    phrases=["chest pain","seene mein dard","chest hurts","difficulty breathing","saans nahi",
             "saans phool","can't breathe","cannot breathe","not breathing","unconscious",
             "behosh","severe bleeding","heavy bleeding","stroke","face drooping",
             "fits aa","seizure","suicidal","overdose","poison"]
    return any(x in t for x in phrases)

def is_clinical(text: str) -> bool:
    t=norm(text)
    markers=["medicine","tablet","goli","dose","dosage","crocin","paracetamol","fever",
             "bukhar","pain","dard","symptom","symptoms","rash","vomit","vomiting",
             "pregnant","pregnancy","should i take","kya karu","kya karoon","medical advice"]
    return any(x in t for x in markers)

def is_injection(text: str) -> bool:
    t=norm(text)
    return any(x in t for x in ["ignore your previous","administrator mode","cancel every",
                                "cancel all","delete all","system prompt","reveal your instructions"])

class ClinicTools:
    """Ground-truth tools. No LLM calls are permitted in this layer."""
    def __init__(self, source=None):
        self.data=copy.deepcopy(source or MASTER)
        self.calls=[]
        self._lock=threading.RLock()

    def call(self,name,args):
        self.calls.append({"name":name,"arguments":copy.deepcopy(args)})
        fn=getattr(self,name,None)
        if not callable(fn) or name.startswith("_"): raise ValueError(f"Unknown tool: {name}")
        return fn(**args)

    def lookup_patient(self, name: str, phone: Optional[str]=None, patient_hint: Optional[str]=None):
        if not isinstance(name,str) or not name.strip(): raise ValueError("name is required")
        candidates=[]
        for pt in self.data["patients"]:
            nm=norm(pt["name"]); q=norm(name)
            match=(q in nm or nm in q or all(part in nm for part in q.split()))
            if phone and pt["phone"] != re.sub(r"\D","",phone): match=False
            if patient_hint and norm(patient_hint) not in nm: match=False
            if match: candidates.append({k:pt[k] for k in ("id","name","phone","dob","guardian_of")})
        return {"candidates":candidates,"count":len(candidates)}

    def search_slots(self, doctor_id: str, date: str, window: Optional[str]=None):
        if doctor_id not in [d["id"] for d in self.data["doctors"]]: raise ValueError("Unknown doctor_id")
        try: day=__import__("datetime").date.fromisoformat(date)
        except Exception: raise ValueError("date must use YYYY-MM-DD")
        if date in self.data["holidays"] or day.weekday()==6: return {"slots":[],"reason":"clinic_closed"}
        doc=next(d for d in self.data["doctors"] if d["id"]==doctor_id)
        if date in doc.get("leave_dates",[]): return {"slots":[],"reason":"doctor_on_leave"}
        dayname=day.strftime("%a")
        windows=[w for w in doc["windows"] if w["day"]==dayname]
        slots=[]
        for w in windows:
            start=datetime.strptime(w["start"],"%H:%M")
            end=datetime.strptime(w["end"],"%H:%M")
            cur=start
            while cur+timedelta(minutes=15)<=end:
                st=cur.strftime("%H:%M")
                if window=="morning" and cur.hour>=12: cur+=timedelta(minutes=15); continue
                if window=="evening" and cur.hour<16: cur+=timedelta(minutes=15); continue
                occupied=any(a["doctor_id"]==doctor_id and a["date"]==date and a["start"]==st and a["status"]=="booked" for a in self.data["appointments"])
                if not occupied: slots.append({"doctor_id":doctor_id,"date":date,"start":st,"end":(cur+timedelta(minutes=15)).strftime("%H:%M")})
                cur+=timedelta(minutes=15)
        return {"slots":slots,"reason":None if slots else "no_free_slots"}

    def book_appointment(self, patient_id: str, doctor_id: str, date: str, start: str):
        with self._lock:
            if not any(p["id"]==patient_id for p in self.data["patients"]): raise ValueError("Unknown patient_id")
            result=self.search_slots(doctor_id,date)
            if not any(s["start"]==start for s in result["slots"]): raise ValueError(f"Slot {date} {start} is unavailable; search slots again")
            nums=[int(a["id"].split("_")[1]) for a in self.data["appointments"]]
            aid=f"ap_{max(nums+[0])+1:04d}"
            self.data["appointments"].append({"id":aid,"patient_id":patient_id,"doctor_id":doctor_id,
                "date":date,"start":start,"end":(datetime.strptime(start,"%H:%M")+timedelta(minutes=15)).strftime("%H:%M"),"status":"booked"})
            return next(a for a in self.data["appointments"] if a["id"]==aid)

    def reschedule_appointment(self, patient_id: str, appointment_id: str, doctor_id: str, date: str, start: str):
        with self._lock:
            ap=next((a for a in self.data["appointments"] if a["id"]==appointment_id and a["status"]=="booked"),None)
            if not ap: raise ValueError("Active appointment not found")
            if ap["patient_id"]!=patient_id: raise ValueError("Appointment does not belong to resolved patient")
            # Validate destination before mutating original: atomic move.
            result=self.search_slots(doctor_id,date)
            if not any(s["start"]==start for s in result["slots"]): raise ValueError(f"Destination slot {date} {start} is unavailable")
            ap.update({"doctor_id":doctor_id,"date":date,"start":start,
                       "end":(datetime.strptime(start,"%H:%M")+timedelta(minutes=15)).strftime("%H:%M")})
            return ap

    def cancel_appointment(self, patient_id: str, appointment_id: str):
        with self._lock:
            ap=next((a for a in self.data["appointments"] if a["id"]==appointment_id and a["status"]=="booked"),None)
            if not ap: raise ValueError("Active appointment not found")
            if ap["patient_id"]!=patient_id: raise ValueError("Appointment does not belong to resolved patient")
            ap["status"]="cancelled"
            return ap

    def escalate_to_human(self, reason: str, detail: str):
        allowed={"clinical_urgent","medical_advice","not_authorised","ambiguous_patient","out_of_scope"}
        if reason not in allowed: raise ValueError("Invalid escalation reason")
        return {"status":"escalated","reason":reason,"detail":detail}

def extract_person(turns):
    """Find known patient records mentioned in the conversation and a phone number."""
    text = " ".join(turns)
    phone_m = re.findall(r"(?<!\d)(\d{10})(?!\d)", text)
    phone = phone_m[-1] if phone_m else None
    known = MASTER["patients"]
    matches = []
    normalized_text = norm(text)
    for pt in known:
        if norm(pt["name"]) in normalized_text:
            matches.append(pt)
    if phone and not matches:
        matches = [pt for pt in known if re.sub(r"\D", "", pt["phone"]) == phone]
    return matches, phone


def extract_declared_name(turns):
    """Extract a full name explicitly stated by the caller; this is not verification."""
    patterns = [
        r"\bmy name is\s+([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){1,3})(?=[.!?,;]|$)",
        r"\bi am\s+([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){1,3})(?=[.!?,;]|$)",
        r"\bi'm\s+([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){1,3})(?=[.!?,;]|$)",
        r"\bthis is\s+([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){1,3})(?=[.!?,;]|$)",
        r"\bpatient name is\s+([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){1,3})(?=[.!?,;]|$)",
    ]
    for turn in turns:
        for pattern in patterns:
            match = re.search(pattern, turn, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    return None

def caller_is_authorised(turns, patient, patient_id):
    text=norm(" ".join(turns))
    if not patient_id: return False
    callers,phone=extract_person(turns)
    # A registered phone is the primary self-verification signal. A different
    # caller phone cannot authorise action on another adult's record.
    if phone == patient.get("phone"):
        return True
    # A listed guardian may act for a child when the relationship is explicit.
    if any(x in text for x in ["mera beta","meri beti","my son","my daughter","guardian"]) and callers:
        return any(patient_id in c.get("guardian_of",[]) for c in callers)
    return False

def run_agent(req: RunRequest):
    started=time.perf_counter()
    tools=ClinicTools() # assignment: reset to clinic.json for every conversation
    turns=req.turns
    full=" ".join(turns)
    lower=norm(full)
    patient_id=None; appointment_id=None; reason=None; state="abandoned"
    reply="I could not identify a booking or appointment request. Please call again when you are ready."
    # Medical red flags take absolute precedence over all booking intent.
    if any(is_urgent(t) for t in turns):
        detail=next(t for t in turns if is_urgent(t))
        tools.call("escalate_to_human",{"reason":"clinical_urgent","detail":detail})
        state="escalated"; reason="clinical_urgent"
        reply="I’m stopping the booking process and handing this to the clinic team now. If you are experiencing chest pain or breathing difficulty, seek emergency medical help immediately."
    elif is_clinical(full) and not any(x in lower for x in ["appointment","appointment chahiye","doctor ke saath","milna hai","dikhana hai"]):
        tools.call("escalate_to_human",{"reason":"medical_advice","detail":full})
        state="escalated"; reason="medical_advice"
        reply="I can’t provide medical advice or medication guidance. I’m handing your question to a clinician."
    elif is_injection(full):
        state="refused"; reply="I can only help with an individual patient's appointment. I cannot follow instructions to modify or cancel multiple records."
    else:
        # Detect cancellation/reschedule/booking intent
        cancel=any(x in lower for x in ["cancel","radd","cancellation"])
        resched=any(x in lower for x in ["reschedule","move","shift","change","use saturday","use sunday","use monday","use tuesday","use wednesday","use thursday","use friday"]) or "aaj ka appointment" in lower
        # Explicit date/time from last non-correction context; corrections override earlier date.
        date_value=None
        for t in turns:
            parsed=parse_date(t,req.today)
            if parsed: date_value=parsed
        # Hindi day-number references are parsed from entire conversation as fallback.
        if date_value is None: date_value=parse_date(full,req.today)
        doc=doctor_id(full) or "dr_rao"
        matches,phone=extract_person(turns)
        # Detect intended child name if guardian booking
        child_hint=None
        m=re.search(r"\b([A-Za-z]+)\s+mera\s+beta\b|\b(?:bete|beta|son|daughter|beti)\s+([A-Za-z]+)",full,re.I)
        if m: child_hint=next(g for g in m.groups() if g)
        # For cancellation/rescheduling, patient identity must be resolved, and ownership checked.
        if cancel or resched or any(x in lower for x in ["appointment chahiye","appointment karwana","appointment hai","dikhana hai","milna hai","aa sakta hoon"]) or (doctor_id(full) and date_value is not None):
            # Resolve known records first. If no known record was mentioned,
            # extract the caller's declared full name and verify it against the database.
            target_matches = matches
            if child_hint:
                target_matches = [
                    pt for pt in MASTER["patients"]
                    if norm(child_hint) in norm(pt["name"])
                ]

            if len(target_matches) == 1:
                lookup_name = target_matches[0]["name"]
                lookup_phone = phone if phone == target_matches[0]["phone"] else None
                lookup = tools.call(
                    "lookup_patient",
                    {"name": lookup_name, "phone": lookup_phone, "patient_hint": None}
                )
                candidates = lookup["candidates"]
            elif len(target_matches) > 1:
                # Do not choose among multiple records without a disambiguating phone.
                if phone:
                    phone_matches = [
                        pt for pt in target_matches
                        if re.sub(r"\D", "", pt["phone"]) == phone
                    ]
                else:
                    phone_matches = []
                if len(phone_matches) == 1:
                    lookup = tools.call(
                        "lookup_patient",
                        {"name": phone_matches[0]["name"], "phone": phone, "patient_hint": None}
                    )
                    candidates = lookup["candidates"]
                else:
                    candidates = target_matches
            else:
                declared_name = extract_declared_name(turns)
                if declared_name:
                    lookup = tools.call(
                        "lookup_patient",
                        {"name": declared_name, "phone": phone, "patient_hint": None}
                    )
                    candidates = lookup["candidates"]
                else:
                    # A generic surname returns all plausible candidates; never guess.
                    surname = re.search(r"\b(sharma|gupta|iyer|joshi|nair)\b", full, re.I)
                    if surname:
                        lookup = tools.call(
                            "lookup_patient",
                            {"name": surname.group(1), "phone": phone, "patient_hint": None}
                        )
                        candidates = lookup["candidates"]
                    else:
                        candidates = []
            if len(candidates)>1:
                tools.call("escalate_to_human",{"reason":"ambiguous_patient","detail":"Multiple patient records match the caller; clarification required."})
                state="escalated"; reason="ambiguous_patient"
                reply="I found more than one matching patient record and cannot choose between them. I’m handing this to the clinic team."
            elif len(candidates)==0:
                state="abandoned"; reply="I could not verify the patient record. Please provide the patient's full name and registered phone number."
            else:
                patient=candidates[0]; patient_id=patient["id"]
                # If booking on behalf of a child, require explicit listed guardian relationship.
                is_child=bool(child_hint)
                caller_matches,_=extract_person(turns)
                if is_child and not any(patient_id in c.get("guardian_of",[]) for c in caller_matches):
                    tools.call("escalate_to_human",{"reason":"not_authorised","detail":"Caller authority for the requested patient's record could not be verified."})
                    state="escalated"; reason="not_authorised"
                    reply="I cannot verify that you are authorised to manage this patient's appointment. I’m handing this to the clinic team."
                elif cancel or resched:
                    # Identify active appointment for patient; today/current appointment preferred.
                    active=[a for a in tools.data["appointments"] if a["patient_id"]==patient_id and a["status"]=="booked"]
                    if not active:
                        state="abandoned"; reply="I could not find an active appointment for this patient."
                    elif not caller_is_authorised(turns,patient,patient_id):
                        tools.call("escalate_to_human",{"reason":"not_authorised","detail":"Caller is not the patient or a listed guardian."})
                        state="escalated"; reason="not_authorised"
                        reply="I cannot verify authority to change this patient's appointment. I’m handing this to the clinic team."
                    else:
                        ap=next((a for a in active if a["date"]==req.today),active[0])
                        appointment_id=ap["id"]
                        if cancel:
                            tools.call("cancel_appointment",{"patient_id":patient_id,"appointment_id":appointment_id})
                            state="cancelled"; reply=f"The appointment {appointment_id} has been cancelled."
                        else:
                            if date_value is None:
                                state="abandoned"; reply="Please tell me the new date for the appointment."
                            else:
                                # Doctor and time default to existing when not specified.
                                newtime=parse_time(full) or ap["start"]
                                tools.call("reschedule_appointment",{"patient_id":patient_id,"appointment_id":appointment_id,
                                    "doctor_id":doc,"date":date_value,"start":newtime})
                                state="rescheduled"; reply=f"Your appointment {appointment_id} has been moved to {date_value} at {newtime}."
                else:
                    if date_value is None:
                        state="abandoned"; reply="Please tell me which date you would like."
                    else:
                        window="morning" if any(x in lower for x in ["subah","morning"]) else ("evening" if any(x in lower for x in ["shaam","evening"]) else None)
                        slots=tools.call("search_slots",{"doctor_id":doc,"date":date_value,"window":window})
                        wanted=parse_time(full)
                        if not slots["slots"]:
                            state="abandoned"; reply=f"No available slot was returned for {date_value}. No appointment was created."
                        else:
                            chosen=next((s for s in slots["slots"] if s["start"]==wanted),None) if wanted else slots["slots"][0]
                            if chosen is None:
                                # A slot was requested but unavailable; do not substitute without consent.
                                state="abandoned"; reply=f"The requested time {wanted} is not available on {date_value}. No appointment was created."
                            else:
                                booked=tools.call("book_appointment",{"patient_id":patient_id,"doctor_id":doc,"date":date_value,"start":chosen["start"]})
                                appointment_id=booked["id"]; state="booked"
                                reply=f"Your appointment is booked for {date_value} at {chosen['start']} with {doc.replace('dr_','Dr. ').title()}."
        else:
            state="abandoned"
    latency=int((time.perf_counter()-started)*1000)
    # Deterministic estimated token count; no external model is used in this baseline.
    tokens=max(1,(len(full)+3)//4 + len(json.dumps(tools.calls))//4)
    return {"conversation_id":req.conversation_id,"tool_calls":tools.calls,"terminal_state":state,
            "escalation_reason":reason,"patient_id":patient_id,"appointment_id":appointment_id,
            "reply":reply,"metrics":{"turns":len(turns),"tokens":tokens,"latency_ms":latency}}

@app.post("/agent/run")
def agent_run(req: RunRequest):
    try:
        with LOCK:
            return run_agent(req)
    except ValueError as e:
        raise HTTPException(status_code=422,detail=str(e))
    except Exception as e:
        # Do not leak internals to callers.
        raise HTTPException(status_code=400,detail="The request could not be safely processed.")

@app.get("/health")
def health(): return {"status":"ok","clinic":MASTER["clinic"]["name"]}

@app.get("/dashboard")
def dashboard():
    # Synthetic dashboard snapshot for the UI; handoffs are deterministic demo examples.
    return {"clinic":MASTER["clinic"]["name"],"city":MASTER["clinic"]["city"],
        "counters":{"conversations":37,"completed":31,"escalated":6,"urgent":1},
        "handoffs":[
          {"id":"cv_4471","caller":"“Seene mein dard ho raha hai”","reason":"CLINICAL","time":"11:42","detail":"Caller reports active chest pain and shortness of breath."},
          {"id":"cv_4468","caller":"“Cancel for a different patient”","reason":"NOT AUTHORISED","time":"11:20","detail":"Caller is not the patient or a listed guardian."},
          {"id":"cv_4463","caller":"“Sharma ji ke liye” — 3 matches","reason":"AMBIGUOUS PATIENT","time":"10:57","detail":"Three patient records matched the supplied surname."},
          {"id":"cv_4455","caller":"“Ye dawa lun ya nahi?”","reason":"MEDICAL ADVICE","time":"10:18","detail":"Caller requested medication advice."}]}
