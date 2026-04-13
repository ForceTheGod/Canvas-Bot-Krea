import discord
from discord.ext import commands
from discord.ui import View, Select
from utils.canvas_api import get_active_courses, search_course_files, get_course_syllabus
from utils.database import get_user
from utils.helpers import clean_html

class SyllabusSelect(Select):
    def __init__(self, courses, user):
        self.user = user
        options = [
            discord.SelectOption(label=c.get("name", "Unnamed")[:100], value=str(c.get("id")))
            for c in courses[:25]
        ]
        if not options:
            options = [discord.SelectOption(label="No courses available", value="none")]
            
        super().__init__(placeholder="Select Course to view Syllabus...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        course_id = self.values[0]
        if course_id == "none":
            await interaction.followup.send("No courses available.", ephemeral=True)
            return

        course_name = next((c.get("name", "Unknown") for c in self.view.courses if str(c.get("id")) == course_id), "Unknown")
        
        course_data = await get_course_syllabus(self.user["base_url"], self.user["token"], course_id)
        if not course_data:
            await interaction.followup.send(f"❌ Failed to fetch course data for **{course_name}**.", ephemeral=True)
            return
            
        syllabus_body_html = course_data.get("syllabus_body")
        text = clean_html(syllabus_body_html) if syllabus_body_html else ""
        
        # We also want to search for actual syllabus files (e.g. PDF/Docx files)
        syllabus_files = await search_course_files(self.user["base_url"], self.user["token"], course_id, "syllabus")
        
        if not text and not syllabus_files:
            embed = discord.Embed(title=f"📜 Syllabus: {course_name}", color=discord.Color.red())
            embed.description = "No syllabus text or syllabus documents found for this course on Canvas."
            await interaction.followup.send(embed=embed)
            return
            
        embed = discord.Embed(title=f"📜 Syllabus: {course_name}", color=discord.Color.teal())
        
        if text:
            # Limit to discord max embed description
            if len(text) > 4000:
                embed.description = text[:4000] + "\n\n*(Truncated due to length)*"
            else:
                embed.description = text
        else:
            embed.description = "*(No text overview was provided by the professor. See attached files instead:)*"
            
        if syllabus_files:
            files_str = ""
            for f in syllabus_files[:5]: # Max 5 files
                name = f.get("display_name", f.get("filename", "Unnamed File"))
                dl_url = f.get("url")
                size_kb = f.get("size", 0) // 1024
                files_str += f"• **{name}** ({size_kb} KB) - [📥 Download]({dl_url})\n"
                
            embed.add_field(name="📎 Attached Syllabus Files", value=files_str, inline=False)
            
        await interaction.followup.send(embed=embed)


class SyllabusView(View):
    def __init__(self, user, courses):
        super().__init__(timeout=None)
        self.user = user
        self.courses = courses
        if courses:
            self.add_item(SyllabusSelect(courses, user))


class Materials(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(aliases=["syl", "course_summary"])
    async def syllabus(self, ctx):
        """
        Pull the syllabus text / course summary for a specific course.
        Select from an interactive dropdown to instantly fetch up to 4000 chars of syllabus.
        """
        user = get_user(ctx.author.id)
        if not user:
            await ctx.send("❌ You haven't set your Canvas API token yet! Use `!settoken <your_token>` in my DMs first.")
            return

        msg = await ctx.send("📚 **Fetching your active courses...**")
        courses = await get_active_courses(user["base_url"], user["token"])
        
        if not courses:
            await msg.edit(content="❌ No active courses found.")
            return

        view = SyllabusView(user, courses)
        await msg.edit(content="📚 **Select a course to view its Official Syllabus:**", view=view)


    @commands.hybrid_command(aliases=["search", "files"])
    async def find(self, ctx, *, keyword: str = None):
        """
        Search through course files instantaneously!
        Provides a direct download link and file page. Search by name or topic.
        Example: !find midterm study guide
        """
        if not keyword:
            await ctx.send("⚠️ You must provide a keyword to search! Example: `!find lecture slide`")
            return
            
        user = get_user(ctx.author.id)
        if not user:
            await ctx.send("❌ You haven't set your Canvas API token yet! Use `!settoken <your_token>` in my DMs first.")
            return

        msg = await ctx.send(f"🔍 **Searching all active courses for `{keyword}`...** (This may take a moment)")
        
        courses = await get_active_courses(user["base_url"], user["token"])
        if not courses:
            await msg.edit(content="❌ No active courses found to search.")
            return

        all_files = []
        
        for course in courses:
            c_id = course.get("id")
            c_name = course.get("name", "Unknown Course")
            
            # Hit files search API for this course
            files = await search_course_files(user["base_url"], user["token"], c_id, keyword)
            for f in files:
                all_files.append((c_name, f))
                
        if not all_files:
            embed = discord.Embed(
                title="🔍 Search Results", 
                description=f"No files matching `{keyword}` were found across your active courses.", 
                color=discord.Color.light_grey()
            )
            await msg.edit(content=None, embed=embed)
            return

        # Restrict to maximum of 10 matches to avoid discord chunk limit
        all_files = all_files[:10]
        
        embed = discord.Embed(title=f"🔍 Top Search Results for `{keyword}`", color=discord.Color.magenta())
        
        for c_name, f in all_files:
            name = f.get("display_name", f.get("filename", "Unnamed File"))
            dl_url = f.get("url")
            # `html_url` does not always exist, fallback to direct download URL
            canvas_web = f.get("html_url", dl_url)
            
            size_mb = round(f.get("size", 0) / (1024 * 1024), 2)
            
            val = f"**Course:** {c_name}\n**Size:** {size_mb} MB\n[📥 Direct Download]({dl_url}) | [🌐 Canvas File Page]({canvas_web})"
            embed.add_field(name=f"📄 {name}", value=val, inline=False)
            
        embed.set_footer(text="If you didn't find what you need, try a more specific keyword!")
        await msg.edit(content=None, embed=embed)

async def setup(bot):
    await bot.add_cog(Materials(bot))
