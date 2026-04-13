# Discord Bot Gamification System - Documentation

## Overview
This is a comprehensive gamification system for a Discord bot that integrates with Canvas LMS. Students earn **Canvas Credits (CC)** and **XP** based on their academic performance and habits.

## Features Implemented

### 1. **User Profile & Leveling System**
- **Level**: Based on total XP (1 level per 100 XP)
- **Canvas Credits (CC)**: Virtual currency earned through submissions and good grades
- **Total XP**: Cumulative experience points
- **Active Features**: Time-limited perks and cosmetics

### 2. **Earning Logic**

#### Submission Bonus
- **+50 CC** for any submission

#### Speedrun Multiplier
- **1.5x** if submitted > 12 hours before due date
- **2x** if submitted > 24 hours before due date
- **3x** if submitted > 36 hours before due date

#### Academic Weapon Bonus
- **+100 CC** and **+200 XP** for grades ≥ 90%

#### First Blood Bounty
- **+75 CC** for the first user in the database to submit each assignment

#### Starting Bonus
- CC and XP based on user's total grades when they first register
- Calculated as: `Total Grade × 5` for CC

### 3. **Shop System**

#### Features
- **Grade Ping Priority**: 50 CC - Polls Canvas every 2 minutes for 24 hours
- **Cosmetic Roles**: 100 CC - "Top Tier Student" role for 7 days

#### Visualizations
- **Histogram**: 3 CC
- **Bar Graph**: 5 CC
- **Box Plot**: 7.5 CC
- **Scatter Plot**: 12 CC
- **Regression Analysis**: 15 CC
- **Correlation Heatmap**: 10 CC

### 4. **Commands Implemented**

#### User Commands
- `/profile` - Display level, XP progress, CC balance, and active features
- `/leaderboard` - Top 10 users ranked by XP
- `/balance` - Quick view of CC and XP
- `/howtoearn` - Earning guide and tips
- `/workload` - Upcoming assignments and potential rewards
- `/shop` - Browse items
- `/shop-buy <item>` - Purchase items
- `/analyze` - Open visualization dashboard with button UI

#### Admin Commands (Legacy)
- `!settoken` - Register Canvas API token with gamification initialization
- `!cleartoken` - Remove token
- `!notifications` - Toggle notification settings

### 5. **Background Tasks**

#### Main Polling Task (Every 15 minutes)
- Fetches submissions from Canvas for all registered users
- Calculates rewards based on submission time, grade, and first-submission status
- Awards CC and XP automatically
- Prevents double-rewards using submission history tracking

#### Priority Polling Task (Every 2 minutes)
- For users with "Grade Ping Priority" feature active
- Same reward logic as main polling

#### Cleanup Task (Every hour)
- Removes expired time-limited features
- Cleans up expired roles

### 6. **Security Features**
- Canvas API tokens encrypted using Fernet encryption
- Ephemeral responses for all commands involving sensitive data
- Decryption on-demand only
- Async/await for non-blocking API calls
- Rate limit handling for Canvas API

## Database Schema

### Users (`users.json`)
```json
{
  "discord_id": "encrypted_canvas_token",
  "base_url": "canvas_url",
  "canvas_id": "user_id",
  "username": "student_name",
  "level": 1,
  "xp": 0,
  "cc_balance": 100,
  "total_xp": 0,
  "created_at": "2024-01-01T00:00:00",
  "last_poll": null,
  "announce_notifs": false,
  "grade_notifs": false,
  "special_features": ["feature_name"],
  "active_features": {"feature_name": "expiry_datetime"},
  "purchase_history": [{"item_id": "cost": 50, "purchased_at": "datetime"}]
}
```

### Shop Items (`shop.json`)
```json
{
  "item_id": {
    "name": "Item Name",
    "description": "Description",
    "cost": 50,
    "type": "feature|role|visualization",
    "duration_hours": 24
  }
}
```

