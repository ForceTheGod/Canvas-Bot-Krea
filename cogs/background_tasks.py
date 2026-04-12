import discord
from discord.ext import commands, tasks
from utils.canvas_api import get_active_courses, get_announcements, get_course_grades, get_assignments
from utils.database import load_users, get_tracker, set_tracker
from utils.helpers import clean_html

class BackgroundTasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tracker_loop.start()

    def cog_unload(self):
        self.tracker_loop.cancel()

    @tasks.loop(minutes=20.0)
    async def tracker_loop(self):
        print("Running background tracker for Announcements and Grades...")
        users = load_users()
        
        for user_id_str, user_data in users.items():
            try:
                user_id = int(user_id_str)
                discord_user = self.bot.get_user(user_id)
                if not discord_user:
                    try:
                        discord_user = await self.bot.fetch_user(user_id)
                    except:
                        continue
                        
                base_url = user_data.get("base_url")
                token = user_data.get("token")
                
                courses = await get_active_courses(base_url, token)
                if not courses:
                    continue
                    
                course_map = {c["id"]: c.get("name", "Unknown Course") for c in courses}
                
                tracker = get_tracker(user_id)
                ann_tracker = tracker.get("announcements", {})
                grade_tracker = tracker.get("grades", {})

                # Check courses one by one
                for c_id, c_name in course_map.items():
                    # --- 1. ANNOUNCEMENTS ---
                    anns = await get_announcements(base_url, token, c_id)
                    if anns:
                        last_seen_id = ann_tracker.get(str(c_id))
                        is_new_ann_tracking = (last_seen_id is None)
                        last_seen_id = last_seen_id or 0
                        
                        new_max_id = last_seen_id
                        
                        # Sort oldest to newest
                        anns.sort(key=lambda x: x.get("id", 0))
                        
                        for ann in anns:
                            ann_id = ann.get("id", 0)
                            if ann_id > last_seen_id:
                                if not is_new_ann_tracking:
                                    title = ann.get("title", "Untitled Announcement")
                                    desc_html = ann.get("message", "")
                                    desc = clean_html(desc_html)[:300]
                                    if len(clean_html(desc_html)) > 300:
                                        desc += "..."
                                        
                                    url = ann.get("html_url")
                                    embed = discord.Embed(
                                        title=f"📢 New Announcement: {c_name}", 
                                        color=discord.Color.blue(), 
                                        description=f"**{title}**\n\n{desc}"
                                    )
                                    if url:
                                        embed.add_field(name="Link", value=f"[Read on Canvas]({url})")
                                        
                                    try:
                                        if user_data.get("announce_notifs", False):
                                            await discord_user.send(content=f"Hey {discord_user.mention}, you have a new announcement!", embed=embed)
                                    except:
                                        pass
                                        
                                if ann_id > new_max_id:
                                    new_max_id = ann_id
                                    
                        if new_max_id > last_seen_id or is_new_ann_tracking:
                            set_tracker(user_id, "announcements", c_id, new_max_id)


                    # --- 2. GRADES ---
                    subs = await get_course_grades(base_url, token, c_id)
                    assignments = await get_assignments(base_url, token, c_id)
                    if not subs or not assignments:
                        continue
                        
                    a_map = {a["id"]: a for a in assignments}
                    
                    course_subs = grade_tracker.get(str(c_id))
                    is_new_grade_tracking = (course_subs is None)
                    if is_new_grade_tracking:
                        course_subs = {}
                        
                    updates_made = False
                    
                    for sub in subs:
                        sub_id = str(sub.get("assignment_id"))
                        score = sub.get("score")
                        if score is None: 
                            continue # Not graded yet
                            
                        prev_score = course_subs.get(sub_id)
                        
                        if prev_score != score:
                            if not is_new_grade_tracking:
                                assignment = a_map.get(sub.get("assignment_id"), {})
                                max_score = assignment.get("points_possible", "?")
                                name = assignment.get("name", "Unknown Assignment")
                                
                                embed = discord.Embed(
                                    title=f"🎓 Grade Update: {c_name}", 
                                    color=discord.Color.green(),
                                    description=f"Your grade for **{name}** has been posted or updated!"
                                )
                                embed.add_field(name="Score", value=f"`{score} / {max_score}`", inline=False)
                                
                                stats = sub.get("score_statistics")
                                if stats:
                                    stat_str = f"Mean: `{stats.get('mean', '?')}` | Max: `{stats.get('max', '?')}` | Min: `{stats.get('min', '?')}`"
                                    embed.add_field(name="Class Statistics", value=stat_str, inline=False)
                                
                                url = assignment.get("html_url")
                                if url:
                                    embed.add_field(name="Link", value=f"[View Assignment]({url})", inline=False)
                                    
                                try:
                                    if user_data.get("grade_notifs", False):
                                        await discord_user.send(content=f"Hey {discord_user.mention}, you have a grade update!", embed=embed)
                                except:
                                    pass
                                    
                            course_subs[sub_id] = score
                            updates_made = True
                            
                    if updates_made or is_new_grade_tracking:
                        set_tracker(user_id, "grades", c_id, course_subs)

            except Exception as e:
                print(f"Error checking background tasks for {user_id_str}: {e}")

    @tracker_loop.before_loop
    async def before_tracker(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(BackgroundTasks(bot))
