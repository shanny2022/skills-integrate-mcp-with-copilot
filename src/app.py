"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

# DB imports for PoC
from sqlmodel import select
from src.db import init_db, get_session
from src.models import User, Activity, Participant

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


# --- Database initialization & migration (PoC) ---
try:
    init_db()

    def migrate_activities_to_db():
        """Migrate the existing in-memory `activities` dict into the database if empty."""
        with get_session() as session:
            existing = session.exec(select(Activity)).first()
            if existing:
                return

            for name, data in activities.items():
                activity = Activity(
                    name=name,
                    description=data.get("description"),
                    schedule=data.get("schedule"),
                    max_participants=data.get("max_participants"),
                )
                session.add(activity)
                session.commit()
                session.refresh(activity)

                for email in data.get("participants", []):
                    user = session.exec(select(User).where(User.email == email)).first()
                    if not user:
                        user = User(email=email)
                        session.add(user)
                        session.commit()
                        session.refresh(user)

                    participant = Participant(user_id=user.id, activity_id=activity.id)
                    session.add(participant)

                session.commit()

    migrate_activities_to_db()
except Exception:
    # Fallback: if SQLModel isn't installed or DB init fails, keep using in-memory store
    pass


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    # Return DB-backed activities if available, otherwise fallback to in-memory
    try:
        with get_session() as session:
            results = session.exec(select(Activity)).all()
            out = {}
            for a in results:
                # fetch participant emails
                participants = []
                parts = session.exec(select(Participant).where(Participant.activity_id == a.id)).all()
                for p in parts:
                    u = session.get(User, p.user_id)
                    if u:
                        participants.append(u.email)

                out[a.name] = {
                    "description": a.description,
                    "schedule": a.schedule,
                    "max_participants": a.max_participants,
                    "participants": participants,
                }
            return out
    except Exception:
        return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Try DB-backed signup first
    try:
        with get_session() as session:
            activity = session.exec(select(Activity).where(Activity.name == activity_name)).first()
            if not activity:
                raise HTTPException(status_code=404, detail="Activity not found")

            # Check if user exists or create
            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                user = User(email=email)
                session.add(user)
                session.commit()
                session.refresh(user)

            # Check already signed up
            exists = session.exec(
                select(Participant).where(Participant.activity_id == activity.id, Participant.user_id == user.id)
            ).first()
            if exists:
                raise HTTPException(status_code=400, detail="Student is already signed up")

            # Check capacity
            count = session.exec(select(Participant).where(Participant.activity_id == activity.id)).all()
            if activity.max_participants and len(count) >= activity.max_participants:
                raise HTTPException(status_code=400, detail="Activity is full")

            participant = Participant(user_id=user.id, activity_id=activity.id)
            session.add(participant)
            session.commit()
            return {"message": f"Signed up {email} for {activity_name}"}
    except HTTPException:
        raise
    except Exception:
        # Fallback to in-memory behavior
        if activity_name not in activities:
            raise HTTPException(status_code=404, detail="Activity not found")

        activity = activities[activity_name]

        if email in activity["participants"]:
            raise HTTPException(status_code=400, detail="Student is already signed up")

        activity["participants"].append(email)
        return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    try:
        with get_session() as session:
            activity = session.exec(select(Activity).where(Activity.name == activity_name)).first()
            if not activity:
                raise HTTPException(status_code=404, detail="Activity not found")

            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

            participant = session.exec(
                select(Participant).where(Participant.activity_id == activity.id, Participant.user_id == user.id)
            ).first()
            if not participant:
                raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

            session.delete(participant)
            session.commit()
            return {"message": f"Unregistered {email} from {activity_name}"}
    except HTTPException:
        raise
    except Exception:
        # Fallback to in-memory
        if activity_name not in activities:
            raise HTTPException(status_code=404, detail="Activity not found")

        activity = activities[activity_name]

        if email not in activity["participants"]:
            raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

        activity["participants"].remove(email)
        return {"message": f"Unregistered {email} from {activity_name}"}