### Submission History (`submission_history.json`)
Tracks processed submissions to prevent double-rewarding:
```json
{
  "user_id": {
    "submission_id": {
      "processed_at": "datetime",
      "rewards": {"cc": 50, "xp": 25, "reason": "..."}
    }
  }
}
```

## File Structure

```
main.py                                  # Bot entry point
requirements.txt                         # Python dependencies

utils/
  ├── gamification_db.py                 # Enhanced database module
  ├── earning_logic.py                   # Reward calculation logic
  ├── encryption.py                      # Token encryption
  ├── canvas_api.py                      # Canvas API calls
  └── helpers.py                         # Helper functions

cogs/
  ├── gamification.py                    # User commands cog
  ├── visualizations.py                  # Visualization commands cog
  ├── gamification_background.py         # Background tasks cog
  └── [other existing cogs]

Data files:
  ├── users.json                         # User data
  ├── shop.json                          # Shop items
  ├── submission_history.json            # Processed submissions
  └── .encryption_key                    # Encryption key (auto-generated)
```

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Setup
Create a `.env` file with:
```
DISCORD_TOKEN=your_bot_token
```

### 3. First Run
- Bot will auto-generate encryption key
- Shop items will be initialized on first run
- Users register via `!settoken <canvas_token>`

### 4. User Registration Flow
1. User sends `!settoken <canvas_token> [canvas_url]` in DM
2. Bot validates token and fetches user profile
3. Bot initializes gamification profile with starting bonus
4. User can now use all commands

## API Integrations

### Canvas LMS
- **Endpoint**: `/api/v1/` prefix
- **Auth**: Bearer token in Authorization header
- **Rate Limits**: Standard Canvas rate limiting applies
- **Data Fetched**:
  - Active courses
  - Course submissions
  - Grades and scores
  - Assignment details

## Examples

### Earning Rewards Example
```
User submits assignment:
- 30 hours before due date
- Gets 92% grade

Calculation:
- Base: 50 CC
- Speedrun 2x (>24h early): 50 × 2 = 100 CC
- Academic Weapon (92%): +100 CC
- Total: 200 CC, 200 XP
```

### Visualization Example
```
User runs /analyze:
- Clicks "Scatter Plot (12 CC)" button
- Bot checks balance: ✅ Has 250 CC
- Bot deducts 12 CC
- Bot generates scatter plot from grade data
- Sends image with analysis
```

## Configuration

### Earning Logic Parameters
Located in `utils/earning_logic.py`:
- `SUBMISSION_BONUS_CC = 50`
- `ACADEMIC_WEAPON_CC = 100`
- `ACADEMIC_WEAPON_XP = 200`
- `FIRST_BLOOD_CC = 75`
- `GRADE_BONUS_MULTIPLIER = 5`
- `XP_PER_LEVEL = 100`

### Background Task Intervals
Located in `cogs/gamification_background.py`:
- Main polling: 15 minutes (configurable)
- Priority polling: 2 minutes (configurable)
- Cleanup: 1 hour (configurable)

## Future Enhancements

1. **Achievements System**: Badges for milestones
2. **Guild Leaderboards**: Per-server competition
3. **Seasonal Passes**: Time-limited reward tracks
4. **Trading System**: Users trade CC with each other
5. **Daily Quests**: One-time daily tasks for bonus CC
6. **Social Features**: Friend lists, shared milestones
7. **Mobile App Integration**: Check stats on mobile
8. **Webhook Integration**: Send notifications to other services

## Troubleshooting

### Token Decryption Fails
- Check that `.encryption_key` exists in bot directory
- Ensure token format is correct
- If corrupted, delete `.encryption_key` and re-register

### No Rewards Appearing
- Check if submissions are submitted_at timestamp
- Verify user has active courses
- Check bot permissions in server
- Review polling task logs

### Visualization Command Fails
- Ensure matplotlib is properly installed
- Check matplotlib backend configuration
- Verify enough grade data exists


