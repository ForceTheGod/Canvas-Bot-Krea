import discord
from discord.ext import commands
from discord.ui import View, Select, Button, Modal, TextInput
from utils.canvas_api import get_calendar_events, get_active_courses
from utils.database import get_user
from utils.helpers import clean_html
import datetime

# Helper to format a single event neatly on one line/field
def format_event_inline(ev):
    desc = ""
    html_desc = ev.get("description")
    if html_desc:
        desc = clean_html(html_desc)[:100]
        if len(desc) == 100: desc += "..."
            
    venue = ev.get("location_name") or "No Venue specified"
    
    start_at = ev.get("start_at") 
    if start_at:
        try:
            dt = datetime.datetime.fromisoformat(start_at.replace("Z", "+00:00"))
            dt_str = dt.strftime("%B %d at %I:%M %p")
        except:
            dt_str = start_at
    else:
        dt_str = "All Day"
        
    info = f"**Time:** {dt_str} | **Venue:** {venue}"
    if desc:
        info += f"\n**Details:** {desc}"
    return info

# Helper to format full scale events block
def format_events_embed(events, date_str):
    if not events:
        embed = discord.Embed(title=f"📅 Events on {date_str}", description="No events found for this day.", color=discord.Color.light_gray())
        return embed

    embed = discord.Embed(title=f"📅 Events on {date_str}", color=discord.Color.purple())

    for ev in events[:10]: # Max 10 fields to not hit discord limits
        title = ev.get("title") or "Untitled Event"
        context_name = ev.get("context_name") or ""
        
        info = f"**Course:** {context_name}\n" + format_event_inline(ev)
        embed.add_field(name=title, value=info, inline=False)
        
    if len(events) > 10:
        embed.set_footer(text=f"And {len(events) - 10} more events not shown.")
        
    return embed

