import discord
from discord.ext import commands
from discord.ui import View, Select
from utils.canvas_api import get_active_courses, get_announcements, get_course_grades, get_assignments, get_assignment_groups
from utils.helpers import clean_html, build_assignment_map, build_group_map, categorize_with_assignments, trim_text
from utils.database import get_user

class CourseAnnouncementSelect(Select):
    def __init__(self, courses, user):
        self.courses = courses
        self.user = user

        options = [
            discord.SelectOption(
                label=c.get("name", "Unnamed")[:100],
                value=str(c.get("id"))
            )
            for c in courses[:25]
        ]
        if not options:
            options = [discord.SelectOption(label="No courses available", value="none")]

        super().__init__(placeholder="Choose a course...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        course_id = self.values[0]
        if course_id == "none":
            await interaction.response.send_message("No courses available.", ephemeral=True)
            return

        course = next((c for c in self.courses if str(c["id"]) == course_id), None)
        course_name = course.get("name", "Unknown") if course else "Unknown"

        announcements = await get_announcements(self.user["base_url"], self.user["token"], course_id)

        if not announcements:
            await interaction.response.send_message(f"📭 No announcements for **{course_name}**.", ephemeral=True)
            return

        embed = discord.Embed(title=f"📢 {course_name}", color=discord.Color.green())
        
        # Sort announcements to ensure we get the latest
        announcements.sort(key=lambda x: x.get("posted_at", ""), reverse=True)

        for ann in announcements[:3]: # Latest 3 announcements
            title = ann.get("title", "No Title")
            message = clean_html(ann.get("message", ""))[:1000]
            if not message.strip():
                message = "*No text content*"
            embed.add_field(name=title, value=message, inline=False)

        await interaction.response.send_message(embed=embed)


class CourseGradeSelect(Select):
    def __init__(self, courses, user):
        self.courses = courses
        self.user = user

        options = [
            discord.SelectOption(
                label=c.get("name", "Unnamed")[:100],
                value=str(c.get("id"))
            )
            for c in courses[:25]
        ]
        if not options:
            options = [discord.SelectOption(label="No courses available", value="none")]

        super().__init__(placeholder="Choose a course...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        course_id = self.values[0]
        if course_id == "none":
            await interaction.followup.send("No courses available.", ephemeral=True)
            return

        course = next((c for c in self.courses if str(c["id"]) == course_id), None)
        course_name = course.get("name", "Unknown") if course else "Unknown"

        submissions = await get_course_grades(self.user["base_url"], self.user["token"], course_id)
        if not submissions:
            await interaction.followup.send(f"❌ No grade data for **{course_name}**.", ephemeral=True)
            return
        
        assignments = await get_assignments(self.user["base_url"], self.user["token"], course_id)
        groups = await get_assignment_groups(self.user["base_url"], self.user["token"], course_id)

        assignment_map = build_assignment_map(assignments)
        group_map = build_group_map(groups)

        categorized = categorize_with_assignments(submissions, assignment_map, group_map)

        scores = [s.get("score") for s in submissions if s.get("score") is not None]
        avg = round(sum(scores) / len(scores), 2) if scores else 0

        embed = discord.Embed(
            title=f"📊 {course_name}",
            description=f"**Overall Attempted Score Avg:** `{avg}`\n(Note: This is an average of assignment scores, not the final Canvas grade)",
            color=discord.Color.blue()
        )

        for category, items in categorized.items():
            if items:
                text = trim_text(items)
                if not text.strip():
                    text = "*Empty*"
                embed.add_field(name=category, value=text, inline=False)

        await interaction.followup.send(embed=embed)


class Courses(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _check_user(self, ctx):
        user = get_user(ctx.author.id)
        if not user:
            await ctx.send("❌ You haven't set your Canvas API token yet! Use `!settoken <your_token> [optional_base_url]` in my DMs first.")
            return None
        return user

    @commands.hybrid_command(aliases=["announcements"])
    async def announcement(self, ctx):
        """
        View the latest 3 announcements for a specific course!
        You will be prompted to select a course from a dropdown menu.
        """
        user = await self._check_user(ctx)
        if not user: return

        courses = await get_active_courses(user["base_url"], user["token"])
        if not courses:
            await ctx.send("❌ No active courses found.")
            return

        view = View()
        view.add_item(CourseAnnouncementSelect(courses, user))

        await ctx.send("📚 **Select a course to view announcements:**", view=view)

    @commands.hybrid_command(aliases=["details", "grades_details"])
    async def grade_details(self, ctx):
        """
        Select a course to view detailed grades by assignment categories!
        This will break down your scores by groups (like Homework, Exams, etc).
        """
        user = await self._check_user(ctx)
        if not user: return

        courses = await get_active_courses(user["base_url"], user["token"])
        if not courses:
            await ctx.send("❌ No active courses found.")
            return

        view = View()
        view.add_item(CourseGradeSelect(courses, user))

        await ctx.send("📊 **Select a course to view detailed grades:**", view=view)

async def setup(bot):
    await bot.add_cog(Courses(bot))
