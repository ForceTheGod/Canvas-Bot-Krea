"""
Visualization commands cog - Generate various charts and analyses with button-based UI
"""

import discord
from discord.ext import commands
from discord import app_commands
import io
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from sklearn.linear_model import LinearRegression
import seaborn as sns
from utils import gamification_db
from utils.canvas_api import get_active_courses, get_course_grades
import asyncio

plt.style.use('seaborn-v0_8-darkgrid')


class VisualizationButtons(discord.ui.View):
    """Button view for visualization selection."""
    
    def __init__(self, user_id: int, courses: list, token: str, base_url: str):
        super().__init__()
        self.user_id = user_id
        self.courses = courses
        self.token = token
        self.base_url = base_url
        self.user = gamification_db.get_user(user_id)
    
    @discord.ui.button(label="📊 Histogram (3 CC)", style=discord.ButtonStyle.primary)
    async def histogram_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.generate_visualization(interaction, "histogram", 3)
    
    @discord.ui.button(label="📈 Bar Graph (5 CC)", style=discord.ButtonStyle.primary)
    async def bar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.generate_visualization(interaction, "bar", 5)
    
    @discord.ui.button(label="📦 Box Plot (7.5 CC)", style=discord.ButtonStyle.primary)
    async def box_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.generate_visualization(interaction, "box", 7.5)
    
    @discord.ui.button(label="• Scatter Plot (12 CC)", style=discord.ButtonStyle.danger)
    async def scatter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.generate_visualization(interaction, "scatter", 12)
    
    @discord.ui.button(label="📉 Regression (15 CC)", style=discord.ButtonStyle.success)
    async def regression_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.generate_visualization(interaction, "regression", 15)
    
    @discord.ui.button(label="🔗 Heatmap (10 CC)", style=discord.ButtonStyle.success)
    async def heatmap_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.generate_visualization(interaction, "heatmap", 10)
    
    async def generate_visualization(self, interaction: discord.Interaction, viz_type: str, cost: int):
        """Generate and send visualization."""
        await interaction.response.defer(ephemeral=True)
        
        # Check balance
        if self.user.get("cc_balance", 0) < cost:
            embed = discord.Embed(
                title="❌ Insufficient CC",
                description=f"You need {cost} CC but only have {self.user.get('cc_balance', 0)} CC.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        try:
            # Generate visualization
            img_buffer = await self.create_chart(viz_type)
            
            if img_buffer is None:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Could not generate chart. Make sure you have grade data available.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Deduct CC
            gamification_db.update_user_cc(interaction.user.id, -cost)
            gamification_db.record_purchase(interaction.user.id, f"visualization_{viz_type}", cost)
            
            # Send chart
            img_buffer.seek(0)
            file = discord.File(img_buffer, filename=f"{viz_type}_{datetime.now().timestamp()}.png")
            
            embed = discord.Embed(
                title=f"📊 {viz_type.title()} Analysis",
                description=f"*Cost: {cost} CC*\n\nYour grade performance visualization.",
                color=discord.Color.blue()
            )
            embed.set_image(url=f"attachment://{file.filename}")
            
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Could not generate visualization: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def create_chart(self, chart_type: str) -> io.BytesIO:
        """Create a chart based on type."""
        try:
            # Fetch grades data - this is simplified, in production would need real data
            grades_data = await self._fetch_grades_data()
            
            if not grades_data or len(grades_data) == 0:
                return None
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            if chart_type == "histogram":
                ax.hist(grades_data, bins=10, color='skyblue', edgecolor='black', alpha=0.7)
                ax.set_xlabel("Grade (%)")
                ax.set_ylabel("Frequency")
                ax.set_title("Distribution of Your Grades")
            
            elif chart_type == "bar":
                courses = list(range(len(grades_data)))
                ax.bar(courses, grades_data, color='coral', alpha=0.7)
                ax.set_xlabel("Assignment #")
                ax.set_ylabel("Grade (%)")
                ax.set_title("Your Grades Across Assignments")
            
            elif chart_type == "box":
                ax.boxplot(grades_data, vert=True)
                ax.set_ylabel("Grade (%)")
                ax.set_title("Grade Distribution Box Plot")
            
            elif chart_type == "scatter":
                x = np.arange(len(grades_data))
                ax.scatter(x, grades_data, s=100, alpha=0.6, color='green')
                ax.plot(x, grades_data, alpha=0.3)
                ax.set_xlabel("Assignment #")
                ax.set_ylabel("Grade (%)")
                ax.set_title("Grade Progression Over Time")
            
            elif chart_type == "regression":
                x = np.arange(len(grades_data)).reshape(-1, 1)
                y = np.array(grades_data)
                
                model = LinearRegression()
                model.fit(x, y)
                y_pred = model.predict(x)
                
                ax.scatter(x, y, alpha=0.6, label='Actual Grades', color='blue')
                ax.plot(x, y_pred, color='red', linewidth=2, label='Trend Line')
                ax.set_xlabel("Assignment #")
                ax.set_ylabel("Grade (%)")
                ax.set_title("Grade Trend Analysis")
                ax.legend()
            
            elif chart_type == "heatmap":
                # Create correlation matrix from mock data
                data = pd.DataFrame({
                    'Grade': grades_data[:10],
                    'Days_Early': np.random.randint(1, 30, 10),
                    'Assignments_Submitted': np.random.randint(1, 10, 10)
                })
                
                corr_matrix = data.corr()
                sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', 
                           center=0, ax=ax, cbar_kws={'label': 'Correlation'})
                ax.set_title("Correlation: Grades, Submission Speed, Completion Rate")
            
            plt.tight_layout()
            
            # Save to bytes buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            plt.close(fig)
            
            return buffer
        
        except Exception as e:
            print(f"Error creating chart: {e}")
            return None
    
    async def _fetch_grades_data(self) -> list:
        """Fetch grades data for visualization."""
        try:
            # Simplified mock data for now - would need to fetch real data from Canvas
            # In production, would iterate through courses and get submissions
            grades = [85, 90, 78, 92, 88, 95, 87, 91, 89, 84]
            return grades
        except Exception as e:
            print(f"Error fetching grades: {e}")
            return []


class VisualizationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="analyze", description="Generate grade visualizations and analyses")
    async def analyze(self, interaction: discord.Interaction):
        """Open visualization menu."""
        await interaction.response.defer(ephemeral=True)
        
        user = gamification_db.get_user(interaction.user.id)
        if not user:
            embed = discord.Embed(
                title="❌ Not Registered",
                description="Use `/setup` to link your Canvas account first.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        token = gamification_db.get_decrypted_token(interaction.user.id)
        if not token:
            embed = discord.Embed(
                title="❌ Token Error",
                description="Could not decrypt your Canvas token.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        try:
            base_url = user.get("base_url")
            courses = await get_active_courses(base_url, token)
            
            if not courses:
                embed = discord.Embed(
                    title="❌ No Courses",
                    description="No active courses found.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📊 Grade Analytics",
                description=f"Your Balance: **{user.get('cc_balance', 0)}** CC\n\nSelect a visualization type:",
                color=discord.Color.blurple()
            )
            
            embed.add_field(
                name="💎 Premium Visualizations",
                value="**Histogram** (3 CC) - Grade distribution\n**Bar Graph** (5 CC) - Compare assignments\n**Box Plot** (7.5 CC) - Statistical distribution\n**Scatter Plot** (120 CC) - Trends over time",
                inline=False
            )
            
            embed.add_field(
                name="🔬 Analysis Tools",
                value="**Regression** (15 CC) - Predict future grades\n**Heatmap** (10 CC) - Correlations between metrics",
                inline=False
            )
            
            view = VisualizationButtons(interaction.user.id, courses, token, base_url)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Could not load courses: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(VisualizationCog(bot))
