import discord
from discord.ext import commands, tasks
import sqlite3
import os
from datetime import datetime, timezone, timedelta, date
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_USER_ID = int(os.getenv("TARGET_USER_ID"))
ANNOUNCE_CHANNEL_ID = int(os.getenv("ANNOUNCE_CHANNEL_ID"))

DEADLINE = datetime(2026, 5, 1, tzinfo=timezone.utc)
START_DATE = datetime(2026, 3, 31, tzinfo=timezone.utc)  # Day letter was sent
DAILY_REPORT_HOUR = 20  # 8pm UTC / 9pm BST

TOTAL_DAYS = (DEADLINE - START_DATE).days  # ~31 days

# Stages along the Gay -> Trans spectrum
STAGES = [
    (0,   "🏳️‍🌈 Gay",          "Fully gay, just vibing. Still might reply. Maybe."),
    (20,  "💗 Bisexual",       "Getting curious. The silence is giving bi erasure."),
    (40,  "💛 Pansexual",      "Love knows no bounds, apparently including this server."),
    (55,  "🌸 Queer",          "Defying all labels, including 'person who replies to messages'."),
    (70,  "💜 Non-binary",     "Beyond the binary of replying and not replying. They chose not replying."),
    (85,  "⚧️ Questioning",    "We're all questioning at this point. Mainly: where IS he?"),
    (100, "⚧️ Transgender",    "FULLY TRANSITIONED. He is gone. He is someone else now. Farewell."),
]

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

def days_until_deadline() -> int:
    now = datetime.now(timezone.utc)
    remaining = (DEADLINE - now).days
    return max(remaining, 0)

def get_stage(percent: int):
    current = STAGES[0]
    for threshold, name, flavour in STAGES:
        if percent >= threshold:
            current = (threshold, name, flavour)
    return current

def build_meter(last_seen: datetime) -> str:
    now = datetime.now(timezone.utc)
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)

    days_gone = (now - START_DATE).days
    percent = min(round((days_gone / TOTAL_DAYS) * 100), 100)
    days_left = days_until_deadline()

    # Progress bar: GAY -> TRANS, 24 blocks
    filled = round((percent / 100) * 24)
    empty = 24 - filled
    bar = "🟣" * filled + "⬜" * empty

    _, stage_name, stage_flavour = get_stage(percent)
    last_seen_fmt = last_seen.strftime("%d/%m/%Y at %H:%M GMT")

    msg = (
        f"🏳️‍🌈✨ **SCAR IDENTITY CRISIS TRACKER** ✨🏳️‍⚧️\n\n"
        f"📅 Last seen: **{last_seen_fmt}**\n"
        f"⏳ Days since letter sent: **{days_gone}** / {TOTAL_DAYS}\n"
        f"🚨 Days until deadline: **{days_left}**\n\n"
        f"**🏳️‍🌈 GAY** {bar} **TRANS ⚧️**\n"
        f"**[{percent}%] — Currently: {stage_name}**\n"
        f"_{stage_flavour}_\n\n"
    )

    if days_left == 0:
        msg += "💀 **THE DEADLINE HAS PASSED. HE IS FULLY TRANSITIONED. WE ARE DECEASED.** 💀"
    elif percent >= 85:
        msg += f"⚠️ HUNTY the deadline is {days_left} days away and we are in CRISIS. 🌈💀"
    elif percent >= 50:
        msg += f"Girl... {days_left} days left. He needs to MATERIALISE. 👀💅"
    else:
        msg += f"Still {days_left} days until the deadline bestie. No panic. Yet. 🌸"

    return msg

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
        channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
        if channel:
            await channel.send(
                f"🚨🌈 BREAKING NEWS BESTIE! He has APPEARED! 🌈🚨\n"
                f"The gay meter has been RESET. He lives. He typed. We're THRIVING. 💅✨"
            )
    await bot.process_commands(message)

@bot.command(name="awol")
async def awol(ctx: commands.Context):
    last_seen = get_last_seen()
    if last_seen is None:
        await ctx.send(
            "Hunty, I have NEVER seen this man type a single word 💀🌈 "
            "Use `!awol_set DD/MM/YYYY` to set when he was last seen, "
            "or he's just so far along the meter he's already FULLY TRANSITIONED. ⚧️✨"
        )
        return
    await ctx.send(build_meter(last_seen))

@bot.command(name="awol_set")
@commands.has_permissions(administrator=True)
async def awol_set(ctx: commands.Context, date_str: str):
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y").replace(tzinfo=timezone.utc)
        update_last_seen(dt)
        await ctx.send(
            f"Okay BESTIE, last seen locked in as {date_str} 📅✨ "
            f"The identity crisis tracker is PRIMED and ready. 🌈⚧️💅"
        )
    except ValueError:
        await ctx.send("Hunty that format is NOT it 😩 Use DD/MM/YYYY — e.g. `!awol_set 31/03/2026`")

# ── Daily report at 8pm UTC ───────────────────────────────────────
@tasks.loop(hours=24)
async def daily_report():
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if channel is None:
        return
    last_seen = get_last_seen()
    if last_seen is None:
        return
    await channel.send(
        f"🌙✨ **END OF DAY REPORT** ✨🌙\n\n"
        + build_meter(last_seen)
    )

@daily_report.before_loop
async def before_daily():
    await bot.wait_until_ready()
    now = datetime.now(timezone.utc)
    target = now.replace(hour=DAILY_REPORT_HOUR, minute=0, second=0, microsecond=0)
    if target < now:
        target += timedelta(days=1)
    await discord.utils.sleep_until(target)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    daily_report.start()

bot.run(TOKEN)
