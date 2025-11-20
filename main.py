import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Gesture, Module, Quiz, Profile, Accessibility

app = FastAPI(title="SignifyLearn API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "SignifyLearn Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:20]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:120]}"
    return response


# Utility functions
from bson import ObjectId

def _to_json(doc):
    if not doc:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


# -------------------- Gesture Catalog --------------------
@app.get("/api/gestures")
def list_gestures(
    q: Optional[str] = Query(None, description="Search by name or tags"),
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    page: int = 1,
    limit: int = 24,
):
    if db is None:
        return {"items": [], "total": 0, "page": page, "limit": limit}
    filter_q = {}
    if q:
        filter_q["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"tags": {"$regex": q, "$options": "i"}},
        ]
    if category:
        filter_q["category"] = category
    if difficulty:
        filter_q["difficulty"] = difficulty

    total = db["gesture"].count_documents(filter_q)
    cursor = db["gesture"].find(filter_q).skip((page - 1) * limit).limit(limit)
    items = [_to_json(x) for x in cursor]
    return {"items": items, "total": total, "page": page, "limit": limit}


@app.get("/api/gestures/{slug}")
def get_gesture(slug: str):
    if db is None:
        raise HTTPException(status_code=404, detail="Database not available")
    doc = db["gesture"].find_one({"slug": slug})
    if not doc:
        raise HTTPException(status_code=404, detail="Gesture not found")
    return _to_json(doc)


# -------------------- Modules --------------------
@app.get("/api/modules")
def list_modules():
    if db is None:
        return []
    return [_to_json(x) for x in db["module"].find({})]


@app.get("/api/modules/{slug}")
def get_module(slug: str):
    if db is None:
        raise HTTPException(status_code=404, detail="Database not available")
    doc = db["module"].find_one({"slug": slug})
    if not doc:
        raise HTTPException(status_code=404, detail="Module not found")
    return _to_json(doc)


# -------------------- Quizzes --------------------
@app.get("/api/quizzes/{slug}")
def get_quiz(slug: str):
    if db is None:
        raise HTTPException(status_code=404, detail="Database not available")
    doc = db["quiz"].find_one({"slug": slug})
    if not doc:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return _to_json(doc)


# -------------------- Profiles --------------------
class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    favorite_gesture_slug: Optional[str] = None
    remove_favorite: bool = False
    completed_module_slug: Optional[str] = None


@app.get("/api/profile/{user_id}")
def get_profile(user_id: str):
    if db is None:
        return {}
    doc = db["profile"].find_one({"user_id": user_id})
    if not doc:
        # initialize minimal profile
        profile = Profile(user_id=user_id, name="Pengguna", email=f"{user_id}@example.com")
        create_document("profile", profile)
        doc = db["profile"].find_one({"user_id": user_id})
    return _to_json(doc)


@app.post("/api/profile/{user_id}")
def update_profile(user_id: str, payload: ProfileUpdate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    update = {"$set": {"updated_at": os.times().elapsed if hasattr(os, 'times') else None}}

    if payload.name is not None:
        update["$set"]["name"] = payload.name
    if payload.avatar_url is not None:
        update["$set"]["avatar_url"] = payload.avatar_url

    if payload.favorite_gesture_slug:
        if payload.remove_favorite:
            update.setdefault("$pull", {})["favorite_gesture_slugs"] = payload.favorite_gesture_slug
        else:
            update.setdefault("$addToSet", {})["favorite_gesture_slugs"] = payload.favorite_gesture_slug

    if payload.completed_module_slug:
        update.setdefault("$addToSet", {})["completed_module_slugs"] = payload.completed_module_slug

    db["profile"].update_one({"user_id": user_id}, update, upsert=True)
    doc = db["profile"].find_one({"user_id": user_id})
    return _to_json(doc)


# -------------------- Accessibility Preferences --------------------
@app.get("/api/accessibility/{user_id}")
def get_accessibility(user_id: str):
    if db is None:
        return {}
    doc = db["accessibility"].find_one({"user_id": user_id})
    if not doc:
        pref = Accessibility(user_id=user_id)
        create_document("accessibility", pref)
        doc = db["accessibility"].find_one({"user_id": user_id})
    return _to_json(doc)


class AccessibilityUpdate(BaseModel):
    dark_mode: Optional[bool] = None
    high_contrast: Optional[bool] = None
    font_scale: Optional[float] = None
    reduce_motion: Optional[bool] = None


@app.post("/api/accessibility/{user_id}")
def update_accessibility(user_id: str, payload: AccessibilityUpdate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    update = {"$set": {}}
    for k, v in payload.model_dump(exclude_none=True).items():
        update["$set"][k] = v
    db["accessibility"].update_one({"user_id": user_id}, update, upsert=True)
    doc = db["accessibility"].find_one({"user_id": user_id})
    return _to_json(doc)


# -------------------- Seed Data --------------------
@app.post("/api/seed")
def seed_data():
    if db is None:
        return {"inserted": 0}

    # Only seed if empty
    if db["gesture"].count_documents({}) == 0:
        sample_gestures: List[Gesture] = [
            Gesture(
                name="A", slug="letter-a", category="letters", difficulty="easy",
                thumbnail="https://images.unsplash.com/photo-1520975916090-3105956dac38?w=400",
                video_url="https://samplelib.com/lib/preview/mp4/sample-5s.mp4",
                steps=["Kepalkan tangan", "Letakkan ibu jari di samping"],
                examples=["A untuk 'Aku'"]
            ),
            Gesture(
                name="Halo", slug="halo", category="basic", difficulty="easy",
                thumbnail="https://images.unsplash.com/photo-1516873240891-4bf2b74d0a2a?w=400",
                video_url="https://samplelib.com/lib/preview/mp4/sample-5s.mp4",
                steps=["Lambaikan tangan"], examples=["Halo, apa kabar?"]
            ),
            Gesture(
                name="Terima kasih", slug="terima-kasih", category="basic", difficulty="easy",
                thumbnail="https://images.unsplash.com/photo-1520975916090-3105956dac38?w=400",
                video_url="https://samplelib.com/lib/preview/mp4/sample-5s.mp4",
                steps=["Sentuh dagu, gerakkan ke depan"], examples=["Terima kasih atas bantuannya"]
            ),
        ]
        for g in sample_gestures:
            create_document("gesture", g)

    if db["module"].count_documents({}) == 0:
        sample_modules: List[Module] = [
            Module(
                title="Dasar Bahasa Isyarat", slug="dasar-bahasa-isyarat",
                description="Pelajari gestur dasar untuk memulai.",
                cover_image="https://images.unsplash.com/photo-1520975916090-3105956dac38?w=800",
                subtopics=["Salam", "Huruf", "Angka"],
                gesture_slugs=["halo", "terima-kasih", "letter-a"],
            )
        ]
        for m in sample_modules:
            create_document("module", m)

    if db["quiz"].count_documents({}) == 0:
        quiz = Quiz(
            title="Kuis Dasar", slug="kuis-dasar",
            questions=[
                {"prompt": "Gestur untuk 'Halo' adalah...", "media_url": None, "options": ["A", "Lambaian tangan", "Kepalan"], "answer_index": 1},
                {"prompt": "Bagaimana membuat huruf A?", "media_url": None, "options": ["Kepalkan tangan" , "Luruskan jari"], "answer_index": 0},
            ],
            related_module_slug="dasar-bahasa-isyarat",
        )
        create_document("quiz", quiz)

    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
