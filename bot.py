import discord
from discord.ext import commands, tasks
import sqlite3
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_USER_ID = int(os.getenv("TARGET_USER_ID"))
ANNOUNCE_CHANNEL_ID = int(os.getenv("ANNOUNCE_CHANNEL_ID"))
DAILY_ANNOUNCE_HOUR = 9  # 9am UTC / 10am BST

# ── Database ──────────────────────────────────────────────────────
conn = sqlite3.connect("awol.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS last_seen (
        user_id INTEGER PRIMARY KEY,
        timestamp TEXT NOT NULL
    )
""")
conn.commit()

def get_last_seen() -> datetime | None:
    cursor.execute("SELECT timestamp FROM last_seen WHERE user_id = ?", (TARGET_USER_ID,))
    row = cursor.fetchone()
    if row:
        return datetime.fromisoformat(row[0])
    return None

def update_last_seen(dt: datetime):
    cursor.execute(
        "INSERT OR REPLACE INTO last_seen (user_id, timestamp) VALUES (?, ?)",
        (TARGET_USER_ID, dt.isoformat())
    )
    conn.commit()

def days_since(dt: datetime) -> int:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).days

def gay_meter(days: int):
    max_days = 30
    filled = min(days, max_days)
    total_bars = 20
    fill_count = round((filled / max_days) * total_bars)
    empty_count = total_bars - fill_count
    bar = "🌈" * fill_count + "⬜" * empty_count
    percent = min(round((filled / max_days) * 100), 100)

    if days == 0:
        label = "Practically straight rn, how BORING 😒"
    elif days < 3:
        label = "Mildly fruity, just a hint of gay 🍑"
    elif days < 7:
        label = "Getting gayer by the DAY, hunty 💅"
    elif days < 14:
        label = "Full twink energy, serving nothing but ABSENCE 👑"
    elif days < 21:
        label = "Somewhere in Mykonos probably, the NERVE 🏖️🏳️‍🌈"
    elif days < 30:
        label = "Legally a gay icon at this point, we stan a ghost 💀✨"
    else:
        label = "MAXIMUM GAY 🌈🌈🌈 He has ASCENDED. Gone FOREVER. We're DECEASED."

    return bar, percent, label

# ── Bot setup ─────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.author.id == TARGET_USER_ID:
        update_last_seen(datetime.now(timezone.utc))
    await bot.process_commands(message)

@bot.command(name="awol")
async def awol(ctx: commands.Context):
    last_seen = get_last_seen()
    if last_seen is None:
        await ctx.send(
            "Hunty, I have NEVER seen this man type a single word 🌈💀 "
            "He might not even exist! Or he's so gay he's transcended Discord entirely, "
            "which honestly? ICONIC. 👑🏳️‍🌈"
        )
        return

    days = days_since(last_seen)
    bar, percent, label = gay_meter(days)
    formatted = last_seen.strftime("%d/%m/%Y at %H:%M GMT")

    if days == 0:
        intro = "OH HONEY, he actually SHOWED UP today?! Mark the calendars! 📅✨"
    elif days < 3:
        intro = "Babes, he's only been gone a couple of days but the GAY METER doesn't lie 💅"
    elif days < 7:
        intro = "Sweetie, it's been a WEEK. The audacity. The NERVE. 😤🏳️‍🌈"
    elif days < 14:
        intro = "Oh no no no, TWO WEEKS?! He said 'bye bestie' and meant it 💀"
    elif days < 30:
        intro = "SCREAMING. CRYING. He has LEFT the chat and the BUILDING. 🚨🌈"
    else:
        intro = "A WHOLE MONTH?! He is GONE gone. We are in our grieving era. 😭🏳️‍🌈✨"

    msg = (
        f"🏳️‍🌈🏳️‍🌈 **SCAR AWOL TRACKER - PRIDE EDITION** 🏳️‍🌈🏳️‍🌈\n\n"
        f"{intro}\n\n"
        f"Last seen: **{formatted}**\n"
        f"Days missing: **{days}** 💀\n\n"
        f"✨ **Gay Meter** [{percent}%] ✨\n"
        f"{bar}\n"
        f"_{label}_"
    )
    await ctx.send(msg)

@bot.command(name="awol_set")
@commands.has_permissions(administrator=True)
async def awol_set(ctx: commands.Context, date_str: str):
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y").replace(tzinfo=timezone.utc)
        update_last_seen(dt)
        await ctx.send(
            f"Okay BESTIE, last seen set to {date_str} 📅✨ "
            f"The gay meter is initialised and we are READY to track this disappearing act. 🌈💅"
        )
    except ValueError:
        await ctx.send("Hunty that date format is NOT it 😩 Use DD/MM/YYYY — e.g. `!awol_set 01/03/2026`")

@tasks.loop(hours=24)
async def daily_check():
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if channel is None:
        return
    last_seen = get_last_seen()
    if last_seen is None:
        return
    days = days_since(last_seen)
    if days >= 3:
        bar, percent, label = gay_meter(days)
        await channel.send(
            f"☀️🌈 Good morning BESTIES! Daily AWOL update for day **{days}** ✨\n\n"
            f"✨ **Gay Meter** [{percent}%] ✨\n{bar}\n_{label}_\n\n"
            f"Still no sign of him. We're in our waiting era. 💀🏳️‍🌈"
        )

@daily_check.before_loop
async def before_daily():
    await bot.wait_until_ready()
    now = datetime.now(timezone.utc)
    target = now.replace(hour=DAILY_ANNOUNCE_HOUR, minute=0, second=0, microsecond=0)
    if target < now:
        target += timedelta(days=1)
    await discord.utils.sleep_until(target)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    daily_check.start()

bot.run(TOKEN)
