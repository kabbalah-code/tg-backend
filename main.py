"""
Kabbalah Code - Backend API
Deploy to Render.com (free tier)
Python 3.10+
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta
import random
import string

# Initialize FastAPI
app = FastAPI(title="Kabbalah Code API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (replace with Supabase/PostgreSQL for production)
users_db = {}
predictions_db = {}
referrals_db = {}
tasks_db = []
ugc_submissions = []

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_bot_token_here")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "KABBALAH_ADMIN_2025")

# Models
class UserOnboard(BaseModel):
    telegram_id: str
    username: str
    evm_address: str = Field(pattern=r"^0x[a-fA-F0-9]{40}$")
    twitter_username: str

class User(BaseModel):
    telegram_id: str
    username: str
    evm_address: str
    twitter_username: str
    level: int = 1
    xp: int = 0
    points: int = 0
    referrer_id: Optional[str] = None
    last_spin: Optional[datetime] = None
    last_prediction: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)

class PredictionResponse(BaseModel):
    text: str
    image_url: str
    code: str
    mystical_hash: str

class VerifyCode(BaseModel):
    code: str
    tweet_url: str

class SpinResult(BaseModel):
    points: int
    
class Task(BaseModel):
    id: str
    title: str
    description: str
    points: int
    task_type: str
    url: Optional[str] = None
    
class UGCSubmission(BaseModel):
    user_id: str
    content_type: str
    url: str
    points_claim: int

# Utility Functions
def verify_telegram_auth(init_data: str) -> dict:
    """Verify Telegram WebApp initData"""
    try:
        data = dict(x.split('=') for x in init_data.split('&'))
        hash_value = data.pop('hash', None)
        
        data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(data.items()))
        secret_key = hmac.new(
            b"WebAppData",
            TELEGRAM_BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()
        
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if calculated_hash == hash_value:
            return json.loads(data.get('user', '{}'))
        return None
    except:
        return None

def generate_mystical_code() -> str:
    """Generate unique verification code"""
    return 'KC' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_prediction() -> dict:
    """Generate daily prediction"""
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
    """Calculate XP needed for next level"""
    return 1000 * level + 500 * (level - 1)

def add_points_and_xp(user: User, points: int):
    """Add points and XP, handle level up"""
    user.points += points
    user.xp += points
    
    xp_needed = calculate_xp_for_level(user.level)
    if user.xp >= xp_needed:
        user.level += 1
        user.xp -= xp_needed
        
    # Distribute referral rewards
    if user.referrer_id and user.referrer_id in users_db:
        referrer = users_db[user.referrer_id]
        referrer.points += int(points * 0.10)  # 10% level 1
        
        # Level 2 referral
        if referrer.referrer_id and referrer.referrer_id in users_db:
            level2_ref = users_db[referrer.referrer_id]
            level2_ref.points += int(points * 0.05)  # 5% level 2
            
            # Level 3 referral
            if level2_ref.referrer_id and level2_ref.referrer_id in users_db:
                level3_ref = users_db[level2_ref.referrer_id]
                level3_ref.points += int(points * 0.02)  # 2% level 3

# Authentication
async def get_current_user(authorization: str = Header(None)) -> User:
    """Get current user from Telegram auth"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # In production: verify Telegram initData
    # For demo: extract user_id from header
    user_id = authorization.replace("Bearer ", "")
    
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    return users_db[user_id]

async def verify_admin(authorization: str = Header(None)):
    """Verify admin access"""
    if not authorization or authorization.replace("Bearer ", "") != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Admin access denied")

# API Endpoints

