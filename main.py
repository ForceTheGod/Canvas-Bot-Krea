import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from utils import gamification_db

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    print("[ERROR] DISCORD_TOKEN not found! Please check your .env file.")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    print(f"Serving {len(bot.guilds)} guild(s)")
    
    # Initialize shop items
    gamification_db.initialize_shop()
    print("Shop initialized")

async def load_cogs():
    """Load all cogs from the cogs directory."""
    cog_files = [
        "setup",
        "gamification",
        "visualizations",
        "gamification_background",
        # Add other cogs here
        "calendar",
        "courses",
        "grades",
        "materials",
        "todo",
        "background_tasks"
    ]
    
    for cog_name in cog_files:
        try:
            await bot.load_extension(f"cogs.{cog_name}")
            print(f"[OK] Loaded cog: {cog_name}")
        except Exception as e:
            print(f"[ERROR] Failed to load cog {cog_name}: {e}")
    
    print("All cogs loaded!")

@bot.event
async def setup_hook():
    await load_cogs()
    try:
        synced = await bot.tree.sync()
        print(f"[OK] Synced {len(synced)} slash commands!")
    except Exception as e:
        print(f"[ERROR] Error syncing commands: {e}")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
