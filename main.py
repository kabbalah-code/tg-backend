"""
Kabbalah Code - Backend API with Supabase
Deploy to Render.com (free tier)
Python 3.10+
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import os
from datetime import datetime, date
import random
import string
import hashlib

# Supabase (uncomment when credentials ready)
try:
    from supabase import create_client, Client
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    if SUPABASE_URL and SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        USE_SUPABASE = True
    else:
        USE_SUPABASE = False
        print("⚠️  Supabase not configured, using in-memory storage")
except ImportError:
    USE_SUPABASE = False
    print("⚠️  Supabase not installed, using in-memory storage")

# Initialize FastAPI
app = FastAPI(
    title="Kabbalah Code API",
    version="2.0.0",
    description="Mystical Web3 rewards platform"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory fallback storage
users_memory = {}
predictions_memory = {}

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "KABBALAH_ADMIN_2025")

# Models
class UserOnboard(BaseModel):
    telegram_id: int
    username: str
    evm_address: str = Field(pattern=r"^0x[a-fA-F0-9]{40}$")
    twitter_username: str

class VerifyCode(BaseModel):
    code: str
    tweet_url: Optional[str] = None

# Utility Functions
def generate_mystical_code() -> str:
    return 'KC' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_prediction() -> dict:
    predictions = [
        "Today the gates of ancient wisdom open. Sephira Chokmah illuminates your path through digital realms.",
        "Energies of Binah protect your journey. Time for deep meditation on blockchain mysteries.",
        "Malkuth grants material abundance in the metaverse. Act boldly with your transactions!",
        "Tiferet harmonizes your endeavors. A day for important decisions in the Web3 space.",
        "Netzach empowers your creative vision. Share your wisdom with the community.",
        "Hod brings clarity to complex protocols. Study the ancient codes carefully today.",
        "Yesod connects you to the foundation. Your network grows stronger.",
        "Gevurah demands discipline. Review your security and strengthen your defenses."
    ]
    
    return {
        "text": random.choice(predictions),
        "image_url": f"https://api.dicebear.com/7.x/shapes/svg?seed={random.randint(1000, 9999)}",
        "code": generate_mystical_code(),
        "mystical_hash": hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:16]
    }

def calculate_xp_for_level(level: int) -> int:
    return 1000 * level + 500 * (level - 1)

# API Endpoints

@app.get("/")
async def root():
    return {
        "service": "Kabbalah Code API",
        "version": "2.0.0",
        "status": "operational",
        "database": "Supabase" if USE_SUPABASE else "In-Memory"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected" if USE_SUPABASE else "memory"}

@app.post("/api/auth/onboard")
async def onboard_user(data: UserOnboard, referrer: Optional[int] = None):
    """Onboard new user"""
    
    if USE_SUPABASE:
        # Check if user exists
        existing = supabase.table("users").select("*").eq("telegram_id", data.telegram_id).execute()
        if existing.data:
            return existing.data[0]
        
        # Create new user
        user_data = {
            "telegram_id": data.telegram_id,
            "username": data.username,
            "evm_address": data.evm_address,
            "twitter_username": data.twitter_username,
            "referrer_id": referrer
        }
        
        result = supabase.table("users").insert(user_data).execute()
        return result.data[0]
    else:
        # In-memory fallback
        if data.telegram_id in users_memory:
            return users_memory[data.telegram_id]
        
        user = {
            "telegram_id": data.telegram_id,
            "username": data.username,
            "evm_address": data.evm_address,
            "twitter_username": data.twitter_username,
            "level": 1,
            "xp": 0,
            "points": 0,
            "referrer_id": referrer,
            "created_at": datetime.now().isoformat()
        }
        users_memory[data.telegram_id] = user
        return user

@app.get("/api/user/profile")
async def get_profile(telegram_id: int):
    """Get user profile"""
    
    if USE_SUPABASE:
        result = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = result.data[0]
        
        # Count referrals
        referrals = supabase.table("users").select("telegram_id").eq("referrer_id", telegram_id).execute()
        user["referrals"] = len(referrals.data)
        user["xp_to_next"] = calculate_xp_for_level(user["level"])
        
        return user
    else:
        # In-memory fallback
        if telegram_id not in users_memory:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = users_memory[telegram_id].copy()
        referrals = sum(1 for u in users_memory.values() if u.get("referrer_id") == telegram_id)
        user["referrals"] = referrals
        user["xp_to_next"] = calculate_xp_for_level(user["level"])
        
        return user

@app.get("/api/prediction/daily")
async def get_daily_prediction(telegram_id: int):
    """Get daily prediction"""
    
    today = date.today()
    cache_key = f"{telegram_id}_{today}"
    
    if USE_SUPABASE:
        # Check if prediction exists for today
        result = supabase.table("predictions")\
            .select("*")\
            .eq("user_id", telegram_id)\
            .eq("created_at", str(today))\
            .execute()
        
        if result.data:
            pred = result.data[0]
            return {
                "text": pred["prediction_text"],
                "image_url": pred["image_url"],
                "code": pred["verification_code"],
                "mystical_hash": pred.get("mystical_hash", "")
            }
        
        # Generate new prediction
        prediction = generate_prediction()
        
        # Save to DB
        supabase.table("predictions").insert({
            "user_id": telegram_id,
            "prediction_text": prediction["text"],
            "image_url": prediction["image_url"],
            "verification_code": prediction["code"],
            "mystical_hash": prediction["mystical_hash"]
        }).execute()
        
        # Update user's last_prediction
        supabase.table("users")\
            .update({"last_prediction": datetime.now().isoformat()})\
            .eq("telegram_id", telegram_id)\
            .execute()
        
        return prediction
    else:
        # In-memory fallback
        if cache_key in predictions_memory:
            return predictions_memory[cache_key]
        
        prediction = generate_prediction()
        predictions_memory[cache_key] = prediction
        return prediction

@app.post("/api/prediction/verify")
async def verify_prediction(telegram_id: int, data: VerifyCode):
    """Verify tweet and award points"""
    
    today = date.today()
    
    if USE_SUPABASE:
        # Get today's prediction
        result = supabase.table("predictions")\
            .select("*")\
            .eq("user_id", telegram_id)\
            .eq("created_at", str(today))\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=400, detail="No prediction for today")
        
        prediction = result.data[0]
        
        if prediction["is_verified"]:
            raise HTTPException(status_code=400, detail="Already verified today")
        
        if data.code != prediction["verification_code"]:
            raise HTTPException(status_code=400, detail="Invalid verification code")
        
        # Mark as verified
        supabase.table("predictions")\
            .update({"is_verified": True, "verified_at": datetime.now().isoformat()})\
            .eq("id", prediction["id"])\
            .execute()
        
        # Get user
        user_result = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
        user = user_result.data[0]
        
        # Award points
        points = 100
        new_xp = user["xp"] + points
        new_points = user["points"] + points
        new_level = user["level"]
        
        # Level up logic
        xp_needed = calculate_xp_for_level(new_level)
        while new_xp >= xp_needed:
            new_level += 1
            new_xp -= xp_needed
            xp_needed = calculate_xp_for_level(new_level)
        
        # Update user
        supabase.table("users")\
            .update({"points": new_points, "xp": new_xp, "level": new_level})\
            .eq("telegram_id", telegram_id)\
            .execute()
        
        return {
            "success": True,
            "points_earned": points,
            "new_balance": new_points,
            "level": new_level
        }
    else:
        # In-memory fallback
        cache_key = f"{telegram_id}_{today}"
        if cache_key not in predictions_memory:
            raise HTTPException(status_code=400, detail="No prediction for today")
        
        if data.code != predictions_memory[cache_key]["code"]:
            raise HTTPException(status_code=400, detail="Invalid verification code")
        
        user = users_memory.get(telegram_id, {})
        points = 100
        user["points"] = user.get("points", 0) + points
        users_memory[telegram_id] = user
        
        return {
            "success": True,
            "points_earned": points,
            "new_balance": user["points"]
        }

@app.post("/api/fortune/spin")
async def spin_fortune(telegram_id: int):
    """Spin the fortune tape"""
    
    today = date.today()
    
    if USE_SUPABASE:
        # Check if already spun today
        result = supabase.table("spins")\
            .select("*")\
            .eq("user_id", telegram_id)\
            .eq("spun_at", str(today))\
            .execute()
        
        if result.data:
            raise HTTPException(status_code=400, detail="Already spun today")
        
        # Random reward
        prizes = [50, 100, 150, 200, 500, 1000]
        weights = [30, 25, 20, 15, 8, 2]
        points = random.choices(prizes, weights=weights)[0]
        
        # Save spin
        supabase.table("spins").insert({
            "user_id": telegram_id,
            "points_won": points
        }).execute()
        
        # Get user
        user_result = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
        user = user_result.data[0]
        
        # Update points
        new_points = user["points"] + points
        new_xp = user["xp"] + points
        new_level = user["level"]
        
        xp_needed = calculate_xp_for_level(new_level)
        while new_xp >= xp_needed:
            new_level += 1
            new_xp -= xp_needed
            xp_needed = calculate_xp_for_level(new_level)
        
        supabase.table("users")\
            .update({
                "points": new_points,
                "xp": new_xp,
                "level": new_level,
                "last_spin": datetime.now().isoformat()
            })\
            .eq("telegram_id", telegram_id)\
            .execute()
        
        return {"points": points, "new_balance": new_points}
    else:
        # In-memory fallback
        prizes = [50, 100, 150, 200, 500, 1000]
        points = random.choice(prizes)
        
        user = users_memory.get(telegram_id, {})
        user["points"] = user.get("points", 0) + points
        users_memory[telegram_id] = user
        
        return {"points": points, "new_balance": user["points"]}

@app.get("/api/leaderboard")
async def get_leaderboard(limit: int = 100):
    """Get top users"""
    
    if USE_SUPABASE:
        result = supabase.table("users")\
            .select("telegram_id, username, level, points")\
            .order("points", desc=True)\
            .limit(limit)\
            .execute()
        
        return [
            {**user, "rank": i + 1}
            for i, user in enumerate(result.data)
        ]
    else:
        # In-memory fallback
        sorted_users = sorted(
            users_memory.values(),
            key=lambda u: u.get("points", 0),
            reverse=True
        )[:limit]
        
        return [
            {
                "telegram_id": u["telegram_id"],
                "username": u["username"],
                "level": u.get("level", 1),
                "points": u.get("points", 0),
                "rank": i + 1
            }
            for i, u in enumerate(sorted_users)
        ]

@app.get("/api/tasks")
async def get_tasks():
    """Get all active tasks"""
    
    if USE_SUPABASE:
        result = supabase.table("tasks")\
            .select("*")\
            .eq("is_active", True)\
            .execute()
        return result.data
    else:
        # Mock tasks
        return [
            {"id": 1, "title": "Join Telegram Channel", "points": 100, "task_type": "telegram_channel", "action_url": "https://t.me/kabbalah_code"},
            {"id": 2, "title": "Follow on Twitter", "points": 150, "task_type": "twitter_follow", "action_url": "https://twitter.com/kabbalah_code"}
        ]

@app.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: int, telegram_id: int):
    """Mark task as completed"""
    
    if USE_SUPABASE:
        # Check if already completed
        result = supabase.table("user_tasks")\
            .select("*")\
            .eq("user_id", telegram_id)\
            .eq("task_id", task_id)\
            .execute()
        
        if result.data:
            raise HTTPException(status_code=400, detail="Task already completed")
        
        # Get task
        task = supabase.table("tasks").select("*").eq("id", task_id).execute()
        if not task.data:
            raise HTTPException(status_code=404, detail="Task not found")
        
        points = task.data[0]["points"]
        
        # Mark as completed
        supabase.table("user_tasks").insert({
            "user_id": telegram_id,
            "task_id": task_id,
            "points_earned": points
        }).execute()
        
        # Award points
        user = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
        new_points = user.data[0]["points"] + points
        
        supabase.table("users")\
            .update({"points": new_points})\
            .eq("telegram_id", telegram_id)\
            .execute()
        
        return {"success": True, "points_earned": points, "new_balance": new_points}
    else:
        return {"success": True, "points_earned": 100, "new_balance": 100}

@app.get("/api/referral/stats")
async def get_referral_stats(telegram_id: int):
    """Get referral statistics"""
    
    if USE_SUPABASE:
        # Get direct referrals (level 1)
        level1 = supabase.table("users").select("telegram_id, points").eq("referrer_id", telegram_id).execute()
        
        level1_ids = [u["telegram_id"] for u in level1.data]
        level1_points = sum(u["points"] for u in level1.data)
        
        # Get level 2 referrals
        level2 = []
        level2_points = 0
        if level1_ids:
            for ref_id in level1_ids:
                refs = supabase.table("users").select("telegram_id, points").eq("referrer_id", ref_id).execute()
                level2.extend(refs.data)
                level2_points += sum(u["points"] for u in refs.data)
        
        # Get level 3 referrals
        level2_ids = [u["telegram_id"] for u in level2]
        level3_points = 0
        if level2_ids:
            for ref_id in level2_ids:
                refs = supabase.table("users").select("points").eq("referrer_id", ref_id).execute()
                level3_points += sum(u["points"] for u in refs.data)
        
        return {
            "level1_count": len(level1.data),
            "level2_count": len(level2),
            "level3_count": len(level2_ids),
            "total_earned": int(level1_points * 0.1 + level2_points * 0.05 + level3_points * 0.02)
        }
    else:
        return {
            "level1_count": 0,
            "level2_count": 0,
            "level3_count": 0,
            "total_earned": 0
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
