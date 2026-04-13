"""
Background task cog - Polls Canvas API and awards gamification rewards
Runs every 15 minutes (or 2 minutes for users with Grade Ping Priority feature)
"""

import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime
from utils import gamification_db, earning_logic
from utils.canvas_api import get_active_courses, get_course_grades, get_canvas_data, get_name
import time


class GamificationBackgroundTasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.polling_task.start()
        self.cleanup_task.start()
    
    def cog_unload(self):
        """Cleanup when cog is unloaded."""
        self.polling_task.cancel()
        self.cleanup_task.cancel()
    
    @tasks.loop(minutes=15)
    async def polling_task(self):
        """Poll Canvas API for all users every 15 minutes."""
        print(f"[{datetime.now()}] Starting gamification polling cycle...")
        
        try:
            users = gamification_db.get_all_users()
            
            # Also check for users with Grade Ping Priority (poll every 2 min)
            priority_users = {
                uid: user for uid, user in users.items()
                if gamification_db.check_active_feature(int(uid), "grade_ping_priority")
            }
            
            # Process all users
            for user_id_str, user in users.items():
                user_id = int(user_id_str)
                
                # Skip if no Canvas token
                if not user.get("canvas_token"):
                    continue
                
                try:
                    await self.process_user_submissions(user_id, user)
                except Exception as e:
                    print(f"Error processing user {user_id}: {e}")
            
            print(f"[{datetime.now()}] Polling cycle complete!")
        
        except Exception as e:
            print(f"Error in polling task: {e}")
    
    @tasks.loop(minutes=2)
    async def priority_polling_task(self):
        """Poll Canvas API every 2 minutes for users with Grade Ping Priority."""
        users = gamification_db.get_all_users()
        
        priority_users = {
            uid: user for uid, user in users.items()
            if gamification_db.check_active_feature(int(uid), "grade_ping_priority")
        }
        
        for user_id_str, user in priority_users.items():
            user_id = int(user_id_str)
            if not user.get("canvas_token"):
                continue
            
            try:
                await self.process_user_submissions(user_id, user)
            except Exception as e:
                print(f"Error in priority polling for user {user_id}: {e}")
    
    @tasks.loop(hours=1)
    async def cleanup_task(self):
        """Cleanup expired features and update user data."""
        print(f"[{datetime.now()}] Running cleanup task...")
        
        try:
            users = gamification_db.get_all_users()
            
            for user_id_str, user in users.items():
                if user.get("active_features"):
                    # Check and remove expired features
                    for feature in list(user.get("active_features", {}).keys()):
                        gamification_db.check_active_feature(int(user_id_str), feature)
            
            print(f"[{datetime.now()}] Cleanup complete!")
        
        except Exception as e:
            print(f"Error in cleanup task: {e}")
    
    async def process_user_submissions(self, user_id: int, user: dict):
        """Process submissions for a single user."""
        token = gamification_db.get_decrypted_token(user_id)
        if not token:
            return
        
        base_url = user.get("base_url")
        
        try:
            # Get active courses
            courses = await get_active_courses(base_url, token)
            if not courses:
                return
            
            total_rewards = {"cc": 0, "xp": 0, "reasons": []}
            
            # Process each course
            for course in courses:
                course_id = course.get("id")
                if not course_id:
                    continue
                
                try:
                    # This gets current user's submissions (not all submissions)
                    submissions = await get_course_grades(base_url, token, course_id)
                    
                    if not submissions:
                        continue
                    
                    # Process each submission
                    for submission in submissions:
                        if submission.get("submitted_at") and submission.get("id"):
                            reward = await earning_logic.SubmissionProcessor.process_submission(
                                user_id,
                                submission,
                                user_total_grade=course.get("computed_current_score")
                            )
                            
                            if reward:
                                total_rewards["cc"] += reward["cc"]
                                total_rewards["xp"] += reward["xp"]
                                total_rewards["reasons"].append(
                                    f"{reward['reason']}"
                                )
                
                except Exception as e:
                    print(f"Error processing course {course_id}: {e}")
                    continue
            
            # Award rewards to user
            if total_rewards["cc"] > 0 or total_rewards["xp"] > 0:
                gamification_db.update_user_cc(user_id, total_rewards["cc"])
                gamification_db.update_user_xp(user_id, total_rewards["xp"])
                
                # Try to notify user
                try:
                    discord_user = await self.bot.fetch_user(user_id)
                    embed = discord.Embed(
                        title="🎉 Rewards Earned!",
                        description=f"**+{total_rewards['cc']}** CC | **+{total_rewards['xp']}** XP",
                        color=discord.Color.gold()
                    )
                    
                    reason_text = "\n".join(total_rewards["reasons"][:5])
                    if len(total_rewards["reasons"]) > 5:
                        reason_text += f"\n... and {len(total_rewards['reasons']) - 5} more"
                    
                    embed.add_field(name="Reasons", value=reason_text, inline=False)
                    
                    # Get updated user for level display
                    updated_user = gamification_db.get_user(user_id)
                    level = earning_logic.LevelCalculator.get_level_from_xp(
                        updated_user.get("total_xp", 0)
                    )
                    
                    embed.add_field(name="📊 New Stats", value=f"Level: **{level}** | CC: **{updated_user.get('cc_balance', 0)}**", inline=False)
                    
                    await discord_user.send(embed=embed)
                except Exception as e:
                    print(f"Could not notify user {user_id}: {e}")
        
        except Exception as e:
            print(f"Error processing user {user_id} submissions: {e}")
    
    @polling_task.before_loop
    async def before_polling_task(self):
        """Wait for bot to be ready before starting polling."""
        await self.bot.wait_until_ready()
    
    @cleanup_task.before_loop
    async def before_cleanup_task(self):
        """Wait for bot to be ready before starting cleanup."""
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(GamificationBackgroundTasks(bot))
