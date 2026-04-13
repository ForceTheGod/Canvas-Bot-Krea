import discord
from discord.ext import commands
from utils.canvas_api import get_canvas_data, get_name
from utils.database import get_user


class Grades(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _check_user(self, ctx):
        user = get_user(ctx.author.id)
        if not user:
            await ctx.send("❌ You haven't set your Canvas API token yet! Use `!settoken <your_token> [optional_base_url]` in my DMs first.")
            return None
        return user

    @commands.hybrid_command(aliases=["grade", "scores"])
    async def grades(self, ctx):
        """
        View your current overall grades across all active courses!
        Fetches the primary score for each course you're enrolled in.
        """
        user = await self._check_user(ctx)
        if not user: return
        
        await ctx.send("Searching the archives... 📊")
        data = await get_canvas_data(user["base_url"], user["token"])
        
        if not data:
            await ctx.send("Couldn't find any active grades. Make sure your token is valid or you have graded courses.")
            return

        msg = "**Your Current Grades:**\n"
        for item in data:
            msg += f"• **{item['Course']}**: `{item['Grade']}%`\n"
        
        await ctx.send(msg)

    @commands.hybrid_command(aliases=["gpa"])
    async def cgpa(self, ctx):
        """
        Calculate an estimated CGPA based on your current Canvas grades!
        Converts your average percentage across courses into a 10-point scale GPA estimate.
        """
        user = await self._check_user(ctx)
        if not user: return

        data = await get_canvas_data(user["base_url"], user["token"])
        
        if not data:
            await ctx.send("No grade data available to calculate CGPA.")
            return

        total_percentage = sum(item['Grade'] for item in data)
        avg_percentage = total_percentage / len(data)
        calculated_cgpa = round(avg_percentage / 10, 2)
        
        embed = discord.Embed(title="Academic Standing", color=discord.Color.blue())
        embed.add_field(name="Average Percentage", value=f"{round(avg_percentage, 2)}%", inline=True)
        embed.add_field(name="Estimated CGPA", value=f"**{calculated_cgpa}** / 10.0", inline=True)
        embed.set_footer(text="Note: This is an automated estimate.")
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["extremes", "extreme"])
    async def maxmin(self, ctx):
        """
        View your highest and lowest graded courses!
        Quickly figure out which courses are carrying your GPA vs dropping it.
        """
        user = await self._check_user(ctx)
        if not user: return

        data = await get_canvas_data(user["base_url"], user["token"])
        usr_name = await get_name(user["base_url"], user["token"])
        
        if not data:
            await ctx.send("No grade data available.")
            return
        
        maximum = max((item['Grade'], item['Course']) for item in data)
        minimum = min((item['Grade'], item['Course']) for item in data)
        spread = round(maximum[0] - minimum[0], 2)

        embed = discord.Embed(
            title="Grade Spread",
            color=discord.Color.red(),
            description="Here's a quick look at your highest and lowest performance."
        )

        embed.add_field(name="Highest 💪", value=f"{maximum[1]}\n`{maximum[0]}`", inline=True)
        embed.add_field(name="Lowest 👎", value=f"{minimum[1]}\n`{minimum[0]}`", inline=True)
        embed.add_field(name="Spread ➖", value=f"`{spread}`", inline=True)
        embed.set_footer(text=f"Fetched from Canvas | {usr_name}")

        await ctx.send(embed=embed)



async def setup(bot):
    await bot.add_cog(Grades(bot))
