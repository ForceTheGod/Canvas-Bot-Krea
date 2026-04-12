import json
import os

DB_FILE = "users.json"

def load_users():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_users(users):
    with open(DB_FILE, "w") as f:
        json.dump(users, f, indent=4)

def get_user(user_id):
    return load_users().get(str(user_id))

def set_user(user_id, token, base_url):
    users = load_users()
    uid_str = str(user_id)
    prev = users.get(uid_str, {})
    users[uid_str] = {
        "token": token, 
        "base_url": base_url.rstrip("/"),
        "announce_notifs": prev.get("announce_notifs", False),
        "grade_notifs": prev.get("grade_notifs", False)
    }
    save_users(users)

def set_notif_prefs(user_id, announce=None, grades=None):
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

def delete_user(user_id):
    users = load_users()
    if str(user_id) in users:
        del users[str(user_id)]
        save_users(users)
        return True
    return False

TRACKER_FILE = "tracker.json"

def load_tracker():
    if not os.path.exists(TRACKER_FILE):
        return {}
    with open(TRACKER_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_tracker(data):
    with open(TRACKER_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_tracker(user_id):
    return load_tracker().get(str(user_id), {"announcements": {}, "grades": {}})

def set_tracker(user_id, key, subkey, val):
    data = load_tracker()
    uid_str = str(user_id)
    if uid_str not in data:
        data[uid_str] = {"announcements": {}, "grades": {}}
    if key not in data[uid_str]:
        data[uid_str][key] = {}
        
    data[uid_str][key][str(subkey)] = val
    save_tracker(data)
