import discord
from discord.ext import commands, tasks
import sqlite3
import os
from datetime import datetime, timezone, timedelta
import urllib.request
import json
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_USER_ID = int(os.getenv("TARGET_USER_ID"))
ANNOUNCE_CHANNEL_ID = int(os.getenv("ANNOUNCE_CHANNEL_ID"))

DEADLINE = datetime(2026, 5, 1, tzinfo=timezone.utc)
LETTER_DATE = datetime(2026, 3, 31, tzinfo=timezone.utc)
TOTAL_DAYS = (DEADLINE - LETTER_DATE).days  # 31 days
DAILY_REPORT_HOUR = 20  # 8pm UTC / 9pm BST

PING = f"<@{TARGET_USER_ID}>"

RAINBOW = ["🟥", "🟧", "🟨", "🟩", "🟦", "🟪"]

STAGES = [
    (0,   "🏳️‍🌈 Gay",                  "Fully gay, just vibing. Still might reply. Maybe. 💅"),
    (15,  "💗🟣💙 Bisexual",            "The silence is giving serious bi erasure energy hunty 😤"),
    (30,  "💛🤍💗🖤 Pansexual",         "Love knows no bounds! Apparently including this Discord server 💀"),
    (50,  "🌸🌈 Queer",                 "Defying all labels, INCLUDING 'person who replies to messages' 😩✨"),
    (65,  "💛⬜💜⬛ Non-binary",        "Beyond the binary of replying and not replying. They chose NOT replying 👑"),
    (80,  "⚧️🌸 Questioning",           "We're ALL questioning at this point babes. Mainly: WHERE IS HE?? 🚨"),
    (100, "⚧️🏳️‍⚧️ Fully Transitioned", "TRANSITIONED. He is a NEW PERSON now. Gone forever. We are DECEASED 💀🌈"),
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

def get_stage(percent: int):
    result = STAGES[0]
    for threshold, name, flavour in STAGES:
        if percent >= threshold:
            result = (threshold, name, flavour)
    return result

def build_meter() -> str:
    now = datetime.now(timezone.utc)
    last_seen = get_last_seen()

    # Meter runs from his last seen date to the deadline
    anchor = last_seen if last_seen else LETTER_DATE
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=timezone.utc)
    total_window = max((DEADLINE - anchor).days, 1)
    days_silent = (now - anchor).days
    days_left = max((DEADLINE - now).days, 0)
    days_elapsed = (now - LETTER_DATE).days
    percent = min(round((days_silent / total_window) * 100), 100)

    # Rainbow bar - 24 blocks, colours shift left to right
    total_blocks = 24
    filled = round((percent / 100) * total_blocks)
    bar_blocks = ""
    for i in range(filled):
        colour_index = min(int((i / total_blocks) * len(RAINBOW)), len(RAINBOW) - 1)
        bar_blocks += RAINBOW[colour_index]
    bar_blocks += "⬜" * (total_blocks - filled)

    _, stage_name, stage_flavour = get_stage(percent)
    last_seen_fmt = last_seen.strftime("%d/%m/%Y at %H:%M GMT") if last_seen else "never seen 💀"
    today_fmt = now.strftime("%d/%m/%Y")

    if days_left == 0:
        urgency = f"🚨🚨🚨 **THE DEADLINE HAS PASSED** 🚨🚨🚨\n{PING} HE IS FULLY TRANSITIONED. IT IS OVER. 💀🏳️‍⚧️"
    elif days_left <= 3:
        urgency = f"🔥🔥 {PING} BABES THE DEADLINE IS IN **{days_left} DAYS** THIS IS NOT A DRILL 🔥🔥"
    elif days_left <= 7:
        urgency = f"⚠️ {PING} hunty you have **{days_left} days** left before full transition. JUST REPLY. 😩🌈"
    elif percent >= 50:
        urgency = f"👀 {PING} girl... **{days_left} days** until the deadline. The meter is NOT looking cute. 💅"
    else:
        urgency = f"🌸 {PING} still **{days_left} days** until the deadline. No panic. Yet. 🏳️‍🌈✨"

    msg = (
        f"🏳️‍🌈🏳️‍⚧️💅✨ **SCAR IDENTITY CRISIS TRACKER** ✨💅🏳️‍⚧️🏳️‍🌈\n"
        f"📅 Today: **{today_fmt}** | Deadline: **01/05/2026**\n\n"
        f"👀 Last seen: **{last_seen_fmt}**\n"
        f"💀 Days since last message: **{days_silent}**\n"
        f"⏳ Days since letter sent: **{days_elapsed}** / {TOTAL_DAYS}\n"
        f"🚨 Days until deadline: **{days_left}**\n\n"
        f"🏳️‍🌈 **GAY** ━━━━━━━━━━━━━━━━ **TRANS** ⚧️\n"
        f"{bar_blocks}\n"
        f"**{percent}% transitioned — {stage_name}**\n"
        f"_{stage_flavour}_\n\n"
        f"{urgency}"
    )
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
                f"🚨🌈🚨 **BREAKING NEWS BESTIE** 🚨🌈🚨\n\n"
                f"{PING} HAS APPEARED!! 😱✨\n"
                f"He TYPED. He EXISTS. We are THRIVING. We are HEALED. We are SO back. 🎉🌈🎉"
            )
    await bot.process_commands(message)

@bot.command(name="awol")
async def awol(ctx: commands.Context):
    await ctx.send(build_meter())

@bot.command(name="awol_set")
@commands.has_permissions(administrator=True)
async def awol_set(ctx: commands.Context, date_str: str):
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y").replace(tzinfo=timezone.utc)
        update_last_seen(dt)
        await ctx.send(
            f"Okay BESTIE, {PING}'s last seen is locked in as **{date_str}** 📅✨\n"
            f"The identity crisis tracker is PRIMED. 🌈⚧️💅"
        )
    except ValueError:
        await ctx.send("Hunty that format is NOT it 😩 Use DD/MM/YYYY — e.g. `!awol_set 31/03/2026`")

@tasks.loop(hours=24)
async def daily_report():
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if channel is None:
        return
    await channel.send(
        f"🌙✨💅 **END OF DAY IDENTITY REPORT** 💅✨🌙\n\n"
        + build_meter()
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