class CalendarCourseSelect(Select):
    def __init__(self, courses, user):
        self.user = user
        options = [
            discord.SelectOption(label=c.get("name", "Unnamed")[:100], value=str(c.get("id")))
            for c in courses[:25]
        ]
        if not options:
            options = [discord.SelectOption(label="No courses available", value="none")]
            
        super().__init__(placeholder="Upcoming sessions by Course...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        course_id = self.values[0]
        if course_id == "none":
            await interaction.followup.send("No courses available.", ephemeral=True)
            return

        course_name = next((c.get("name", "Unknown") for c in self.view.courses if str(c.get("id")) == course_id), "Unknown")
        
        target_date = datetime.datetime.now(datetime.timezone.utc)
        
        start_date_str = (target_date - datetime.timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")
        end_date_str = (target_date + datetime.timedelta(days=60)).strftime("%Y-%m-%dT23:59:59Z")
        
        context_codes = [f"course_{course_id}"]
        events = await get_calendar_events(self.user["base_url"], self.user["token"], start_date_str, end_date_str, context_codes)
        
        events_sorted = [ev for ev in events if ev.get("start_at")]
        events_sorted.sort(key=lambda x: x.get("start_at"))
        
        now_iso = target_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        prev_events = [ev for ev in events_sorted if ev.get("start_at") < now_iso][-2:]
        next_events = [ev for ev in events_sorted if ev.get("start_at") >= now_iso][:3]
        
        embed = discord.Embed(title=f"📅 Course Sessions: {course_name}", color=discord.Color.teal())
        
        if not prev_events and not next_events:
            embed.description = "No recent or upcoming sessions found for this course (+/- 30-60 days)."
            await interaction.followup.send(embed=embed)
            return
            
        for ev in prev_events:
            embed.add_field(name=f"⏪ Previous: {ev.get('title', 'Untitled')}", value=format_event_inline(ev), inline=False)
                
        for ev in next_events:
            embed.add_field(name=f"⏩ Next: {ev.get('title', 'Untitled')}", value=format_event_inline(ev), inline=False)
                
        await interaction.followup.send(embed=embed)

class CustomDateModal(Modal, title='Enter Custom Date'):
    day = TextInput(label='Day (e.g., 15)', placeholder='15', min_length=1, max_length=2)
    month = TextInput(label='Month (e.g., 04 for April)', placeholder='04', min_length=1, max_length=2)

    def __init__(self, user):
        super().__init__()
        self.user = user

    async def on_submit(self, interaction: discord.Interaction):
        try:
            day = int(self.day.value)
            month = int(self.month.value)
            year = 2026 # Default year requested by user

            target_date = datetime.date(year, month, day)
        except ValueError:
            await interaction.response.send_message("❌ Invalid date entered. Make sure it's a real day & month.", ephemeral=True)
            return

        await process_calendar_selection(interaction, self.user, target_date)


class CalendarView(View):
    def __init__(self, user, courses):
        super().__init__(timeout=None)
        self.user = user
        self.courses = courses
        
        options = [
            discord.SelectOption(label="3 Days Before", value="-3", emoji="⏪"),
            discord.SelectOption(label="2 Days Before", value="-2", emoji="◀️"),
            discord.SelectOption(label="Yesterday", value="-1", emoji="⬅️"),
            discord.SelectOption(label="Today", value="0", emoji="📅"),
            discord.SelectOption(label="Tomorrow", value="1", emoji="➡️"),
            discord.SelectOption(label="2 Days After", value="2", emoji="▶️"),
            discord.SelectOption(label="3 Days After", value="3", emoji="⏩"),
        ]
        
        self.select_menu = Select(placeholder="Quick Access...", options=options, custom_id="quick_access_cal")
        self.select_menu.callback = self.quick_access_callback
        self.add_item(self.select_menu)
        
        if courses:
            self.add_item(CalendarCourseSelect(courses, user))

    async def quick_access_callback(self, interaction: discord.Interaction):
        offset = int(self.select_menu.values[0])
        target_date = datetime.date.today() + datetime.timedelta(days=offset)
        
        await process_calendar_selection(interaction, self.user, target_date)

    @discord.ui.button(label="Custom Date", style=discord.ButtonStyle.primary, emoji="🗓️")
    async def custom_date_btn(self, interaction: discord.Interaction, button: Button):
        modal = CustomDateModal(self.user)
        await interaction.response.send_modal(modal)


async def process_calendar_selection(interaction, user, target_date):
    if not interaction.response.is_done():
        await interaction.response.defer()
        follow_up = True
    else:
        follow_up = False

    start_date_str = target_date.strftime("%Y-%m-%dT00:00:00Z")
    end_date_str = target_date.strftime("%Y-%m-%dT23:59:59Z")
    
    events = []
    
    courses = await get_active_courses(user["base_url"], user["token"])
    if courses:
        context_codes = [f"course_{c['id']}" for c in courses]
        events = await get_calendar_events(user["base_url"], user["token"], start_date_str, end_date_str, context_codes)
    
    events.sort(key=lambda x: x.get("start_at") or "")
    
    date_str = target_date.strftime("%B %d, %Y")
    embed = format_events_embed(events, date_str)
    
    if follow_up:
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(embed=embed)


class CalendarCmd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["cal", "events", "schedule"])
    async def calendar(self, ctx):
        """
        View events and assignments from your Canvas Calendar!
        You'll be able to select Quick Dates, Custom Date, or View Upcoming Course Sessions.
        """
        user = get_user(ctx.author.id)
        if not user:
            await ctx.send("❌ You haven't set your Canvas API token yet! Use `!settoken <your_token>` in my DMs first.")
            return

        # Fetch courses right before showing the UI to populate the Course list.
        # This will delay the interaction box briefly, but makes the GUI much more useful
        msg = await ctx.send("📅 **Fetching your courses...**")
        courses = await get_active_courses(user["base_url"], user["token"])

        view = CalendarView(user, courses)
        await msg.edit(content="📅 **Select a date or course to view your Canvas Calendar Events:**", view=view)

async def setup(bot):
    await bot.add_cog(CalendarCmd(bot))
