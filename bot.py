import discord
from discord.ext import commands, tasks
import sqlite3
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_USER_ID = int(os.getenv("TARGET_USER_ID"))          # The AWOL mate's Discord user ID
ANNOUNCE_CHANNEL_ID = int(os.getenv("ANNOUNCE_CHANNEL_ID")) # Channel for daily check-ins
DAILY_ANNOUNCE_HOUR = 9  # 9am UTC

# ── Database setup ────────────────────────────────────────────────
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

# ── Bot setup ─────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ── Event: track the target user's messages ───────────────────────
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.author.id == TARGET_USER_ID:
        update_last_seen(datetime.now(timezone.utc))

    await bot.process_commands(message)

# ── Command: !awol ────────────────────────────────────────────────
@bot.command(name="awol")
async def awol(ctx: commands.Context):
    """Check how long the target has been quiet."""
    last_seen = get_last_seen()

    if last_seen is None:
        await ctx.send(
            "I've never seen him say a word. Classic. He might just be a ghost at this point."
        )
        return

    days = days_since(last_seen)
    formatted = last_seen.strftime("%d %b %Y at %H:%M UTC")

    if days == 0:
        msg = f"Actually spoke today (shock). Last seen: {formatted}. Enjoy it while it lasts."
    elif days == 1:
        msg = f"It's been **1 day** since he last spoke. The silence begins. Last seen: {formatted}."
    elif days < 7:
        msg = f"It's been **{days} days** since he last spoke. Still recent enough to be excusable. Last seen: {formatted}."
    elif days < 14:
        msg = f"**{days} days.** He's gone a bit quiet. Someone should probably check the bins. Last seen: {formatted}."
    elif days < 30:
        msg = f"**{days} days** since his last transmission. At this point he owes everyone a written explanation. Last seen: {formatted}."
    else:
        msg = f"**{days} days.** He has transcended this Discord. A legend. A ghost. A cautionary tale. Last seen: {formatted}."

    await ctx.send(msg)

# ── Command: !awol_set ────────────────────────────────────────────
@bot.command(name="awol_set")
@commands.has_permissions(administrator=True)
async def awol_set(ctx: commands.Context, date_str: str):
    """Manually set last seen date. Format: YYYY-MM-DD (admin only)"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        update_last_seen(dt)
        await ctx.send(f"Last seen manually set to {date_str}. The clock is ticking.")
    except ValueError:
        await ctx.send("Bad format. Use YYYY-MM-DD, e.g. `!awol_set 2025-02-01`")

# ── Daily announcement task ───────────────────────────────────────
@tasks.loop(hours=24)
async def daily_check():
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if channel is None:
        return

    last_seen = get_last_seen()
    if last_seen is None:
        return

    days = days_since(last_seen)

    # Only announce if he's been gone a while (no point spamming if he's active)
    if days >= 3:
        await channel.send(
            f"Good morning. Day **{days}** of the AWOL situation. "
            f"Use `!awol` for the full report."
        )

@daily_check.before_loop
async def before_daily():
    await bot.wait_until_ready()
    now = datetime.now(timezone.utc)
    # Calculate seconds until next 9am UTC
    target = now.replace(hour=DAILY_ANNOUNCE_HOUR, minute=0, second=0, microsecond=0)
    if target < now:
        from datetime import timedelta
        target += timedelta(days=1)
    await discord.utils.sleep_until(target)

# ── Ready ─────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    daily_check.start()

bot.run(TOKEN)
