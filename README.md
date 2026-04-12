# Canvas Discord Bot

A Discord bot that integrates with the Canvas API, allowing users to securely enter their Canvas token in DMs and interact with their canvas data (Grades, Announcements, etc.) straight from Discord!

## Features
- Secure token storage for multiple users.
- Connect your Canvas courses by simply adding a token and an optional base url wrapper.
- Look up current grades, estimated CGPA, and view recent grade scores.
- Interactive course selections for Detailed Grades and Course Announcements.
- **Live Notifications:** Receive instant DMs whenever a new Announcement is posted or a Grade is scored (complete with class distribution statistics).

## WorkSpace Setup
This repository uses a clean modular structure with Cogs.
1. `cogs/` - Discord Cogs commands (Setup, Grades, Courses)
2. `utils/` - Helpers, Canvas API fetchers, and DB wrapper.
3. `main.py` - Core bot execution. 

## Commands
* `!settoken <token> [base_url]` - Register a Canvas API token.
* `!tokenhelp` - Step-by-step instructions on generating your Canvas API token.
* `!cleartoken` - Remove your token from the bot's database.
* `!notifications` - Subscribe or unsubscribe to background LIVE tracking (Announcements/Grades) globally.
* `!grades` - View overall grades.
* `!cgpa` - Calculate average/estimated CGPA.
* `!maxmin` - View highest and lowest courses.
* `!find [keyword]` - Search for specific files across all actively enrolled courses (Download links provided!).
* `!syllabus` - Read the detailed Syllabus and Course Summary by picking from a drop down menu.
* `!calendar` - View events from your canvas calendar based on a selected date.
* `!due` / `!todo`/ `!whats_due` - Quick dashboard snapshot of upcoming assignments color coded by urgency limit.
* `!announcement` - Select a course and view the last 5 announcements.
* `!grade_details` - View detailed scores for assignments inside a specific course.

## How to Run
1. Install dependencies: `pip install -r requirements.txt`
2. Rename `.env.example` to `.env` and fill in your Discord Bot Token:
   `DISCORD_TOKEN=your_token_here`
3. Run the bot: `python main.py`

## Maintainer

* **Maintained by Haresh** - [ForceTheGod](https://github.com/ForceTheGod)

Feel free to reach out if you have any questions or want to contribute!

* Note that this project is intended for use by students of Krea University. Any other use might result in breaking of code.