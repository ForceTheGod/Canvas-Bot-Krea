"""
Gamification commands cog - /profile, /leaderboard, /shop, /balance, /howtoearn, /workload
Commands work with both ! prefix and / slash syntax
"""

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View, Button
from typing import Optional
from utils import gamification_db, earning_logic
from utils.canvas_api import get_active_courses, get_canvas_data
import asyncio


class ShopPurchaseView(View):
    """Shop purchase selection dropdown UI"""
    def __init__(self, user_id, shop_items, bot):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.shop_items = shop_items
        self.bot = bot
        
        # Create select dropdown with all shop items
        options = []
        for item_id, item in shop_items.items():
            label = f"{item['name']} - {int(item['cost'])} CC"
            description = item.get('description', '')[:100]
            options.append(discord.SelectOption(
                label=label,
                value=item_id,
                description=description,
                emoji=self._get_emoji(item.get('type'))
            ))
        
        # Create the select
        self.item_select = Select(
            placeholder="Choose an item to purchase...",
            min_values=1,
            max_values=1,
            options=options[:25]  # Discord limit: max 25 options per select
        )
        self.item_select.callback = self.purchase_item
        self.add_item(self.item_select)
    
    def _get_emoji(self, item_type):
        """Get emoji based on item type"""
        emojis = {
            "feature": "⚙️",
            "role": "🎭",
            "visualization": "📊"
        }
        return emojis.get(item_type, "🛍️")
    
    async def purchase_item(self, interaction: discord.Interaction):
        """Handle item purchase"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't use this menu!", ephemeral=True)
            return
        
        item_id = self.item_select.values[0]
        shop_item = self.shop_items.get(item_id)
        
        if not shop_item:
            await interaction.response.send_message("Item not found!", ephemeral=True)
            return
        
        user = gamification_db.get_user(interaction.user.id)
        cost = int(shop_item.get("cost", 0))
        user_cc = user.get("cc_balance", 0)
        
        if user_cc < cost:
            embed = discord.Embed(
                title="❌ Insufficient CC",
                description=f"You need **{cost}** CC but only have **{user_cc}** CC.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Process purchase
        gamification_db.update_user_cc(interaction.user.id, -cost)
        gamification_db.record_purchase(interaction.user.id, item_id, cost)
        
        # Handle different item types
        item_type = shop_item.get("type")
        
        if item_type == "feature":
            duration = shop_item.get("duration_hours", 24)
            gamification_db.add_active_feature(interaction.user.id, item_id, duration)
            embed = discord.Embed(
                title="✅ Purchase Successful!",
                description=f"You purchased **{shop_item['name']}** for **{cost}** CC!\n\n⏱️ Active for {duration} hours.",
                color=discord.Color.green()
            )
        elif item_type == "role":
            duration = shop_item.get("duration_hours", 168)
            gamification_db.add_active_feature(interaction.user.id, item_id, duration)
            
            # Try to assign role
            guild = interaction.guild
            if guild:
                try:
                    role_name = shop_item["name"]
                    role = discord.utils.get(guild.roles, name=role_name)
                    if not role:
                        role = await guild.create_role(name=role_name, color=discord.Color.gold())
                    await interaction.user.add_roles(role)
                except Exception as e:
                    print(f"Could not assign role: {e}")
            
            embed = discord.Embed(
                title="✅ Purchase Successful!",
                description=f"You purchased **{shop_item['name']}** for **{cost}** CC!\n\n⏱️ Role active for {duration} hours.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="✅ Purchase Successful!",
                description=f"You purchased **{shop_item['name']}** for **{cost}** CC!",
                color=discord.Color.green()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        # Disable the select after purchase
        self.item_select.disabled = True
        await interaction.message.edit(view=self)


class GamificationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="profile", description="View your profile with level, XP, and CC balance")
    async def profile(self, ctx):
        """Display user profile with gamification stats."""
        await ctx.defer(ephemeral=True)
        
        user = gamification_db.get_user(ctx.author.id)
        if not user:
            embed = discord.Embed(
                title="❌ Profile Not Found",
                description="You need to register first! Use `/setup` to link your Canvas account.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # Calculate current level
        level = earning_logic.LevelCalculator.get_level_from_xp(user.get("total_xp", 0))
        current_xp = user.get("total_xp", 0)
        xp_to_next = earning_logic.LevelCalculator.get_xp_to_next_level(current_xp)
        progress = earning_logic.LevelCalculator.get_progress_to_next_level(current_xp)
        
        # Create XP progress bar
        bar_length = 20
        filled = int(bar_length * progress)
        xp_bar = "█" * filled + "░" * (bar_length - filled)
        
        embed = discord.Embed(
            title=f"📊 {ctx.author.name}'s Profile",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="⭐ Level",
            value=f"**{level}**",
            inline=True
        )
        
        embed.add_field(
            name="💰 Canvas Credits",
            value=f"**{user.get('cc_balance', 0)}** CC",
            inline=True
        )
        
        embed.add_field(
            name="📈 Total XP",
            value=f"**{current_xp}** XP",
            inline=True
        )
        
        embed.add_field(
            name="🎯 XP Progress",
            value=f"{xp_bar}\n{current_xp - (level - 1) * 100}/{100} XP to level {level + 1}",
            inline=False
        )
        
        # Active features
        active_features = user.get("active_features", {})
        if active_features:
            features_list = []
            for feature in active_features:
                features_list.append(f"• {feature.replace('_', ' ').title()}")
            embed.add_field(
                name="🎁 Active Features",
                value="\n".join(features_list),
                inline=False
            )
        
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_footer(text=f"Joined: {user.get('created_at', 'Unknown')[:10]}")
        
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="leaderboard", description="View top 10 users by XP")
    async def leaderboard(self, ctx):
        """Display top 10 users ranked by XP."""
        await ctx.defer()
        
        top_users = gamification_db.get_top_users(limit=10)
        
        if not top_users:
            embed = discord.Embed(
                title="📊 Leaderboard",
                description="No users registered yet!",
                color=discord.Color.greyple()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🏆 Top 10 Studious Players",
            color=discord.Color.gold()
        )
        
        leaderboard_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for i, user in enumerate(top_users, 1):
            medal = medals[i - 1] if i <= 3 else f"{i}."
            level = earning_logic.LevelCalculator.get_level_from_xp(user.get("total_xp", 0))
            cc = user.get("cc_balance", 0)
            xp = user.get("total_xp", 0)
            
            try:
                discord_user = await self.bot.fetch_user(int(user.get("discord_id", 0)))
                username = discord_user.name
            except:
                username = f"User {user.get('discord_id', 'Unknown')}"
            
            leaderboard_text += f"{medal} **{username}** - Lvl {level} | {xp} XP | {cc} CC\n"
        
        embed.description = leaderboard_text
        embed.set_footer(text="Updated live!")
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="balance", description="Check your CC and XP balance")
    async def balance(self, ctx):
        """Display user's CC and XP balance."""
        await ctx.defer(ephemeral=True)
        
        user = gamification_db.get_user(ctx.author.id)
        if not user:
            embed = discord.Embed(
                title="❌ Not Registered",
                description="Use `/setup` to link your Canvas account first.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        level = earning_logic.LevelCalculator.get_level_from_xp(user.get("total_xp", 0))
        
        embed = discord.Embed(
            title="💼 Your Balance",
            color=discord.Color.blurple()
        )
        
        embed.add_field(name="💰 Canvas Credits", value=f"**{user.get('cc_balance', 0)}** CC", inline=False)
        embed.add_field(name="⭐ Current Level", value=f"**{level}**", inline=False)
        embed.add_field(name="📊 Total XP", value=f"**{user.get('total_xp', 0)}** XP", inline=False)
        
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="howtoearn", description="Learn how to earn CC and XP")
    async def howtoearn(self, ctx):
        """Display earning guide."""
        await ctx.defer()
        
        embed = discord.Embed(
            title="💎 How to Earn Canvas Credits & XP",
            description="Here's your ultimate guide to grinding and leveling up!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📝 Submission Bonus",
            value="**+50 CC** | Submit any assignment",
            inline=False
        )
        
        embed.add_field(
            name="⚡ Speedrun Multiplier",
            value="**+50% at 12h before due** | **2x CC at 24h before due** | **3x CC at 36h before due**\n*Submit assignments early for huge rewards!*",
            inline=False
        )
        
        embed.add_field(
            name="🎯 Academic Weapon Bonus",
            value="**+100 CC & +200 XP** when you get a grade 90% or higher",
            inline=False
        )
        
        embed.add_field(
            name="🩸 First Blood Bounty",
            value="**+75 CC** if you're the first in the database to submit an assignment",
            inline=False
        )
        
        embed.add_field(
            name="🎖️ Starting Bonus",
            value="Get CC and XP based on your total grades when you register",
            inline=False
        )
        
        embed.add_field(
            name="📈 Level Up",
            value="Earn **100 XP per level**. Higher levels unlock achievements!",
            inline=False
        )
        
        embed.add_field(
            name="💡 Pro Tips",
            value="• Submit early for speedrun multipliers\n• Maintain high grades for Academic Weapon bonuses\n• Check `/workload` to see potential CC values\n• Use shop to enhance your grind",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="workload", description="View upcoming assignments and potential rewards")
    async def workload(self, ctx):
        """Display upcoming assignments with potential CC values."""
        await ctx.defer(ephemeral=True)
        
        user = gamification_db.get_user(ctx.author.id)
        if not user:
            embed = discord.Embed(
                title="❌ Not Registered",
                description="Use `/setup` to link your Canvas account first.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        token = gamification_db.get_decrypted_token(ctx.author.id)
        if not token:
            embed = discord.Embed(
                title="❌ Token Error",
                description="Could not decrypt your Canvas token.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        try:
            base_url = user.get("base_url")
            courses = await get_active_courses(base_url, token)
            
            if not courses:
                embed = discord.Embed(
                    title="📚 Your Workload",
                    description="No active courses found.",
                    color=discord.Color.greyple()
                )
                await ctx.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📚 Your Workload",
                description="Upcoming assignments and their potential rewards",
                color=discord.Color.blue()
            )
            
            # This would need to fetch assignments from each course
            # For now, show a summary
            embed.add_field(
                name="Courses",
                value=f"You have {len(courses)} active course(s). Assignment data coming soon!",
                inline=False
            )
            
            await ctx.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Could not fetch workload: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="shop", description="Browse and purchase items from the shop")
    async def shop(self, ctx):
        """Display shop interface with purchase buttons."""
        await ctx.defer(ephemeral=True)
        
        user = gamification_db.get_user(ctx.author.id)
        if not user:
            embed = discord.Embed(
                title="❌ Not Registered",
                description="Use `/setup` to link your Canvas account first.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🛍️ Gamification Shop",
            description=f"Your Balance: **{user.get('cc_balance', 0)}** CC",
            color=discord.Color.purple()
        )
        
        shop_items = gamification_db.get_all_shop_items()
        
        # Separate by category
        features = {k: v for k, v in shop_items.items() if v.get("type") == "feature"}
        roles = {k: v for k, v in shop_items.items() if v.get("type") == "role"}
        visualizations = {k: v for k, v in shop_items.items() if v.get("type") == "visualization"}
        
        # Add fields for each category
        if features:
            features_text = "\n".join([f"• **{v['name']}** - {int(v['cost'])} CC\n  *{v['description']}*" for v in features.values()])
            embed.add_field(name="⚙️ Features", value=features_text, inline=False)
        
        if roles:
            roles_text = "\n".join([f"• **{v['name']}** - {int(v['cost'])} CC\n  *{v['description']}*" for v in roles.values()])
            embed.add_field(name="🎭 Cosmetics", value=roles_text, inline=False)
        
        if visualizations:
            viz_text = "\n".join([f"• **{v['name']}** - {int(v['cost'])} CC" for v in visualizations.values()])
            embed.add_field(name="📊 Visualizations", value=viz_text, inline=False)
        
        # Create a view with shop items
        view = ShopPurchaseView(ctx.author.id, shop_items, self.bot)
        embed.set_footer(text="Use the dropdown below to purchase items")
        
        await ctx.send(embed=embed, view=view, ephemeral=True)

    @commands.hybrid_command(name="buy", aliases=["shop-buy"], description="Purchase an item from the shop")
    async def buy(self, ctx):
        """Open the shop purchase interface with dropdown selection."""
        await ctx.defer(ephemeral=True)
        
        user = gamification_db.get_user(ctx.author.id)
        if not user:
            embed = discord.Embed(
                title="❌ Not Registered",
                description="Use `/setup` to link your Canvas account first.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        shop_items = gamification_db.get_all_shop_items()
        if not shop_items:
            embed = discord.Embed(
                title="❌ Shop Empty",
                description="No items available in the shop.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🛒 Purchase Item",
            description=f"Your Balance: **{user.get('cc_balance', 0)}** CC\n\nSelect an item from the dropdown below:",
            color=discord.Color.purple()
        )
        
        view = ShopPurchaseView(ctx.author.id, shop_items, self.bot)
        await ctx.send(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(GamificationCommands(bot))
