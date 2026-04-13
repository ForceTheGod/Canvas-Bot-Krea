"""
Enhanced database module with gamification features.
Manages users, shop items, earning history, and game state.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from utils.encryption import encrypt_token, decrypt_token

DB_FILE = "users.json"
SHOP_FILE = "shop.json"
HISTORY_FILE = "earning_history.json"

# ============= USER DATABASE =============

def load_users():
    """Load all users from database."""
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_users(users):
    """Save users to database."""
    with open(DB_FILE, "w") as f:
        json.dump(users, f, indent=4)

def get_user(user_id: int) -> Optional[Dict]:
    """Get user data by Discord ID."""
    return load_users().get(str(user_id))

def create_user(user_id: int, canvas_token: str, base_url: str) -> Dict:
    """Create a new user with gamification fields."""
    users = load_users()
    uid_str = str(user_id)
    
    # Encrypt the token
    encrypted_token = encrypt_token(canvas_token)
    
    users[uid_str] = {
        "canvas_token": encrypted_token,
        "base_url": base_url.rstrip("/"),
        "discord_id": user_id,
        "username": None,  # Will be filled from Canvas
        "level": 1,
        "xp": 0,
        "cc_balance": 0,  # Canvas Credits
        "total_xp": 0,
        "created_at": datetime.now().isoformat(),
        "last_poll": None,
        "announce_notifs": False,
        "grade_notifs": False,
        "special_features": [],  # ["grade_ping_priority", "cosmetic_role"]
        "active_features": {},  # {"grade_ping_priority": datetime, "cosmetic_role": datetime}
        "purchase_history": []
    }
    
    save_users(users)
    return users[uid_str]

def set_user(user_id: int, token: str, base_url: str):
    """Legacy function - kept for backward compatibility."""
    users = load_users()
    uid_str = str(user_id)
    
    encrypted_token = encrypt_token(token)
    
    prev = users.get(uid_str, {})
    users[uid_str] = {
        "canvas_token": encrypted_token,
        "base_url": base_url.rstrip("/"),
        "discord_id": user_id,
        "level": prev.get("level", 1),
        "xp": prev.get("xp", 0),
        "cc_balance": prev.get("cc_balance", 0),
        "total_xp": prev.get("total_xp", 0),
        "created_at": prev.get("created_at", datetime.now().isoformat()),
        "announce_notifs": prev.get("announce_notifs", False),
        "grade_notifs": prev.get("grade_notifs", False),
        "special_features": prev.get("special_features", []),
        "active_features": prev.get("active_features", {}),
        "purchase_history": prev.get("purchase_history", [])
    }
    save_users(users)

def get_decrypted_token(user_id: int) -> Optional[str]:
    """Get and decrypt user's Canvas API token."""
    user = get_user(user_id)
    if not user:
        return None
    encrypted_token = user.get("canvas_token")
    if not encrypted_token:
        return None
    return decrypt_token(encrypted_token)

