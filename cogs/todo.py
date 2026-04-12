import discord
from discord.ext import commands
from utils.canvas_api import get_todo_items, get_active_courses
from utils.database import get_user
import datetime

class Todo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["todo", "due"])
    async def whats_due(self, ctx):
        """
        Snapshot of your workload directly in Discord!
        Displays upcoming Canvas assignments with color-coded urgency.
        """
        user = get_user(ctx.author.id)
        if not user:
            await ctx.send("❌ You haven't set your Canvas API token yet! Use `!settoken <your_token>` in my DMs first.")
            return

        msg = await ctx.send("📋 **Fetching your pending task list...**")
        todos = await get_todo_items(user["base_url"], user["token"])
        
        if not todos:
            embed = discord.Embed(
                title="✅ What's Due? Nothing!", 
                description="Your workload is completely clear! Take a break. 🛋️",
                color=discord.Color.green()
            )
            await msg.edit(content=None, embed=embed)
            return

        # Fetch active courses to map course_id to human readable course names
        courses = await get_active_courses(user["base_url"], user["token"])
        course_map = {c.get("id"): c.get("name", "Unknown Course") for c in courses} if courses else {}

        now = datetime.datetime.now(datetime.timezone.utc)
        
        red_items = []
        yellow_items = []
        green_items = []
        
        for item in todos[:20]: # Parse up to 20 to avoid discord size limits
            assignment = item.get("assignment", {})
            quiz = item.get("quiz", {})
            
            # Try to grab title from assignment first, then quiz, then default string
            title = assignment.get("name") or quiz.get("title") or "Unnamed Task"
            
            # Map course name
            course_id = item.get("course_id") or assignment.get("course_id")
            course_name = course_map.get(course_id, "")
            course_header = f"[{course_name}] " if course_name else ""
            
            # Try to get due date string
            due_at_str = assignment.get("due_at") or quiz.get("due_at")
            
            if due_at_str:
                try:
                    dt = datetime.datetime.fromisoformat(due_at_str.replace("Z", "+00:00"))
                    diff = dt - now
                    hours_diff = diff.total_seconds() / 3600
                except:
                    hours_diff = 999
                    dt = None
            else:
                hours_diff = 999
                dt = None

            if dt:
                dt_formatted = dt.strftime("%B %d at %I:%M %p")
            else:
                dt_formatted = "No strict deadline specified"

            # Parse HTML URL context
            url = item.get("html_url") or assignment.get("html_url") or quiz.get("html_url")
            link_str = f" - [View]({url})" if url else ""

            info = f"**{course_header}{title}**{link_str}\n*Due: {dt_formatted}*\n"
            
            if hours_diff < 0:
                # Overdue (Counts as Red)
                red_items.append(f"🚨 **OVERDUE:**\n" + info)
            elif hours_diff <= 24:
                red_items.append(info)
            elif hours_diff <= 72:
                yellow_items.append(info)
            else:
                green_items.append(info)

        # Logic for Embed Color
        if red_items:
            color = discord.Color.red()
            main_title = "🚨 ❗ What's Due? ⏳ 🚨"
        elif yellow_items:
            color = discord.Color.gold()
            main_title = "⚠️ 🟡 What's Due?"
        else:
            color = discord.Color.green()
            main_title = "✅ 🟢 What's Due?"

        embed = discord.Embed(title=main_title, color=color)
        
        # Helper to safely join items
        def build_field(item_list):
            val = "\n".join(item_list)
            if len(val) > 1024:
                val = val[:1020] + "..."
            return val

        if red_items:
            embed.add_field(name="🚨 Due in < 24 Hours ❗", value=build_field(red_items), inline=False)
        if yellow_items:
            embed.add_field(name="⚠️ Due in < 72 Hours 🟡", value=build_field(yellow_items), inline=False)
        if green_items:
            embed.add_field(name="✅ Due Later 🟢", value=build_field(green_items), inline=False)
            
        await msg.edit(content=None, embed=embed)

async def setup(bot):
    await bot.add_cog(Todo(bot))