@app.get("/")
async def root():
    return {
        "service": "Kabbalah Code API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.post("/api/auth/onboard")
async def onboard_user(data: UserOnboard, referrer: Optional[str] = None):
    """Onboard new user"""
    user = User(
        telegram_id=data.telegram_id,
        username=data.username,
        evm_address=data.evm_address,
        twitter_username=data.twitter_username,
        referrer_id=referrer
    )
    
    users_db[data.telegram_id] = user
    
    return {
        "success": True,
        "user": user.dict()
    }

@app.get("/api/user/profile")
async def get_profile(user: User = Depends(get_current_user)):
    """Get user profile"""
    referral_count = sum(1 for u in users_db.values() if u.referrer_id == user.telegram_id)
    
    return {
        "user": user.dict(),
        "referral_count": referral_count,
        "xp_to_next": calculate_xp_for_level(user.level)
    }

@app.get("/api/prediction/daily")
async def get_daily_prediction(user: User = Depends(get_current_user)):
    """Get daily prediction"""
    today = datetime.now().date()
    
    if user.last_prediction and user.last_prediction.date() == today:
        # Return cached prediction
        cache_key = f"{user.telegram_id}_{today}"
        if cache_key in predictions_db:
            return predictions_db[cache_key]
    
    # Generate new prediction
    prediction = generate_prediction()
    cache_key = f"{user.telegram_id}_{today}"
    predictions_db[cache_key] = prediction
    user.last_prediction = datetime.now()
    
    return prediction

@app.post("/api/prediction/verify")
async def verify_prediction(
    data: VerifyCode,
    user: User = Depends(get_current_user)
):
    """Verify tweet and award points"""
    # In production: check tweet via Twitter API or oEmbed
    # For demo: simple validation
    
    today = datetime.now().date()
    cache_key = f"{user.telegram_id}_{today}"
    
    if cache_key not in predictions_db:
        raise HTTPException(status_code=400, detail="No prediction for today")
    
    prediction = predictions_db[cache_key]
    
    if data.code != prediction['code']:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Award points
    points = 100
    add_points_and_xp(user, points)
    
    return {
        "success": True,
        "points_earned": points,
        "new_balance": user.points
    }

@app.post("/api/fortune/spin")
async def spin_fortune(user: User = Depends(get_current_user)):
    """Spin the fortune tape"""
    today = datetime.now().date()
    
    if user.last_spin and user.last_spin.date() == today:
        raise HTTPException(status_code=400, detail="Already spun today")
    
    # Random reward
    prizes = [50, 100, 150, 200, 500, 1000]
    weights = [30, 25, 20, 15, 8, 2]
    points = random.choices(prizes, weights=weights)[0]
    
    add_points_and_xp(user, points)
    user.last_spin = datetime.now()
    
    return {
        "points": points,
        "new_balance": user.points
    }

@app.get("/api/leaderboard")
async def get_leaderboard(limit: int = 100):
    """Get top users"""
    sorted_users = sorted(
        users_db.values(),
        key=lambda u: u.points,
        reverse=True
    )[:limit]
    
    return [
        {
            "username": u.username,
            "level": u.level,
            "points": u.points,
            "rank": i + 1
        }
        for i, u in enumerate(sorted_users)
    ]

@app.get("/api/referral/stats")
async def get_referral_stats(user: User = Depends(get_current_user)):
    """Get referral statistics"""
    direct_referrals = [u for u in users_db.values() if u.referrer_id == user.telegram_id]
    
    level2_refs = []
    for ref in direct_referrals:
        level2_refs.extend([u for u in users_db.values() if u.referrer_id == ref.telegram_id])
    
    level3_refs = []
    for ref in level2_refs:
        level3_refs.extend([u for u in users_db.values() if u.referrer_id == ref.telegram_id])
    
    return {
        "level1_count": len(direct_referrals),
        "level2_count": len(level2_refs),
        "level3_count": len(level3_refs),
        "total_earned": sum(u.points for u in direct_referrals) * 0.1
    }

# Admin Endpoints

@app.get("/api/admin/users", dependencies=[Depends(verify_admin)])
async def admin_get_users(limit: int = 100):
    """Get all users (admin)"""
    return list(users_db.values())[:limit]

@app.post("/api/admin/points", dependencies=[Depends(verify_admin)])
async def admin_adjust_points(user_id: str, points: int):
    """Manually adjust user points (admin)"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = users_db[user_id]
    user.points += points
    
    return {"success": True, "new_balance": user.points}

@app.post("/api/admin/task", dependencies=[Depends(verify_admin)])
async def admin_create_task(task: Task):
    """Create new task (admin)"""
    tasks_db.append(task)
    return {"success": True, "task": task}

@app.get("/api/admin/ugc", dependencies=[Depends(verify_admin)])
async def admin_get_ugc():
    """Get UGC submissions (admin)"""
    return ugc_submissions

@app.post("/api/admin/ugc/approve", dependencies=[Depends(verify_admin)])
async def admin_approve_ugc(submission_id: str, points: int):
    """Approve UGC submission (admin)"""
    # Find submission and award points
    return {"success": True, "points_awarded": points}

# Health check for Render
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