def update_user_xp(user_id: int, xp_amount: int):
    """Add XP to user and update level."""
    users = load_users()
    uid_str = str(user_id)
    
    if uid_str not in users:
        return False
    
    users[uid_str]["xp"] += xp_amount
    users[uid_str]["total_xp"] += xp_amount
    
    # Level up formula: 100 XP per level
    users[uid_str]["level"] = 1 + (users[uid_str]["total_xp"] // 100)
    
    save_users(users)
    return True

def update_user_cc(user_id: int, cc_amount: int):
    """Add or subtract Canvas Credits from user."""
    users = load_users()
    uid_str = str(user_id)
    
    if uid_str not in users:
        return False
    
    users[uid_str]["cc_balance"] = max(0, users[uid_str]["cc_balance"] + cc_amount)
    save_users(users)
    return True

def set_notif_prefs(user_id: int, announce=None, grades=None):
    """Set user notification preferences."""
    users = load_users()
    uid_str = str(user_id)
    
    if uid_str not in users:
        return False
    
    if announce is not None:
        users[uid_str]["announce_notifs"] = announce
    if grades is not None:
        users[uid_str]["grade_notifs"] = grades
    
    save_users(users)
    return True

def delete_user(user_id: int):
    """Delete user from database."""
    users = load_users()
    if str(user_id) in users:
        del users[str(user_id)]
        save_users(users)
        return True
    return False

def get_all_users() -> Dict:
    """Get all users (for leaderboard, etc.)."""
    return load_users()

def get_user_by_rank(rank: int) -> Optional[Dict]:
    """Get user at specific rank (1-indexed)."""
    users = load_users()
    sorted_users = sorted(users.values(), key=lambda u: u.get("total_xp", 0), reverse=True)
    if 0 <= rank - 1 < len(sorted_users):
        return sorted_users[rank - 1]
    return None

def get_top_users(limit: int = 10) -> List[Dict]:
    """Get top users by XP (for leaderboard)."""
    users = load_users()
    sorted_users = sorted(users.values(), key=lambda u: u.get("total_xp", 0), reverse=True)
    return sorted_users[:limit]

def add_active_feature(user_id: int, feature: str, duration_hours: int):
    """Activate a time-limited feature for user."""
    users = load_users()
    uid_str = str(user_id)
    
    if uid_str not in users:
        return False
    
    expiry = datetime.now() + timedelta(hours=duration_hours)
    users[uid_str]["active_features"][feature] = expiry.isoformat()
    
    if feature not in users[uid_str]["special_features"]:
        users[uid_str]["special_features"].append(feature)
    
    save_users(users)
    return True

def check_active_feature(user_id: int, feature: str) -> bool:
    """Check if user has an active time-limited feature."""
    user = get_user(user_id)
    if not user:
        return False
    
    active_features = user.get("active_features", {})
    if feature not in active_features:
        return False
    
    expiry_str = active_features[feature]
    expiry = datetime.fromisoformat(expiry_str)
    
    if datetime.now() > expiry:
        # Feature expired, remove it
        del active_features[feature]
        users = load_users()
        users[str(user_id)]["active_features"] = active_features
        save_users(users)
        return False
    
    return True

def record_purchase(user_id: int, item_id: str, cost: int):
    """Record a shop purchase for user."""
    users = load_users()
    uid_str = str(user_id)
    
    if uid_str not in users:
        return False
    
    users[uid_str]["purchase_history"].append({
        "item_id": item_id,
        "cost": cost,
        "purchased_at": datetime.now().isoformat()
    })
    
    save_users(users)
    return True

# ============= SUBMISSION HISTORY =============

SUBMISSION_HISTORY_FILE = "submission_history.json"

def load_submission_history():
    """Load processed submission IDs to prevent double-rewarding."""
    if not os.path.exists(SUBMISSION_HISTORY_FILE):
        return {}
    with open(SUBMISSION_HISTORY_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_submission_history(data):
    """Save submission history."""
    with open(SUBMISSION_HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

def is_submission_processed(user_id: int, submission_id: int) -> bool:
    """Check if submission was already processed."""
    history = load_submission_history()
    return str(submission_id) in history.get(str(user_id), {})

def mark_submission_processed(user_id: int, submission_id: int, rewards: Dict):
    """Mark submission as processed and store reward info."""
    history = load_submission_history()
    uid_str = str(user_id)
    
    if uid_str not in history:
        history[uid_str] = {}
    
    history[uid_str][str(submission_id)] = {
        "processed_at": datetime.now().isoformat(),
        "rewards": rewards
    }
    
    save_submission_history(history)

def get_first_submission_user(submission_id: int) -> Optional[int]:
    """Get the first user to submit a specific assignment."""
    history = load_submission_history()
    
    # Find the earliest submission_id across all users
    earliest_user = None
    earliest_time = None
    
    for user_id_str, submissions in history.items():
        if str(submission_id) in submissions:
            processed_time = submissions[str(submission_id)].get("processed_at")
            if processed_time:
                if earliest_time is None or processed_time < earliest_time:
                    earliest_time = processed_time
                    earliest_user = int(user_id_str)
    
    return earliest_user

# ============= SHOP DATABASE =============

def initialize_shop():
    """Initialize shop items if not exists."""
    if os.path.exists(SHOP_FILE):
        return
    
    shop_items = {
        "grade_ping_priority": {
            "name": "Grade Ping Priority",
            "description": "Polls Canvas every 2 minutes for 24 hours",
            "cost": 50,
            "type": "feature",
            "duration_hours": 24
        },
        "cosmetic_role": {
            "name": "Cosmetic Roles",
            "description": "Get 'Top Tier Student' role for 7 days",
            "cost": 100,
            "type": "role",
            "duration_hours": 168
        },
        "histogram": {
            "name": "Histogram Visualization",
            "description": "Generate histograms for grade analysis",
            "cost": 3,
            "type": "visualization"
        },
        "bar_graph": {
            "name": "Bar Graph Visualization",
            "description": "Generate bar graphs for grade analysis",
            "cost": 5,
            "type": "visualization"
        },
        "box_plot": {
            "name": "Box Plot Visualization",
            "description": "Generate box plots for grade analysis",
            "cost": 7.5,
            "type": "visualization"
        },
        "scatter_plot": {
            "name": "Scatter Plot Visualization",
            "description": "Generate scatter plots for grade analysis",
            "cost": 12,
            "type": "visualization"
        },
        "regression_analysis": {
            "name": "Regression Analysis",
            "description": "Analyze trends in your grades",
            "cost": 15,
            "type": "visualization"
        },
        "correlation_heatmap": {
            "name": "Correlation Heatmap",
            "description": "Analyze correlations between grades, submission times, and missing assignments",
            "cost": 10,
            "type": "visualization"
        }
    }
    
    with open(SHOP_FILE, "w") as f:
        json.dump(shop_items, f, indent=4)

def load_shop():
    """Load shop items."""
    if not os.path.exists(SHOP_FILE):
        initialize_shop()
    
    with open(SHOP_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def get_shop_item(item_id: str) -> Optional[Dict]:
    """Get specific shop item."""
    shop = load_shop()
    return shop.get(item_id)

def get_all_shop_items() -> Dict:
    """Get all shop items."""
    return load_shop()

# ============= TRACKER (Legacy) =============

TRACKER_FILE = "tracker.json"

def load_tracker():
    """Load tracker data."""
    if not os.path.exists(TRACKER_FILE):
        return {}
    with open(TRACKER_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_tracker(data):
    """Save tracker data."""
    with open(TRACKER_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_tracker(user_id: int):
    """Get tracker for user."""
    return load_tracker().get(str(user_id), {"announcements": {}, "grades": {}})

def set_tracker(user_id: int, key: str, subkey, val):
    """Set tracker value."""
    data = load_tracker()
    uid_str = str(user_id)
    if uid_str not in data:
        data[uid_str] = {"announcements": {}, "grades": {}}
    if key not in data[uid_str]:
        data[uid_str][key] = {}
    
    data[uid_str][key][str(subkey)] = val
    save_tracker(data)

# Initialize shop on module load
initialize_shop()
