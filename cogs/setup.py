import discord
from discord.ext import commands
from discord.ui import View, Button
from utils.database import set_user, delete_user, get_user, set_notif_prefs

def build_notif_embed(announce, grades):
    embed = discord.Embed(title="⚙️ Notification Preferences", color=discord.Color.blurple())
    embed.description = ("Control what alerts the bot sends you directly.\n"
                         "*(Background syncing remains active so you never lose track!)*")
    
    ann_str = "✅ **Active**" if announce else "❌ **Disabled**"
    grade_str = "✅ **Active**" if grades else "❌ **Disabled**"
    
    embed.add_field(name="📢 Course Announcements", value=f"Live feed of announcements.\nState: {ann_str}", inline=False)
    embed.add_field(name="🎓 Grade Updates", value=f"Instant alerts when your score posts/changes.\nState: {grade_str}", inline=False)
    return embed

class NotifView(View):
    def __init__(self, user_id, announce_state, grade_state):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.announce_state = announce_state
        self.grade_state = grade_state
        self.update_buttons()
        
    def update_buttons(self):
        self.clear_items()
        
        btn_ann = Button(
            label="Disable Announcements" if self.announce_state else "Enable Announcements", 
            style=discord.ButtonStyle.danger if self.announce_state else discord.ButtonStyle.success,
            emoji="📢"
        )
        btn_grade = Button(
            label="Disable Grade Alerts" if self.grade_state else "Enable Grade Alerts", 
            style=discord.ButtonStyle.danger if self.grade_state else discord.ButtonStyle.success,
            emoji="🎓"
        )
        
        btn_ann.callback = self.toggle_ann
        btn_grade.callback = self.toggle_grades
        
        self.add_item(btn_ann)
        self.add_item(btn_grade)
        
    async def toggle_ann(self, interaction: discord.Interaction):
        self.announce_state = not self.announce_state
        set_notif_prefs(self.user_id, announce=self.announce_state)
        self.update_buttons()
        await self.refresh_ui(interaction)
        
    async def toggle_grades(self, interaction: discord.Interaction):
        self.grade_state = not self.grade_state
        set_notif_prefs(self.user_id, grades=self.grade_state)
        self.update_buttons()
        await self.refresh_ui(interaction)
        
    async def refresh_ui(self, interaction):
        embed = build_notif_embed(self.announce_state, self.grade_state)
        await interaction.response.edit_message(embed=embed, view=self)

def get_token_help_embed():
    embed = discord.Embed(title="🔑 How to Generate a Canvas API Token", color=discord.Color.gold())
    embed.description = "To use this bot, you need an API token from your Canvas account. Follow these steps:"
    embed.add_field(name="Step 1", value="Log in to your Canvas website (e.g., https://canvas.krea.edu.in).", inline=False)
    embed.add_field(name="Step 2", value="Click on **Account** in the global left sidebar menu, then click on **Settings**.", inline=False)
    embed.add_field(name="Step 3", value="Scroll down to the **Approved Integrations** section and click the **+ New Access Token** button.", inline=False)
    embed.add_field(name="Step 4", value="Set the **Purpose** (e.g., 'Discord Bot') and an optional **Expires** date (leave blank for no expiration), then click **Generate Token**.", inline=False)
    embed.add_field(name="Step 5", value="Copy the long token shown on the screen. **IMPORTANT:** This token is like a password. Do not share it publicly!", inline=False)
    embed.add_field(name="Step 6", value="Send me a Direct Message (DM) with the command:\n`!settoken <your_copied_token> [optional custom canvas url]`", inline=False)
    return embed

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["token", "login"])
    async def settoken(self, ctx, token: str = None, base_url: str = "https://canvas.krea.edu.in"):
        """
        Save your canvas API token and url to use the bot.
        Best done in DMs to keep your token safe!
        Example: !settoken my_api_key123 https://canvas.instructure.com
        """
        if not token:
            await ctx.send(embed=get_token_help_embed())
            return
            
        if ctx.guild:
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass
            await ctx.send("I recommend sending me your token in a **Direct Message** to keep it safe! I've deleted your message if I had permissions to do so.", delete_after=10)
        
        set_user(ctx.author.id, token, base_url)
        await ctx.send("✅ Your token has been saved successfully! You can now use the bot commands.")

    @commands.command(aliases=["logout", "remove_token"])
    async def cleartoken(self, ctx):
        """
        Remove your canvas API token from the bot's database.
        Use this if you no longer want the bot to access your Canvas account.
        """
        if delete_user(ctx.author.id):
            await ctx.send("🗑️ Your token has been removed from my database.")
        else:
            await ctx.send("⚠️ You don't have a token saved in my database.")

    @commands.command(aliases=["notifs", "alerts", "ping"])
    async def notifications(self, ctx):
        """
        Interactive dashboard to toggle Annoucement & Grade Background Alerts.
        You can subscribe or unsubscribe whenever you want safely!
        """
        user = get_user(ctx.author.id)
        if not user:
            await ctx.send("❌ You haven't set your Canvas API token yet! Use `!settoken <your_token>` in my DMs first.")
            return
            
        ann_state = user.get("announce_notifs", False)
        grade_state = user.get("grade_notifs", False)

        embed = build_notif_embed(ann_state, grade_state)
        view = NotifView(ctx.author.id, ann_state, grade_state)
        await ctx.send(embed=embed, view=view)

    @commands.command(aliases=["token_help", "howtotoken"])
    async def tokenhelp(self, ctx):
        """
        Get step-by-step instructions on how to generate an API token from Canvas.
        """
        await ctx.send(embed=get_token_help_embed())

async def setup(bot):
    await bot.add_cog(Setup(bot))
