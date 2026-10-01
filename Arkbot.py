import asyncio
import datetime
import io
import json
import os
import random
import re
import signal
import sys
import traceback
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Tuple, Union

import discord
from discord.ext import commands, tasks
from discord.ui import Button, Modal, TextInput, View

# ==============================================================================
# BOT SETUP & INTENTS
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

UPDATE_NOTIFIED = False
MAINTENANCE_MODE = False

STATE_FILE = "bot_runtime_state.json"
XP_DATABASE_FILE = "user_xp.json"
BIRTHDAYS_FILE = "birthdays.json"
CONFESSIONS_FILE = "confessions.json"
MASTER_BACKUP_TEMPLATE = "master_backup_{guild_id}.json"

# In-memory caches & state
AFK_USERS: Dict[int, Dict[str, Any]] = {}
LAST_BUMP_TIME: Optional[datetime.datetime] = None
BUMP_TIMER_TASK: Optional[asyncio.Task] = None
BUMP_LOCK = asyncio.Lock()
BUMP_COOLDOWN_SECONDS = 7200  # 2 Hours
ANNOUNCED_BIRTHDAYS_TODAY: List[int] = []
REMINDED_BIRTHDAYS_TOMORROW: List[int] = []

# Chat Revive State & Cooldowns
LAST_REVIVE_TIME: Dict[int, float] = {}
REVIVE_COOLDOWN_SECONDS = 2700  # 45 Minutes Guild Cooldown

# XP In-Memory Cache
XP_CACHE: Dict[str, int] = {}
XP_CACHE_DIRTY = False

# Super Drop tracking (4 Hours Cooldown)
CHANNEL_CHAT_ACTIVITY: Dict[int, deque] = defaultdict(lambda: deque(maxlen=50))
SUPER_DROP_COOLDOWNS: Dict[int, float] = {}
SUPER_DROP_COOLDOWN_SECONDS = 14400  # 4 Hours

# Message rate tracking
USER_MESSAGE_TIMESTAMPS: Dict[int, deque] = defaultdict(lambda: deque(maxlen=10))
USER_CHAT_XP_COOLDOWN: Dict[int, float] = {}
INVITE_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discord(?:app)?\.com/invite)/[a-zA-Z0-9_-]+",
    re.IGNORECASE,
)

SYSTEM_CHANNELS = {
    "bot-memory",
    "📜・audit-logs",
    "audit-logs",
    "🩸・bot-errors",
    "bot-errors",
    "🧪・bot-testing",
    "bot-testing",
    "📢・discord-news",
    "discord-news",
}

LEVEL_TIERS: List[Tuple[int, str]] = [
    (60, "Sovereign (Levels 60-70)"),
    (50, "Legend (Levels 50-59)"),
    (40, "Champion (Levels 40-49)"),
    (30, "Elite (Levels 30-39)"),
    (20, "Vanguard (Levels 20-29)"),
    (10, "Explorer (Levels 10-19)"),
    (1, "Newbie (Levels 1-9)"),
]

COLOR_ROLES = ["Red", "Yellow", "Green", "Blue", "Orange", "Pink"]

# --- DYNAMIC MESSAGE PRESETS (15 EACH) ---
AFK_PRESET_MESSAGES = [
    "💔 Slipping away into the quiet shadows... see you when the world feels softer.",
    "🌧️ Wandering through quiet echoes and lonely thoughts. Leaving sweet love behind while I'm away.",
    "🥀 Drifting away to let a tired heart rest. Please keep my memories warm until I return.",
    "🌙 Disappearing into the silent twilight... sending tender hugs across the distance.",
    "🍂 Drifting into solitude for a little while. Missing you all already.",
    "🖤 Floating where the silence feels gentler. Be back soon, don't forget me.",
    "✨ Tucking away in my quiet sanctuary with fond thoughts of you all.",
    "🥺 Stepping into the quiet mist to breathe alone for a bit. Catch you later, lovely souls.",
    "🕊️ Seeking peace in quiet solitude. Leaving warm whispers of affection behind.",
    "🌧️ Drifting into silent solitude to heal and recharge. Keep a warm thought for me.",
    "☁️ Lost in the clouds for a bit. Keep the chat warm for me.",
    "🕰️ Stepping out of time for a moment. See you on the other side.",
    "🎧 Lost in the music and away from the keyboard. Be right back.",
    "🌌 Stargazing in my own little world... I'll return when the stars align.",
    "🍃 Gone with the wind. Catch you all when it brings me back."
]

AFK_WELCOME_MESSAGES = [
    "☀️ You're back! The entire room just lit up. Welcome back, {user}!",
    "💖 Welcome back, {user}! The server felt far too quiet without your energy!",
    "🎉 Look who returned! We missed you so much, {user}!",
    "🥳 You're finally back! Everything feels complete again. Welcome home, {user}!",
    "✨ Warmest welcome back, {user}! So genuinely happy to see you chatting again!",
    "💫 The stars have realigned, {user} is back! Welcome!",
    "✨ Yay, {user} returned! We were just talking about how much we missed you.",
    "🌸 The garden feels alive again! Welcome back to the chat, {user}.",
    "🚀 Touchdown! {user} has safely landed back in Chill-Verse.",
    "🎉 Let's go! {user} is finally off AFK. We missed your vibe!",
    "🌟 Look who decided to grace us with their presence! Welcome back, {user}!",
    "☕ Hope you had a great break, {user}! Grab a seat and catch up.",
    "🦋 The chat is instantly better now that {user} is here. Welcome back!",
    "🥳 Ring the alarm! {user} has returned to the sanctuary!",
    "💖 There you are, {user}! The server wasn't the same without you."
]

BUMP_PRESET_MESSAGES = [
    "🚀 **Server Bumped!** Chill-Verse has been blasted into the cosmos! Thank you for supporting the community.",
    "🌟 **Boom!** Your bump sent shockwaves across Discord! Our sanctuary continues to flourish.",
    "💖 **Bump Successful!** Spreading the warmth of Chill-Verse far and wide. You're an absolute legend!",
    "🔥 **Rising Higher!** Thanks to your bump, Chill-Verse is shining brighter than ever on the server boards.",
    "🎉 **Bump Power Activated!** You just put Chill-Verse back at the top. The entire team appreciates you!",
    "✨ **Pure Magic!** Chill-Verse was boosted through the clouds! Keep the amazing vibes rolling.",
    "🛡️ **Honor to the Realm!** Your dedication keeps our gates open and thriving. Outstanding bump!",
    "🎈 **Soaring Upward!** Another bump, another milestone reached. You made our community proud today!",
    "⚡ **Volt of Energy!** Chill-Verse just received an electrifying boost across Discord.",
    "🌙 **Twilight Ascendance!** Our voices echo louder thanks to your bump. Thank you for showing love!",
    "🌌 **Galactic Boost!** Chill-Verse is now orbiting at maximum altitude!",
    "💥 **Impact!** Your bump just shattered the charts. We appreciate you!",
    "👑 **Royalty Status!** Thank you for treating Chill-Verse like the kingdom it is.",
    "🌊 **Tidal Wave!** A massive wave of support just hit the server thanks to your bump.",
    "💎 **Flawless Victory!** You secured the bump and kept our community shining."
]

BUMP_15M_MESSAGES = [
    "⏳ **15-Minute Alert!** The 2-hour cooldown is almost over. Stretch those fingers!",
    "🚀 **Pre-Launch Sequence!** Chill-Verse can be launched into the stars in just 15 minutes!",
    "🛡️ **Heads up Guardians!** 15 minutes left until we can boost our sanctuary back to the summit.",
    "✨ **Magic Gathering!** Only 15 minutes remain before the next bump cycle opens!",
    "⚡ **Charging Energy!** 15 minutes until our next bump pulse goes live. Be ready to claim that +250 XP!",
    "🔔 **Almost Time!** The cooldown timer is ticking down—15 minutes until the gates open!",
    "💫 **Cosmic Alignment:** In 15 minutes, Chill-Verse will be eligible to bump again!",
    "🔥 **Stoking the Fire!** 15 minutes left on the clock. Who is taking the XP crown this round?",
    "🌟 **Starlight Alert!** Only 15 minutes to go before our next server boost is unlocked.",
    "🎈 **Prepare for Liftoff!** 15 minutes on the countdown. Get your `.bump` command primed!",
    "⏱️ **15 Minutes!** The hype train is leaving the station soon. Get ready!",
    "👀 **Keep your eyes peeled!** Only 15 minutes left until the bump button works again.",
    "⚔️ **Sharpen your swords!** The battle for the next +250 XP begins in 15 minutes.",
    "🏎️ **Start your engines!** 15 minutes to go. Who will be the fastest to bump?",
    "⏳ **The sands of time run low!** 15 minutes until Chill-Verse needs your boost."
]

BUMP_READY_MESSAGES = [
    "🔔 **TIME TO BUMP!** The 2-hour cooldown is officially over! First to bump takes the **+250 XP**!",
    "🚀 **BUMP GATES OPEN!** Chill-Verse is ready for another boost! Run `.bump` right now!",
    "⚡ **READY FOR ACTION!** The server needs your bump power! Claim your reward today!",
    "🎉 **COOLDOWN FINISHED!** Boost our world to the top of Discord with `.bump`!",
    "🌟 **THE STAGE IS YOURS!** It's time to bump! Show our community some love and grab that XP!",
    "🛡️ **DEFENDERS ASSEMBLE!** The bump timer has cleared! Type `.bump` to push us higher!",
    "🔥 **CHILL-VERSE IS READY!** Fire up your `.bump` command and claim the top booster spot!",
    "🎈 **BUMP UNLOCKED!** Don't let the server wait—boost us up and take home your XP!",
    "✨ **FRESH CYCLE STARTED!** The clock hit zero! Step up and drop a `.bump` in the chat!",
    "💫 **BOOST WINDOW LIVE!** Let's make Chill-Verse shine across Discord again. Hit `.bump` now!",
    "🚨 **GO GO GO!** The bump timer is clear! Claim your XP right now!",
    "🔓 **VAULT UNLOCKED!** The bump cooldown is over. Boost us and grab the 250 XP!",
    "🏆 **CHAMPION NEEDED!** Who will step up and `.bump` the server today?",
    "🟢 **GREEN LIGHT!** We are clear for liftoff. Drop a `.bump` in the chat!",
    "💥 **BOOM! Timer is at ZERO!** Send Chill-Verse to the top and take your reward!"
]

REVIVE_ICEBREAKERS = [
    "If you could have any superpower for 24 hours, what would it be and why?",
    "What's your current favorite video game or series that you can't put down?",
    "If you could travel to any country tomorrow with everything paid for, where are you going?",
    "What is the single best food to eat while binge-watching shows?",
    "If you had to listen to only one music artist for an entire month, who is it?",
    "What's an unpopular opinion you have that will make everyone in chat debate?",
    "Coffee, Chai, Energy Drinks, or Cold Water? What fuels your day?",
    "What was the most fun thing that happened to you this week?",
    "If you could instantly master any language or musical instrument, which would you pick?",
    "What is your all-time favorite movie that you can rewatch without getting bored?",
    "If animals could talk, which species would be the rudest?",
    "What's a movie that everyone loves but you actually secretly hate?",
    "You can only eat one dessert for the rest of your life. What are you picking?",
    "What is the weirdest habit you have when you are completely alone?",
    "If you were forced to participate in a reality TV show, which one would you choose and why?"
]

# ==============================================================================
# SERVER BLUEPRINT
# ==============================================================================
SERVER_BLUEPRINT: List[Dict[str, Any]] = [
    {"category": "Information & Updates", "channels": [
        {"name": "🛡️・server-rules", "type": "text", "restricted": False, "read_only": True},
        {"name": "👋・welcome", "type": "text", "restricted": False},
        {"name": "📢・announcements", "type": "text", "restricted": False, "read_only": True},
        {"name": "🎂・birthdays", "type": "text", "restricted": False},
        {"name": "📢・level-announcements", "type": "text", "restricted": False, "read_only": True},
        {"name": "🎫・tickets", "type": "text", "restricted": False},
        {"name": "🎨・colours", "type": "text", "restricted": False},
        {"name": "🏷️・change-nickname", "type": "text", "restricted": False, "read_only": True}
    ]},
    {"category": "Team Area", "channels": [
        {"name": "🚨・team-news", "type": "text", "restricted": True},
        {"name": "🛡️・team-rules", "type": "text", "restricted": True},
        {"name": "💬・team-chat", "type": "text", "restricted": True},
        {"name": "⏰・bump", "type": "text", "restricted": False}
    ]},
    {"category": "Chill Area", "channels": [
        {"name": "☁️・chat", "type": "text", "restricted": False},
        {"name": "🍸・chat-ai", "type": "text", "restricted": False},
        {"name": "🪄・chat-en", "type": "text", "restricted": False},
        {"name": "✨・chat-ai-beta", "type": "text", "restricted": False}
    ]},
    {"category": "Forms & Discussions Area", "channels": [
        {"name": "🖇️・daily-polls", "type": "text", "restricted": False},
        {"name": "🗣️・nerdyy-stuff", "type": "text", "restricted": False},
        {"name": "💗・shayari-and-poetry", "type": "text", "restricted": False},
        {"name": "🐥・discussions", "type": "text", "restricted": False}
    ]},
    {"category": "Fun Area", "channels": [
        {"name": "🥊・playground", "type": "text", "restricted": False},
        {"name": "🚦・confession", "type": "text", "restricted": False},
        {"name": "🤪・memes", "type": "text", "restricted": False}
    ]},
    {"category": "Event Area", "channels": [
        {"name": "🎉・giveaways", "type": "text", "restricted": False},
        {"name": "⭐・vouch", "type": "text", "restricted": False}
    ]},
    {"category": "Media & Share", "channels": [
        {"name": "🍩・media-share", "type": "text", "restricted": False},
        {"name": "🎨・arts-and-crafts", "type": "text", "restricted": False},
        {"name": "🛼・pfp-share", "type": "text", "restricted": False},
        {"name": "📷・photography", "type": "text", "restricted": False},
        {"name": "🫂・selfies", "type": "text", "restricted": False}
    ]},
    {"category": "Music Area", "channels": [
        {"name": "🎵・Hade Music", "type": "voice", "restricted": False},
        {"name": "🎸・Atom Music", "type": "voice", "restricted": False}
    ]},
    {"category": "Special Activities", "channels": [
        {"name": "🎤・drop-your-songs", "type": "text", "restricted": False},
        {"name": "ヅ・Chill-Verse activities !!", "type": "voice", "restricted": False}
    ]},
    {"category": "Voice Chat", "channels": [
        {"name": "🍔 | Duo", "type": "voice", "restricted": False, "user_limit": 2},
        {"name": "🍞 | Trio", "type": "voice", "restricted": False, "user_limit": 3},
        {"name": "🧀 | squad", "type": "voice", "restricted": False, "user_limit": 4},
        {"name": "🍕 | chit-chat", "type": "voice", "restricted": False, "user_limit": 12},
        {"name": "🍺 | Vip", "type": "voice", "restricted": False, "user_limit": 50}
    ]},
    {"category": "Admin Area 🔒", "channels": [
        {"name": "📢・discord-news", "type": "text", "restricted": True},
        {"name": "💼・bot-commands", "type": "text", "restricted": True},
        {"name": "🩸・bot-errors", "type": "text", "restricted": True},
        {"name": "📜・audit-logs", "type": "text", "restricted": True},
        {"name": "🧪・bot-testing", "type": "text", "restricted": True}
    ]},
]

# ==============================================================================
# ASYNC STORAGE & CACHING ENGINE
# ==============================================================================
FILE_LOCKS: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

def _read_file_sync(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _write_file_sync(path: str, data: Any) -> None:
    temp_path = f"{path}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(temp_path, path)
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        print(f"[Storage Engine] Failed writing {path}: {e}")

async def safe_read_json(path: str, default: Any) -> Any:
    async with FILE_LOCKS[path]:
        return await asyncio.to_thread(_read_file_sync, path, default)

async def safe_write_json(path: str, data: Any) -> None:
    async with FILE_LOCKS[path]:
        return await asyncio.to_thread(_write_file_sync, path, data)

async def init_xp_cache():
    global XP_CACHE, XP_CACHE_DIRTY
    XP_CACHE = await safe_read_json(XP_DATABASE_FILE, {})
    XP_CACHE_DIRTY = False

async def flush_xp_cache():
    global XP_CACHE_DIRTY
    if XP_CACHE_DIRTY:
        await safe_write_json(XP_DATABASE_FILE, XP_CACHE)
        XP_CACHE_DIRTY = False

async def get_user_xp(user_id: int) -> int:
    return XP_CACHE.get(str(user_id), 0)

async def add_user_xp(user_id: int, amount: int) -> Tuple[int, int]:
    global XP_CACHE_DIRTY
    uid = str(user_id)
    prev_xp = XP_CACHE.get(uid, 0)
    new_xp = prev_xp + amount
    XP_CACHE[uid] = new_xp
    XP_CACHE_DIRTY = True
    return prev_xp, new_xp

async def remove_user_xp(user_id: int, amount: int) -> Tuple[int, int]:
    global XP_CACHE_DIRTY
    uid = str(user_id)
    prev_xp = XP_CACHE.get(uid, 0)
    new_xp = max(0, prev_xp - amount)
    XP_CACHE[uid] = new_xp
    XP_CACHE_DIRTY = True
    return prev_xp, new_xp

async def set_user_xp(user_id: int, amount: int) -> Tuple[int, int]:
    global XP_CACHE_DIRTY
    uid = str(user_id)
    prev_xp = XP_CACHE.get(uid, 0)
    new_xp = max(0, amount)
    XP_CACHE[uid] = new_xp
    XP_CACHE_DIRTY = True
    return prev_xp, new_xp

def calculate_level(xp: int) -> int:
    if xp <= 0:
        return 0
    return int((xp / 75) ** 0.5)

def xp_for_level(level: int) -> int:
    return int(75 * (level**2))

async def load_birthdays() -> Dict[str, str]:
    return await safe_read_json(BIRTHDAYS_FILE, {})

async def save_birthdays(data: Dict[str, str]) -> None:
    await safe_write_json(BIRTHDAYS_FILE, data)

async def record_confession(user_id: int, content: str) -> int:
    data = await safe_read_json(CONFESSIONS_FILE, {"last_id": 0, "entries": []})
    new_id = data.get("last_id", 0) + 1
    data["last_id"] = new_id
    if "entries" not in data or not isinstance(data["entries"], list):
        data["entries"] = []
    data["entries"].append({
        "id": new_id,
        "user_id": user_id,
        "content": content,
        "timestamp": discord.utils.utcnow().isoformat(),
    })
    await safe_write_json(CONFESSIONS_FILE, data)
    return new_id

async def persist_runtime_state():
    state = {
        "last_bump_time": LAST_BUMP_TIME.timestamp() if LAST_BUMP_TIME else None,
        "afk_users": {
            str(uid): {"reason": info["reason"], "time": info["time"].isoformat()}
            for uid, info in AFK_USERS.items()
        },
        "announced_birthdays_today": ANNOUNCED_BIRTHDAYS_TODAY,
        "reminded_birthdays_tomorrow": REMINDED_BIRTHDAYS_TOMORROW,
        "maintenance_mode": MAINTENANCE_MODE,
    }
    await safe_write_json(STATE_FILE, state)

async def restore_runtime_state():
    global LAST_BUMP_TIME, AFK_USERS, ANNOUNCED_BIRTHDAYS_TODAY, REMINDED_BIRTHDAYS_TOMORROW, MAINTENANCE_MODE
    state = await safe_read_json(STATE_FILE, {})
    if not state:
        return

    raw_ts = state.get("last_bump_time")
    if raw_ts:
        LAST_BUMP_TIME = datetime.datetime.fromtimestamp(raw_ts, datetime.timezone.utc)

    raw_afk = state.get("afk_users", {})
    AFK_USERS.clear()
    for uid_str, data in raw_afk.items():
        try:
            AFK_USERS[int(uid_str)] = {
                "reason": data.get("reason", "AFK"),
                "time": datetime.datetime.fromisoformat(data["time"]),
            }
        except Exception:
            continue

    ANNOUNCED_BIRTHDAYS_TODAY = state.get("announced_birthdays_today", [])
    REMINDED_BIRTHDAYS_TOMORROW = state.get("reminded_birthdays_tomorrow", [])
    MAINTENANCE_MODE = state.get("maintenance_mode", False)

async def sync_member_level_roles(member: discord.Member, new_xp: int) -> Optional[discord.Role]:
    guild = member.guild
    current_lvl = calculate_level(new_xp)

    target_tier_name = None
    for min_lvl, r_name in LEVEL_TIERS:
        if current_lvl >= min_lvl:
            target_tier_name = r_name
            break

    target_role = discord.utils.get(guild.roles, name=target_tier_name) if target_tier_name else None
    tier_role_names = {r_name for _, r_name in LEVEL_TIERS}

    to_remove = [
        r for r in member.roles
        if r.name in tier_role_names and r != target_role and r < guild.me.top_role
    ]

    try:
        if to_remove:
            await member.remove_roles(*to_remove, reason="Level Tier Recalibration")
        if target_role and target_role not in member.roles and target_role < guild.me.top_role:
            await member.add_roles(target_role, reason=f"Level Tier Sync (Level {current_lvl})")
    except (discord.Forbidden, discord.HTTPException):
        pass

    return target_role

async def handle_level_up(
    member: discord.Member,
    prev_xp: int,
    new_xp: int,
    fallback_ch: Optional[discord.abc.Messageable] = None,
):
    old_lvl = calculate_level(prev_xp)
    new_lvl = calculate_level(new_xp)

    if new_lvl <= old_lvl:
        return

    unlocked_role = await sync_member_level_roles(member, new_xp)

    lvl_channel = discord.utils.get(member.guild.text_channels, name="📢・level-announcements") or fallback_ch
    if lvl_channel and hasattr(lvl_channel, "send"):
        embed = discord.Embed(
            title="🎊 LEVEL UP! 🎊",
            description=f"Congratulations {member.mention}! You leveled up from **Level {old_lvl}** to **Level {new_lvl}**!",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Total XP", value=f"**{new_xp:,} XP**", inline=True)
        embed.add_field(name="Current Level", value=f"**Level {new_lvl}**", inline=True)

        if unlocked_role:
            embed.add_field(name="⭐ New Rank Unlocked", value=f"**{unlocked_role.mention}**", inline=False)

        next_lvl_xp = xp_for_level(new_lvl + 1)
        embed.add_field(name="Next Level At", value=f"`{next_lvl_xp:,} XP`", inline=False)
        embed.set_footer(text="Keep chatting and bumping to unlock higher tier perks!")

        try:
            await lvl_channel.send(content=f"🎉 {member.mention} just hit **Level {new_lvl}**!", embed=embed)
        except (discord.HTTPException, discord.Forbidden):
            pass

# ==============================================================================
# AUTHORITY CHECKS & SYSTEM HELPERS
# ==============================================================================
def is_authority_holder():
    async def predicate(ctx: commands.Context):
        if not ctx.guild:
            return False
        if ctx.author.id == ctx.guild.owner_id or getattr(ctx.author.guild_permissions, "administrator", False):
            return True
        authority_roles = {"supreme leader", "highness", "authority"}
        user_roles = {r.name.lower().strip() for r in getattr(ctx.author, "roles", [])}
        if bool(authority_roles.intersection(user_roles)):
            return True
        raise commands.CheckFailure("⛔ **Restricted:** Only Administrators and Authority holders can execute this command.")
    return commands.check(predicate)

def is_purge_authorized():
    async def predicate(ctx: commands.Context):
        if not ctx.guild:
            return False
        if ctx.author.id == ctx.guild.owner_id or getattr(ctx.author.guild_permissions, "administrator", False):
            return True
        purge_roles = {"supreme leader", "highness", "authority"}
        user_roles = {r.name.lower().strip() for r in getattr(ctx.author, "roles", [])}
        if bool(purge_roles.intersection(user_roles)):
            return True
        raise commands.CheckFailure("⛔ **Restricted:** The purge command is strictly reserved for **Supreme Leader**, **Highness**, and **Authority**.")
    return commands.check(predicate)

def is_team_authorized():
    async def predicate(ctx: commands.Context):
        if not ctx.guild:
            return False
        if ctx.author.id == ctx.guild.owner_id or getattr(ctx.author.guild_permissions, "administrator", False):
            return True
        team_roles = {"supreme leader", "highness", "authority", "head moderator", "moderator", "trial mod", "chill-verse team"}
        user_roles = {r.name.lower().strip() for r in getattr(ctx.author, "roles", [])}
        if bool(team_roles.intersection(user_roles)):
            return True
        raise commands.CheckFailure("⛔ **Restricted:** Only Staff Team members can execute this command.")
    return commands.check(predicate)

def can_moderate(ctx: commands.Context, target: discord.Member) -> bool:
    """Enforces Discord Role Hierarchy."""
    if target.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        return False
    if target.top_role >= ctx.guild.me.top_role:
        return False
    if target.id == ctx.guild.owner_id or target.id == ctx.author.id:
        return False
    return True

def is_team_member(member: Union[discord.Member, discord.User]) -> bool:
    if not isinstance(member, discord.Member):
        return False
    if getattr(member.guild_permissions, "administrator", False):
        return True
    team_roles = {
        "supreme leader", "highness", "authority", "head moderator", "moderator", "trial mod", "chill-verse team",
    }
    user_roles = {r.name.lower().strip() for r in getattr(member, "roles", [])}
    return bool(team_roles.intersection(user_roles))

async def resolve_guild_context(interaction: discord.Interaction) -> Optional[discord.Guild]:
    """Async Guild Resolver to patch DM caching issues."""
    if interaction.guild:
        return interaction.guild
    for g in interaction.client.guilds:
        if g.get_member(interaction.user.id):
            return g
        try:
            if await g.fetch_member(interaction.user.id):
                return g
        except (discord.NotFound, discord.HTTPException):
            continue
    return None

def normalize_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", name).lower()

# ==============================================================================
# ADMIN AREA SECURITY ENFORCER
# ==============================================================================
async def enforce_admin_area_security(guild: discord.Guild):
    admin_cat = discord.utils.get(guild.categories, name="Admin Area 🔒")
    if not admin_cat:
        return

    supreme_role = discord.utils.get(guild.roles, name="Supreme Leader")
    highness_role = discord.utils.get(guild.roles, name="Highness")

    strict_overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True,
            embed_links=True, manage_channels=True, manage_permissions=True, attach_files=True,
        ),
    }

    if supreme_role:
        strict_overwrites[supreme_role] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        )
    if highness_role:
        strict_overwrites[highness_role] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        )

    try:
        for target in list(admin_cat.overwrites.keys()):
            if target not in strict_overwrites:
                await admin_cat.set_permissions(target, overwrite=None)
        await admin_cat.edit(overwrites=strict_overwrites)
    except Exception as e:
        print(f"[Security Enforcer] Failed setting Admin Area category permissions: {e}")

    for ch in admin_cat.channels:
        try:
            for target in list(ch.overwrites.keys()):
                if target not in strict_overwrites:
                    await ch.set_permissions(target, overwrite=None)
            await ch.edit(overwrites=strict_overwrites)
        except Exception:
            pass

async def get_or_create_audit_channel(guild: discord.Guild) -> discord.TextChannel:
    target_name = "📜・audit-logs"
    ch = discord.utils.get(guild.text_channels, name=target_name) or discord.utils.get(guild.text_channels, name="audit-logs")
    if ch:
        return ch

    admin_cat = discord.utils.get(guild.categories, name="Admin Area 🔒")
    admin_roles = ["Supreme Leader", "Highness"]

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True, embed_links=True, manage_channels=True,
        ),
    }
    for rname in admin_roles:
        r = discord.utils.get(guild.roles, name=rname)
        if r:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, read_message_history=True)

    return await guild.create_text_channel(
        name=target_name, category=admin_cat, overwrites=overwrites, reason="Private Audit Channel",
    )

async def get_or_create_testing_channel(guild: discord.Guild) -> discord.TextChannel:
    target_name = "🧪・bot-testing"
    ch = discord.utils.get(guild.text_channels, name=target_name) or discord.utils.get(guild.text_channels, name="bot-testing")
    if ch:
        return ch

    admin_cat = discord.utils.get(guild.categories, name="Admin Area 🔒")
    admin_roles = ["Supreme Leader", "Highness"]

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True, embed_links=True, manage_channels=True,
        ),
    }
    for rname in admin_roles:
        r = discord.utils.get(guild.roles, name=rname)
        if r:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    return await guild.create_text_channel(
        name=target_name, category=admin_cat, overwrites=overwrites, reason="Diagnostics Channel",
    )

async def get_or_create_memory_channel(guild: discord.Guild) -> discord.TextChannel:
    memory_ch = discord.utils.get(guild.text_channels, name="bot-memory")
    if memory_ch:
        return memory_ch

    admin_roles = ["Supreme Leader", "Highness"]
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True, attach_files=True,
        ),
    }
    for rname in admin_roles:
        r = discord.utils.get(guild.roles, name=rname)
        if r:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, read_message_history=True)

    return await guild.create_text_channel(
        name="bot-memory", overwrites=overwrites, reason="Arkbot State Engine",
    )

async def find_latest_backup_from_discord(guild: discord.Guild) -> Optional[Dict[str, Any]]:
    channels = [
        discord.utils.get(guild.text_channels, name="🩸・bot-errors"),
        discord.utils.get(guild.text_channels, name="bot-errors"),
        discord.utils.get(guild.text_channels, name="bot-memory"),
    ]
    for ch in channels:
        if not ch:
            continue
        try:
            async for msg in ch.history(limit=50):
                if msg.author == guild.me and msg.attachments:
                    for att in msg.attachments:
                        if att.filename.endswith(".json"):
                            content = await att.read()
                            data = json.loads(content.decode("utf-8"))
                            if isinstance(data, dict) and ("user_xp" in data or "categories" in data):
                                return data
        except Exception as e:
            print(f"[Backup Search] Failed scanning #{ch.name}: {e}")
    return None

async def purge_all_old_backups(channel: discord.TextChannel):
    """Enforces single master backup retention by removing previous backups."""
    try:
        async for msg in channel.history(limit=100):
            if msg.author == channel.guild.me:
                has_backup_file = any(att.filename.endswith(".json") for att in msg.attachments)
                has_backup_text = "backup" in msg.content.lower() or "snapshot" in msg.content.lower()
                if has_backup_file or has_backup_text:
                    try:
                        await msg.delete()
                        await asyncio.sleep(0.3)
                    except (discord.NotFound, discord.HTTPException):
                        pass
    except Exception as e:
        print(f"Failed purging old backups: {e}")

# ==============================================================================
# AUTO-CLEAN BOT NOTIFICATIONS & ALERTS ENGINE
# ==============================================================================
async def clear_all_bot_notifications(guild: discord.Guild):
    """Clears all stale bot messages and alerts across control channels for a clean start."""
    full_wipe_channels = [
        "🚨・team-news", "team-news", "⏰・bump", "bump", "🧪・bot-testing", "bot-testing", "💼・bot-commands", "bot-commands",
        "🛡️・team-rules", "team-rules", "🛡️・server-rules", "server-rules", "🎨・colours", "colours", "🎫・tickets", "tickets",
        "🏷️・change-nickname", "change-nickname",
    ]

    for ch_name in full_wipe_channels:
        ch = discord.utils.get(guild.text_channels, name=ch_name)
        if ch:
            try:
                await ch.purge(limit=100, check=lambda m: m.author == guild.me)
                await asyncio.sleep(0.2)
            except (discord.Forbidden, discord.HTTPException):
                pass

    confession_ch = discord.utils.get(guild.text_channels, name="🚦・confession") or discord.utils.get(guild.text_channels, name="confessions")
    if confession_ch:
        try:
            async for msg in confession_ch.history(limit=50):
                if msg.author == guild.me and msg.embeds:
                    if "Confession Box" in (msg.embeds[0].title or ""):
                        await msg.delete()
                        await asyncio.sleep(0.2)
        except (discord.Forbidden, discord.HTTPException):
            pass

    bday_ch = discord.utils.get(guild.text_channels, name="🎂・birthdays") or discord.utils.get(guild.text_channels, name="birthdays")
    if bday_ch:
        try:
            async for msg in bday_ch.history(limit=50):
                if msg.author == guild.me and msg.embeds:
                    title = msg.embeds[0].title or ""
                    if any(kw in title for kw in ["Birthday Calendar & Registration", "UPCOMING BIRTHDAY ALERT", "HAPPY BIRTHDAY"]):
                        await msg.delete()
                        await asyncio.sleep(0.2)
        except (discord.Forbidden, discord.HTTPException):
            pass

    announcement_ch = discord.utils.get(guild.text_channels, name="📢・announcements") or discord.utils.get(guild.text_channels, name="announcements")
    if announcement_ch:
        try:
            async for msg in announcement_ch.history(limit=50):
                if msg.author == guild.me and msg.embeds:
                    if "Community Notification Preferences" in (msg.embeds[0].title or ""):
                        await msg.delete()
                        await asyncio.sleep(0.2)
        except (discord.Forbidden, discord.HTTPException):
            pass

# ==============================================================================
# UNIFIED SINGLE BACKUP & RESTORATION ENGINE
# ==============================================================================
async def generate_unified_backup_payload(guild: discord.Guild) -> Dict[str, Any]:
    await flush_xp_cache()
    categories_data = []
    for cat in guild.categories:
        cat_overwrites = {}
        for target, overwrite in cat.overwrites.items():
            allow, deny = overwrite.pair()
            cat_overwrites[str(target.id)] = {
                "name": target.name,
                "type": "role" if isinstance(target, discord.Role) else "member",
                "allow": allow.value,
                "deny": deny.value,
            }

        cat_entry = {"name": cat.name, "position": cat.position, "overwrites": cat_overwrites, "channels": []}
        for ch in cat.channels:
            ch_overwrites = {}
            for target, overwrite in ch.overwrites.items():
                allow, deny = overwrite.pair()
                ch_overwrites[str(target.id)] = {
                    "name": target.name, "type": "role" if isinstance(target, discord.Role) else "member",
                    "allow": allow.value, "deny": deny.value,
                }
            cat_entry["channels"].append({
                "name": ch.name, "type": str(ch.type), "position": ch.position,
                "user_limit": getattr(ch, "user_limit", 0), "overwrites": ch_overwrites,
            })
        categories_data.append(cat_entry)

    current_blueprint = []
    for cat in guild.categories:
        cat_blueprint = {"category": cat.name, "channels": []}
        for ch in cat.channels:
            if ch.name in SYSTEM_CHANNELS:
                continue
            ch_type = "text"
            if isinstance(ch, discord.VoiceChannel):
                ch_type = "voice"
            elif isinstance(ch, getattr(discord, "ForumChannel", ())):
                ch_type = "forum"

            default_ow = ch.overwrites.get(guild.default_role)
            is_restricted, is_read_only = False, False
            if default_ow:
                if default_ow.view_channel is False: is_restricted = True
                if default_ow.send_messages is False: is_read_only = True
            elif cat.name in ["Team Area", "Admin Area 🔒"]:
                is_restricted = True

            ch_item = {"name": ch.name, "type": ch_type, "restricted": is_restricted, "read_only": is_read_only}
            if ch_type == "voice" and getattr(ch, "user_limit", 0) > 0:
                ch_item["user_limit"] = ch.user_limit
            cat_blueprint["channels"].append(ch_item)

        if cat_blueprint["channels"]:
            current_blueprint.append(cat_blueprint)

    return {
        "guild_id": guild.id,
        "guild_name": guild.name,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "categories": categories_data,
        "blueprint": current_blueprint,
        "roles": [{"name": r.name, "permissions": r.permissions.value, "color": r.color.value, "hoist": r.hoist} for r in guild.roles if not r.is_default() and not r.managed],
        "user_xp": XP_CACHE.copy(),
        "user_birthdays": await load_birthdays(),
        "confessions": await safe_read_json(CONFESSIONS_FILE, {"last_id": 0, "entries": []}),
        "last_bump_time": LAST_BUMP_TIME.timestamp() if LAST_BUMP_TIME else None,
    }

async def apply_unified_restore(guild: discord.Guild, data: Dict[str, Any]) -> Dict[str, int]:
    global SERVER_BLUEPRINT, LAST_BUMP_TIME, XP_CACHE, XP_CACHE_DIRTY
    stats = {"channels_created": 0, "perms_applied": 0, "perms_skipped": 0, "xp_users": 0, "birthdays": 0, "confessions": 0}

    saved_blueprint = data.get("blueprint")
    if saved_blueprint and isinstance(saved_blueprint, list):
        SERVER_BLUEPRINT = saved_blueprint

    raw_xp = data.get("user_xp") or {}
    if raw_xp:
        for uid, xp_val in raw_xp.items():
            try:
                XP_CACHE[str(uid)] = max(XP_CACHE.get(str(uid), 0), int(xp_val))
            except (ValueError, TypeError): continue
        XP_CACHE_DIRTY = True
        stats["xp_users"] = len(raw_xp)
        await flush_xp_cache()
        for uid_str, xp_val in XP_CACHE.items():
            try:
                if member := guild.get_member(int(uid_str)):
                    await sync_member_level_roles(member, xp_val)
            except Exception: pass

    if raw_bdays := data.get("user_birthdays"):
        curr_bdays = await load_birthdays()
        curr_bdays.update(raw_bdays)
        await save_birthdays(curr_bdays)
        stats["birthdays"] = len(curr_bdays)

    if (raw_confessions := data.get("confessions")) and isinstance(raw_confessions, dict):
        curr_confessions = await safe_read_json(CONFESSIONS_FILE, {"last_id": 0, "entries": []})
        merged_last_id = max(curr_confessions.get("last_id", 0), raw_confessions.get("last_id", 0))
        existing_ids = {e["id"] for e in curr_confessions.get("entries", []) if isinstance(e, dict) and "id" in e}
        combined_entries = list(curr_confessions.get("entries", []))

        for entry in raw_confessions.get("entries", []):
            if isinstance(entry, dict) and entry.get("id") not in existing_ids:
                combined_entries.append(entry)
                existing_ids.add(entry["id"])

        await safe_write_json(CONFESSIONS_FILE, {"last_id": merged_last_id, "entries": combined_entries})
        stats["confessions"] = len(combined_entries)

    if raw_bump := data.get("last_bump_time"):
        LAST_BUMP_TIME = datetime.datetime.fromtimestamp(raw_bump, datetime.timezone.utc)
        await persist_runtime_state()

    existing_cats = {normalize_name(c.name): c for c in guild.categories}
    for cat_data in data.get("categories", []):
        norm_cat = normalize_name(cat_data["name"])
        if norm_cat in existing_cats:
            category = existing_cats[norm_cat]
        else:
            category = await guild.create_category(name=cat_data["name"])
            existing_cats[norm_cat] = category
            await asyncio.sleep(0.3)

        for target_id, ow_info in cat_data.get("overwrites", {}).items():
            target = guild.get_role(int(target_id)) if ow_info["type"] == "role" else guild.get_member(int(target_id))
            if not target and ow_info["type"] == "role": target = discord.utils.get(guild.roles, name=ow_info.get("name"))
            if target:
                if target in category.overwrites:
                    stats["perms_skipped"] += 1
                    continue
                try:
                    await category.set_permissions(target, overwrite=discord.PermissionOverwrite.from_pair(discord.Permissions(ow_info["allow"]), discord.Permissions(ow_info["deny"])))
                    stats["perms_applied"] += 1
                except Exception: pass

        existing_chs = {normalize_name(ch.name): ch for ch in category.channels}
        for ch_data in cat_data.get("channels", []):
            ch_name, norm_ch, ch_type_str = ch_data["name"], normalize_name(ch_data["name"]), ch_data.get("type", "text")
            if norm_ch in existing_chs:
                channel = existing_chs[norm_ch]
            else:
                if "voice" in ch_type_str:
                    channel = await guild.create_voice_channel(name=ch_name, category=category, user_limit=ch_data.get("user_limit", 0))
                elif "forum" in ch_type_str:
                    try: channel = await guild.create_forum_channel(name=ch_name, category=category)
                    except Exception: channel = await guild.create_text_channel(name=ch_name, category=category)
                else:
                    channel = await guild.create_text_channel(name=ch_name, category=category)
                existing_chs[norm_ch] = channel
                stats["channels_created"] += 1
                await asyncio.sleep(0.3)

            for target_id, ow_info in ch_data.get("overwrites", {}).items():
                target = guild.get_role(int(target_id)) if ow_info["type"] == "role" else guild.get_member(int(target_id))
                if not target and ow_info["type"] == "role": target = discord.utils.get(guild.roles, name=ow_info.get("name"))
                if target:
                    if target in channel.overwrites:
                        stats["perms_skipped"] += 1
                        continue
                    try:
                        await channel.set_permissions(target, overwrite=discord.PermissionOverwrite.from_pair(discord.Permissions(ow_info["allow"]), discord.Permissions(ow_info["deny"])))
                        stats["perms_applied"] += 1
                    except Exception: pass

    await enforce_admin_area_security(guild)
    return stats

# ==============================================================================
# BUMP NOTIFICATION ENGINE
# ==============================================================================
def get_bump_role_mentions(guild: discord.Guild) -> str:
    bump_role = discord.utils.find(lambda r: r.name.lower().strip() in ["bump pings", "bump ping", "bumping"], guild.roles)
    return bump_role.mention if bump_role else "@here"

async def schedule_bump_timers(guild: discord.Guild, origin_channel: discord.TextChannel, expected_bump_time: datetime.datetime):
    target_channel = discord.utils.get(guild.text_channels, name="⏰・bump") or discord.utils.get(guild.text_channels, name="bump") or origin_channel
    if not target_channel: return
    
    now = datetime.datetime.now(datetime.timezone.utc)
    elapsed = (now - expected_bump_time).total_seconds()
    initial_delay = int(elapsed)

    try:
        if (fifteen_min_mark := 6300 - initial_delay) > 0:
            await asyncio.sleep(fifteen_min_mark)
            if LAST_BUMP_TIME != expected_bump_time: return
            
            msg_15m = random.choice(BUMP_15M_MESSAGES)
            embed = discord.Embed(
                title="⏰ Bump Reminder — 15 Minutes Remaining!",
                description=f"{msg_15m}\n\n**Chill-Verse** can be bumped again in exactly **15 minutes**.\n🎁 First to type `.bump` earns **+250 XP**!",
                color=discord.Color.gold(), timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text="Chill-Verse Bump Watch • 15 Minute Notice")
            await target_channel.send(content=get_bump_role_mentions(guild), embed=embed)

        remaining = BUMP_COOLDOWN_SECONDS - (datetime.datetime.now(datetime.timezone.utc) - expected_bump_time).total_seconds()
        if remaining > 0:
            await asyncio.sleep(remaining)
            
        if LAST_BUMP_TIME != expected_bump_time: return
        
        msg_ready = random.choice(BUMP_READY_MESSAGES)
        embed = discord.Embed(
            title="🔔 Chill-Verse is Ready to Bump!",
            description=f"{msg_ready}\n\nType **`.bump`** right now to boost the server and claim your **+250 XP** reward!",
            color=discord.Color.green(), timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="Cooldown Ended • Bump Unlocked")
        await target_channel.send(content=get_bump_role_mentions(guild), embed=embed)
    except asyncio.CancelledError:
        pass

# ==============================================================================
# UI COMPONENTS (NICKNAMES, XP DROPS, CONFESSIONS, COLOURS, TICKETS, BDAY, ADMIN)
# ==============================================================================
async def _schedule_message_deletion(message: Optional[discord.Message], delay: float = 7.0):
    if not message: return
    await asyncio.sleep(delay)
    try: await message.delete()
    except (discord.NotFound, discord.HTTPException): pass

class NicknameModal(Modal, title="Update Server Nickname"):
    new_nick = TextInput(label="New Server Nickname", placeholder="Enter your new nickname (max 32 characters)...", required=True, max_length=32)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        if not member: return await interaction.followup.send("⚠️ Failed to resolve member profile.", ephemeral=True)
        if member.id == interaction.guild.owner_id: return await interaction.followup.send("⚠️ Discord prevents bots from changing the server owner's nickname.", ephemeral=True)
        if member.top_role >= interaction.guild.me.top_role: return await interaction.followup.send("⚠️ My bot role is lower than or equal to yours, Discord prevents me from editing your nickname.", ephemeral=True)
        new_name = self.new_nick.value.strip()
        try:
            old_name = member.display_name
            await member.edit(nick=new_name, reason="Self-service nickname changer (Level 11+)")
            await interaction.followup.send(f"✅ Your server nickname has been updated from **{old_name}** to **{new_name}**!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("⚠️ Missing permissions to modify your nickname.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"⚠️ Discord error: {e}", ephemeral=True)

class NicknamePanelView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🏷️ Change Nickname", style=discord.ButtonStyle.primary, custom_id="persistent_change_nickname")
    async def change_nick_btn(self, interaction: discord.Interaction, button: Button):
        user_xp = await get_user_xp(interaction.user.id)
        lvl = calculate_level(user_xp)
        is_admin = getattr(getattr(interaction.user, "guild_permissions", None), "administrator", False)
        if lvl < 11 and not is_admin:
            return await interaction.response.send_message(f"⛔ **Level 11+ Required!**\nYou are currently **Level {lvl}**.\nKeep chatting and bumping to unlock custom nicknames at Level 11!", ephemeral=True)
        await interaction.response.send_modal(NicknameModal())

    @discord.ui.button(label="🔄 Reset to Default", style=discord.ButtonStyle.secondary, custom_id="persistent_reset_nickname")
    async def reset_nick_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        user_xp = await get_user_xp(interaction.user.id)
        lvl = calculate_level(user_xp)
        is_admin = getattr(getattr(interaction.user, "guild_permissions", None), "administrator", False)
        if lvl < 11 and not is_admin: return await interaction.followup.send(f"⛔ **Level 11+ Required!** You are currently **Level {lvl}**.", ephemeral=True)
        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        if not member: return await interaction.followup.send("⚠️ Member identity could not be resolved.", ephemeral=True)
        if member.id == interaction.guild.owner_id or member.top_role >= interaction.guild.me.top_role:
            return await interaction.followup.send("⚠️ Cannot reset your nickname due to Discord role hierarchy restrictions.", ephemeral=True)
        try:
            await member.edit(nick=None, reason="Nickname reset to default")
            await interaction.followup.send("✅ Your nickname has been reset back to your original username!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"⚠️ Failed to reset nickname: {e}", ephemeral=True)

class ClaimXPDropView(View):
    def __init__(self, xp_amount: int):
        super().__init__(timeout=300.0)
        self.xp_amount = xp_amount
        self.claimed = False
        self.message: Optional[discord.Message] = None

    async def on_timeout(self):
        if not self.claimed and self.message:
            try: await self.message.delete()
            except (discord.NotFound, discord.HTTPException): pass

    @discord.ui.button(label="🎁 Claim XP", style=discord.ButtonStyle.green)
    async def claim_button(self, interaction: discord.Interaction, button: Button):
        if self.claimed: return await interaction.response.send_message("❌ This XP drop has already been claimed!", ephemeral=True)
        self.claimed = True
        button.disabled = True
        button.label = "Claimed!"
        button.style = discord.ButtonStyle.secondary
        prev_xp, new_xp = await add_user_xp(interaction.user.id, self.xp_amount)
        embed = discord.Embed(
            title="🎉 XP DROP CLAIMED!",
            description=(f"Congratulations {interaction.user.mention}! You reacted the fastest!\n\n💰 **Reward:** `+{self.xp_amount} XP`\n"
                         f"📊 **Total XP:** `{new_xp:,} XP` (Level {calculate_level(new_xp)})\n\n*✨ This message will disappear in a few seconds.*"),
            color=discord.Color.green(), timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=self)
        
        asyncio.create_task(_schedule_message_deletion(interaction.message, delay=7.0))
        if isinstance(interaction.user, discord.Member):
            await handle_level_up(interaction.user, prev_xp, new_xp, interaction.channel)

class SuperXPDropView(View):
    def __init__(self, xp_amount: int):
        super().__init__(timeout=180.0)
        self.xp_amount = xp_amount
        self.claimed = False
        self.message: Optional[discord.Message] = None

    async def on_timeout(self):
        if not self.claimed and self.message:
            try: await self.message.delete()
            except (discord.NotFound, discord.HTTPException): pass

    @discord.ui.button(label="⚡ CLAIM SUPER DROP ⚡", style=discord.ButtonStyle.danger)
    async def claim_super_drop(self, interaction: discord.Interaction, button: Button):
        if self.claimed: return await interaction.response.send_message("❌ Too late! Someone already claimed this Super Drop!", ephemeral=True)
        self.claimed = True
        button.disabled = True
        button.label = "Claimed!"
        button.style = discord.ButtonStyle.secondary
        prev_xp, new_xp = await add_user_xp(interaction.user.id, self.xp_amount)
        embed = discord.Embed(
            title="💥 SUPER XP DROP SECURED! 💥",
            description=(f"⚡ {interaction.user.mention} dominated the chat and grabbed the loot!\n\n🔥 **Massive Reward:** `+{self.xp_amount:,} XP`\n"
                         f"📊 **New Total:** `{new_xp:,} XP` (Level {calculate_level(new_xp)})\n\n*✨ This message will disappear in a few seconds.*"),
            color=discord.Color.from_rgb(255, 69, 0), timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=self)
        
        asyncio.create_task(_schedule_message_deletion(interaction.message, delay=7.0))
        if isinstance(interaction.user, discord.Member):
            await handle_level_up(interaction.user, prev_xp, new_xp, interaction.channel)

class ConfessionModal(Modal, title="Submit Anonymous Confession"):
    confession = TextInput(label="Your Secret Confession", style=discord.TextStyle.paragraph, placeholder="Type your confession here... Please keep it respectful of server rules.", required=True, max_length=1500)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = await resolve_guild_context(interaction)
        if not guild: return await interaction.followup.send("⚠️ Error: Server context could not be resolved.", ephemeral=True)
        confession_ch = discord.utils.get(guild.text_channels, name="🚦・confession") or discord.utils.get(guild.text_channels, name="confessions")
        if not confession_ch: return await interaction.followup.send("⚠️ Confession channel not found!", ephemeral=True)
        confession_id = await record_confession(interaction.user.id, self.confession.value)
        embed = discord.Embed(title=f"💌 Anonymous Confession #{confession_id}", description=self.confession.value, color=discord.Color.from_rgb(255, 105, 180), timestamp=discord.utils.utcnow())
        embed.set_footer(text="Anonymous Submission • Chill-Verse Confessions")
        try: await confession_ch.send(embed=embed)
        except discord.HTTPException as e: return await interaction.followup.send(f"⚠️ Failed to deliver confession: {e}", ephemeral=True)
        if audit_ch := await get_or_create_audit_channel(guild):
            log_embed = discord.Embed(title=f"🕵️ Confession #{confession_id} Trace Record", description=self.confession.value, color=discord.Color.dark_grey(), timestamp=discord.utils.utcnow())
            log_embed.add_field(name="Author", value=f"{interaction.user.mention} (`{interaction.user.id}`)")
            try: await audit_ch.send(embed=log_embed)
            except discord.HTTPException: pass
        await interaction.followup.send(f"✅ Your confession has been posted anonymously as **#{confession_id}**!", ephemeral=True)

class ConfessionPanelView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🤫 Submit Confession", style=discord.ButtonStyle.secondary, custom_id="persistent_submit_confession", emoji="💌")
    async def submit_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ConfessionModal())

class BirthdayModal(Modal, title="Register Your Birthday"):
    birthday_input = TextInput(label="Date of Birth (DD/MM or DD/MM/YYYY)", placeholder="e.g. 24/09 or 24/09/2004", required=True, max_length=10)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        val = self.birthday_input.value.strip()
        dob_match = re.match(r"^(\d{1,2})[/\-.](\d{1,2})", val)
        if not dob_match: return await interaction.followup.send("⚠️ Invalid format! Please enter your birthday in `DD/MM` or `DD/MM/YYYY` format (e.g. `14/06`).", ephemeral=True)
        day, month = int(dob_match.group(1)), int(dob_match.group(2))
        if day < 1 or day > 31 or month < 1 or month > 12: return await interaction.followup.send("⚠️ That calendar date is invalid. Please enter a valid date.", ephemeral=True)
        formatted_bdate = f"{str(day).zfill(2)}/{str(month).zfill(2)}"
        bdays = await load_birthdays()
        bdays[str(interaction.user.id)] = formatted_bdate
        await save_birthdays(bdays)
        await interaction.followup.send(f"🎂 **Birthday Registered!** Your birthday has been recorded as **{formatted_bdate}**.\nChill-Verse will send you a community celebration and pre-alert when your day arrives!", ephemeral=True)

class BirthdayPanelView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🎂 Register / Update Birthday", style=discord.ButtonStyle.primary, custom_id="persistent_register_birthday", emoji="🎉")
    async def register_birthday_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BirthdayModal())

class ColourSelectionView(View):
    def __init__(self): super().__init__(timeout=None)
    async def select_color(self, interaction: discord.Interaction, role_name: str):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild: return await interaction.followup.send("Action can only be executed in a server channel.", ephemeral=True)
        target_role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not target_role: return await interaction.followup.send(f"⚠️ Role `{role_name}` not found. Run `.setup_roles` first.", ephemeral=True)
        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        if not member: return await interaction.followup.send("Could not resolve member identity.", ephemeral=True)
        roles_to_remove = [r for r in member.roles if r.name in COLOR_ROLES and r.name != role_name and r < interaction.guild.me.top_role]
        try:
            if roles_to_remove: await member.remove_roles(*roles_to_remove, reason="Colour role switch")
            if target_role in member.roles:
                await member.remove_roles(target_role, reason="Colour role removed")
                await interaction.followup.send(f"⚪ Removed color **{target_role.name}**.", ephemeral=True)
            else:
                await member.add_roles(target_role, reason="Colour role assigned")
                await interaction.followup.send(f"🎨 Selected color: **{target_role.name}** (No notifications attached)!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("⚠️ Permission denied modifying color roles.", ephemeral=True)

    @discord.ui.button(label="🔴 Red", style=discord.ButtonStyle.secondary, custom_id="pure_color_red", row=0)
    async def red(self, interaction: discord.Interaction, button: Button): await self.select_color(interaction, "Red")
    @discord.ui.button(label="🟡 Yellow", style=discord.ButtonStyle.secondary, custom_id="pure_color_yellow", row=0)
    async def yellow(self, interaction: discord.Interaction, button: Button): await self.select_color(interaction, "Yellow")
    @discord.ui.button(label="🟢 Green", style=discord.ButtonStyle.secondary, custom_id="pure_color_green", row=0)
    async def green(self, interaction: discord.Interaction, button: Button): await self.select_color(interaction, "Green")
    @discord.ui.button(label="🔵 Blue", style=discord.ButtonStyle.secondary, custom_id="pure_color_blue", row=1)
    async def blue(self, interaction: discord.Interaction, button: Button): await self.select_color(interaction, "Blue")
    @discord.ui.button(label="🟠 Orange", style=discord.ButtonStyle.secondary, custom_id="pure_color_orange", row=1)
    async def orange(self, interaction: discord.Interaction, button: Button): await self.select_color(interaction, "Orange")
    @discord.ui.button(label="🩷 Pink", style=discord.ButtonStyle.secondary, custom_id="pure_color_pink", row=1)
    async def pink(self, interaction: discord.Interaction, button: Button): await self.select_color(interaction, "Pink")
    
    @discord.ui.button(label="⚪ Remove Colour", style=discord.ButtonStyle.danger, custom_id="pure_color_clear", row=2)
    async def clear_color(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        current_colors = [r for r in member.roles if r.name in COLOR_ROLES and r < interaction.guild.me.top_role]
        if not current_colors: return await interaction.followup.send("You don't currently have a colour role equipped.", ephemeral=True)
        await member.remove_roles(*current_colors, reason="Cleared colour roles")
        await interaction.followup.send("⚪ All color roles have been removed.", ephemeral=True)

class NotificationRolesView(View):
    def __init__(self): super().__init__(timeout=None)
    async def toggle_ping(self, interaction: discord.Interaction, role_name: str):
        await interaction.response.defer(ephemeral=True)
        target_role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not target_role: return await interaction.followup.send(f"⚠️ Role `{role_name}` not found.", ephemeral=True)
        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        try:
            if target_role in member.roles:
                await member.remove_roles(target_role, reason="Notification opt-out")
                await interaction.followup.send(f"🔕 Removed: **{target_role.name}**", ephemeral=True)
            else:
                await member.add_roles(target_role, reason="Notification opt-in")
                await interaction.followup.send(f"🔔 Added: **{target_role.name}**", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("⚠️ Permission denied modifying roles.", ephemeral=True)

    @discord.ui.button(label="⏰ Bump Pings", style=discord.ButtonStyle.primary, custom_id="ping_bump")
    async def bump_ping(self, interaction: discord.Interaction, button: Button): await self.toggle_ping(interaction, "Bump Pings")
    @discord.ui.button(label="📊 Poll Pings", style=discord.ButtonStyle.primary, custom_id="ping_polls")
    async def poll_ping(self, interaction: discord.Interaction, button: Button): await self.toggle_ping(interaction, "Poll Pings")
    @discord.ui.button(label="💬 Chat Revive", style=discord.ButtonStyle.primary, custom_id="ping_revive")
    async def revive_ping(self, interaction: discord.Interaction, button: Button): await self.toggle_ping(interaction, "Chat Revive")

class VerificationModal(Modal, title="Server Verification Form"):
    real_full_name = TextInput(label="Real Full Name", placeholder="John Doe", required=True, max_length=50)
    nickname = TextInput(label="Nickname", placeholder="Johnny", required=True, max_length=30)
    dob = TextInput(label="Date of Birth (DD/MM/YYYY)", placeholder="01/01/2005", required=True, max_length=10)
    reason = TextInput(label="Why do you want to join?", style=discord.TextStyle.paragraph, placeholder="Tell us a bit about yourself...", required=True, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = await resolve_guild_context(interaction)
        if not guild: return await interaction.followup.send("⚠️ Error: Could not determine server context.", ephemeral=True)
        member = guild.get_member(interaction.user.id)
        if not member:
            try: member = await guild.fetch_member(interaction.user.id)
            except discord.HTTPException: return await interaction.followup.send("⚠️ Error: Member profile not found.", ephemeral=True)

        dob_val = self.dob.value.strip()
        dob_match = re.match(r"^(\d{1,2})[/\-.](\d{1,2})", dob_val)
        if dob_match:
            day, month = dob_match.group(1).zfill(2), dob_match.group(2).zfill(2)
            bdays = await load_birthdays()
            bdays[str(interaction.user.id)] = f"{day}/{month}"
            await save_birthdays(bdays)

        role = discord.utils.get(guild.roles, name="Member")
        if role and role < guild.me.top_role:
            try: await member.add_roles(role, reason="Completed Verification Modal")
            except discord.Forbidden: pass

        if log_channel := await get_or_create_audit_channel(guild):
            embed = discord.Embed(title="New Member Verified", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            embed.add_field(name="User", value=interaction.user.mention, inline=False)
            embed.add_field(name="Full Name", value=self.real_full_name.value, inline=True)
            embed.add_field(name="Nickname", value=self.nickname.value, inline=True)
            embed.add_field(name="DOB", value=self.dob.value, inline=True)
            embed.add_field(name="Reason", value=self.reason.value, inline=False)
            try: await log_channel.send(embed=embed)
            except discord.HTTPException: pass
        await interaction.followup.send("Verification complete! Welcome to Chill-Verse.", ephemeral=True)

class TeamApplicationModal(Modal, title="Staff Team Application"):
    age_tz = TextInput(label="Age & Timezone", placeholder="18, EST", required=True, max_length=50)
    experience = TextInput(label="Previous Experience", style=discord.TextStyle.paragraph, placeholder="List past moderation experience...", required=True, max_length=300)
    reason = TextInput(label="Why do you want to join the Team?", style=discord.TextStyle.paragraph, placeholder="Tell us why we should choose you...", required=True, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = await resolve_guild_context(interaction)
        if not guild: return await interaction.followup.send("⚠️ Error: Server context not found.", ephemeral=True)
        team_channel = discord.utils.get(guild.text_channels, name="💬・team-chat") or discord.utils.get(guild.text_channels, name="team-news")
        embed = discord.Embed(title="🚨 New Staff Application Submitted", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Applicant", value=interaction.user.mention, inline=False)
        embed.add_field(name="Age & Timezone", value=self.age_tz.value, inline=True)
        embed.add_field(name="Experience", value=self.experience.value, inline=False)
        embed.add_field(name="Reason", value=self.reason.value, inline=False)
        if team_channel:
            try: await team_channel.send(embed=embed)
            except discord.HTTPException: pass
        await interaction.followup.send("✅ Your application has been submitted for review!", ephemeral=True)

class RulesView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, custom_id="persistent_accept_rules")
    async def accept(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(VerificationModal())

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red, custom_id="persistent_decline_rules")
    async def decline(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        guild = await resolve_guild_context(interaction)
        if not guild: return await interaction.followup.send("⚠️ Error: Server context could not be resolved.", ephemeral=True)
        try:
            await guild.kick(interaction.user, reason="Declined server rules.")
            await interaction.followup.send("You declined the rules and have been removed.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("Error: Bot lacks permission to kick members.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Error handling kick: {e}", ephemeral=True)

class CloseTicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="persistent_close_ticket", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔒 This ticket will close in 5 seconds...")
        await asyncio.sleep(5)
        try: await interaction.channel.delete(reason="Ticket closed by user.")
        except (discord.HTTPException, discord.NotFound): pass

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.blurple, custom_id="persistent_open_ticket", emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild: return await interaction.followup.send("Tickets can only be opened inside the server.", ephemeral=True)

        category = discord.utils.get(guild.categories, name="Team Area")
        clean_user_name = re.sub(r"[^a-zA-Z0-9_-]", "", interaction.user.name).lower() or "user"
        channel_name = f"ticket-{clean_user_name}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True),
        }
        for rname in ["Supreme Leader", "Highness", "Authority", "Head Moderator", "Moderator"]:
            role = discord.utils.get(guild.roles, name=rname)
            if role: overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        try:
            ticket_ch = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites, reason=f"Ticket opened by {interaction.user.name}")
        except discord.HTTPException as e:
            return await interaction.followup.send(f"⚠️ Failed to create ticket channel: {e}", ephemeral=True)

        embed = discord.Embed(title="🎫 Support Ticket", description=f"Welcome {interaction.user.mention}! Explain your issue below. High Command will assist you shortly.", color=discord.Color.blue())
        await ticket_ch.send(embed=embed, view=CloseTicketView())
        await interaction.followup.send(f"✅ Ticket created: {ticket_ch.mention}", ephemeral=True)

    @discord.ui.button(label="Apply for Team", style=discord.ButtonStyle.green, custom_id="persistent_apply_team", emoji="🛡️")
    async def apply_team(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TeamApplicationModal())


class AdminActionModal(Modal):
    def __init__(self, action: str, member: discord.Member):
        super().__init__(title=f"{action}: {member.display_name}")
        self.action = action
        self.member = member
        
        if action == "Edit Nickname":
            self.val = TextInput(label="New Nickname (Leave empty to reset)", required=False, max_length=32)
        elif action == "Set XP":
            self.val = TextInput(label="New XP Amount", placeholder="e.g. 5000", required=True)
            
        self.add_item(self.val)
        
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if self.member.top_role >= interaction.guild.me.top_role and self.member.id != interaction.guild.owner_id:
            return await interaction.followup.send("⚠️ Cannot modify this user due to Discord Role Hierarchy.", ephemeral=True)
            
        if self.action == "Edit Nickname":
            new_nick = self.val.value.strip() or None
            try:
                await self.member.edit(nick=new_nick, reason=f"Admin Dashboard Override by {interaction.user}")
                await interaction.followup.send(f"✅ Forced nickname update to: **{new_nick or 'Default Username'}**", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("⚠️ Permission denied.", ephemeral=True)
                
        elif self.action == "Set XP":
            try:
                amt = int(self.val.value.strip())
                prev_xp, new_xp = await set_user_xp(self.member.id, amt)
                await sync_member_level_roles(self.member, new_xp)
                await interaction.followup.send(f"✅ Forced XP update: **{new_xp:,} XP** (Level {calculate_level(new_xp)})", ephemeral=True)
            except ValueError:
                await interaction.followup.send("⚠️ Invalid number format.", ephemeral=True)

class AdminUserActionsView(View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=300)
        self.member = member

    @discord.ui.button(label="Force Change Nickname", style=discord.ButtonStyle.primary, emoji="🏷️")
    async def change_nick(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AdminActionModal("Edit Nickname", self.member))
        
    @discord.ui.button(label="Override XP", style=discord.ButtonStyle.success, emoji="⭐")
    async def override_xp(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AdminActionModal("Set XP", self.member))

    @discord.ui.button(label="Kick User", style=discord.ButtonStyle.danger, emoji="👢")
    async def kick_user(self, interaction: discord.Interaction, button: Button):
        if self.member.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("⚠️ Cannot kick this user due to Discord Role Hierarchy.", ephemeral=True)
        await self.member.kick(reason=f"Admin Dashboard action by {interaction.user}")
        await interaction.response.send_message(f"✅ Kicked **{self.member}**.", ephemeral=True)

class AdminControlPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Select a Member to Manage...", min_values=1, max_values=1, custom_id="admin_dashboard_select")
    async def select_user(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        selected_user = select.values[0]
        if isinstance(selected_user, discord.User):
            selected_user = interaction.guild.get_member(selected_user.id)
            
        await interaction.response.send_message(
            f"🛠️ **Managing Profile:** {selected_user.mention}\nChoose an override action below:", 
            ephemeral=True, 
            view=AdminUserActionsView(selected_user)
        )


# ==============================================================================
# PANEL DEPLOYERS
# ==============================================================================
async def deploy_nickname_panel(guild: discord.Guild):
    ch = discord.utils.get(guild.text_channels, name="🏷️・change-nickname") or discord.utils.get(guild.text_channels, name="change-nickname")
    if not ch: return
    try:
        async for msg in ch.history(limit=25):
            if msg.author == guild.me and msg.embeds and "Nickname Customization" in (msg.embeds[0].title or ""): return
    except Exception: pass

    embed = discord.Embed(
        title="🏷️ Chill-Verse Nickname Customization (Level 11+)",
        description=("Personalize how you appear in chat conversations across Chill-Verse!\n\n🔒 **Eligibility Requirement**:\n"
                     "• You must be **Level 11 or higher** to customize your nickname.\n• Active community chatters and server boosters unlock this perk automatically!\n\n"
                     "✨ Click **Change Nickname** below to set your name, or **Reset to Default** anytime."),
        color=discord.Color.gold(),
    )
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="Chill-Verse Identity Perks • Level 11+ Restricted")
    try: await ch.send(embed=embed, view=NicknamePanelView())
    except discord.HTTPException as e: print(f"[Nickname Deploy Error]: {e}")

async def deploy_rules_panel(guild: discord.Guild):
    ch = discord.utils.get(guild.text_channels, name="🛡️・server-rules") or discord.utils.get(guild.text_channels, name="server-rules")
    if not ch: return
    try:
        async for msg in ch.history(limit=25):
            if msg.author == guild.me and msg.embeds and "Official Server Rules" in (msg.embeds[0].title or ""): return
    except Exception: pass

    embed = discord.Embed(
        title="📜 Official Server Rules & Member Verification",
        description=("Welcome to **Chill-Verse**! Please read our guidelines carefully:\n\n**1.** Be respectful, kind, and supportive to everyone.\n"
                     "**2.** No discrimination, harassment, hate speech, or toxicity.\n**3.** Keep all chat conversations and media teen-friendly.\n"
                     "**4.** No spam, self-promotion, or unsolicited server invites.\n**5.** Comply with Discord's Terms of Service at all times.\n\n"
                     "👉 Click **Accept** below to submit your verification details and unlock the server, or **Decline** to leave."),
        color=discord.Color.purple(),
    )
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="Chill-Verse Rules & Verification • Click Below to Begin")
    try: await ch.send(embed=embed, view=RulesView())
    except discord.HTTPException as e: print(f"[Rules Panel Deploy Error]: {e}")

async def deploy_birthday_panel(guild: discord.Guild):
    bday_ch = discord.utils.get(guild.text_channels, name="🎂・birthdays") or discord.utils.get(guild.text_channels, name="birthdays")
    if not bday_ch: return
    try:
        async for msg in bday_ch.history(limit=25):
            if msg.author == guild.me and msg.embeds and "Birthday Calendar & Registration" in (msg.embeds[0].title or ""): return
    except Exception: pass

    embed = discord.Embed(
        title="🎂 Chill-Verse Birthday Calendar & Registration",
        description=("Never miss a community celebration!\n\nClick **Register / Update Birthday** below to submit your special day.\n\n"
                     "• **Automated Wishes**: Chill-Verse will announce and celebrate with you when your birthday arrives!\n"
                     "• **Advance Notice**: The server receives a reminder alert 24 hours prior!\n• **Upcoming List**: Type `.birthdays` anytime to view all upcoming server birthdays."),
        color=discord.Color.gold(),
    )
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="Chill-Verse Celebrations • Click Below to Register")
    try: await bday_ch.send(embed=embed, view=BirthdayPanelView())
    except discord.HTTPException as e: print(f"[Birthday Panel Deploy Error]: {e}")

async def deploy_confession_panel(guild: discord.Guild):
    confession_ch = discord.utils.get(guild.text_channels, name="🚦・confession") or discord.utils.get(guild.text_channels, name="confessions")
    if not confession_ch: return
    try:
        async for msg in confession_ch.history(limit=25):
            if msg.author == guild.me and msg.embeds and "Confession Box" in (msg.embeds[0].title or ""): return
    except Exception: pass

    embed = discord.Embed(
        title="💌 Chill-Verse Anonymous Confession Box",
        description=("Have a secret, unsaid feeling, or funny confession?\n\nClick **Submit Confession** below to post your thought 100% anonymously into the channel!\n\n"
                     "*Hate speech, spam, and severe rule breaches will be dealt with by server administrators.*"),
        color=discord.Color.from_rgb(255, 105, 180),
    )
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="Chill-Verse Anonymous Confessions • Click Below")
    try: await confession_ch.send(embed=embed, view=ConfessionPanelView())
    except discord.HTTPException as e: print(f"[Panel Deploy] Failed deploying confession box: {e}")

async def deploy_colours_panel(guild: discord.Guild):
    ch = discord.utils.get(guild.text_channels, name="🎨・colours") or discord.utils.get(guild.text_channels, name="colours")
    if not ch: return
    try:
        async for msg in ch.history(limit=25):
            if msg.author == guild.me and msg.embeds and "Username Colours" in (msg.embeds[0].title or ""): return
    except Exception: pass

    embed = discord.Embed(
        title="🎨 Chill-Verse Username Colours",
        description=("Pick a name color below to customize your chat appearance.\n\n• **Pure Cosmetic**: These roles do not receive pings, announcements, or notifications.\n"
                     "• **Single Selection**: Choosing a new color automatically replaces your previous one.\n• Click **Remove Colour** anytime to return to the server default."),
        color=discord.Color.magenta(),
    )
    embed.set_footer(text="Cosmetic Profile Styling • No Notifications Attached")
    try: await ch.send(embed=embed, view=ColourSelectionView())
    except discord.HTTPException as e: print(f"[Colour Deploy Error]: {e}")

async def deploy_notifications_panel(guild: discord.Guild, target_channel: Optional[discord.TextChannel] = None):
    ch = target_channel or discord.utils.get(guild.text_channels, name="📢・announcements")
    if not ch: return
    try:
        async for msg in ch.history(limit=25):
            if msg.author == guild.me and msg.embeds and "Community Notification Preferences" in (msg.embeds[0].title or ""): return
    except Exception: pass
    embed = discord.Embed(title="🔔 Community Notification Preferences", description="Opt-in to optional community pings by clicking below:", color=discord.Color.blurple())
    try: await ch.send(embed=embed, view=NotificationRolesView())
    except Exception: pass

async def deploy_team_rules_panel(guild: discord.Guild):
    team_rules_ch = discord.utils.get(guild.text_channels, name="🛡️・team-rules") or discord.utils.get(guild.text_channels, name="team-rules")
    if not team_rules_ch: return
    try:
        async for msg in team_rules_ch.history(limit=50):
            if msg.author == guild.me:
                await msg.delete()
                await asyncio.sleep(0.3)
    except (discord.Forbidden, discord.HTTPException): pass

    rules_embed = discord.Embed(title="🛡️ CHILL-VERSE TEAM GUIDELINES & PROTOCOL", description="Welcome to the internal staff directory. Adhere strictly to moderation escalation orders at all times.", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
    rules_embed.add_field(name="1. Impartiality & Maturity", value=("• Moderate objectively. Never let personal disputes dictate punishments.\n• Never use permissions or administrative authority in casual arguments.\n• Keep staff disagreements strictly behind closed doors in `💬・team-chat`."), inline=False)
    rules_embed.add_field(name="2. Confidentiality & Security", value=("• Everything inside `Team Area` and `Admin Area 🔒` is strictly classified.\n• Never leak ticket discussions, audit logs, or member disciplinary history.\n• Do not invite external bots or modify permissions without High Command approval."), inline=False)
    rules_embed.add_field(name="3. Command Escalation Hierarchy", value=("• **Supreme Leader / Highness**: Executive architecture & disaster restores.\n• **Authority**: Channel isolation, bulk cleanup, broadcasts & lockdowns.\n• **Moderators / Trial Mods**: Chat pacing, user warnings, timeouts, kicks, and bans."), inline=False)
    if guild.icon: rules_embed.set_thumbnail(url=guild.icon.url)
    rules_embed.set_footer(text="Chill-Verse Staff Operations • Internal Document")
    try: await team_rules_ch.send(embed=rules_embed)
    except Exception: pass

async def deploy_team_news_commands_panel(guild: discord.Guild, prefix: str = "."):
    team_news_ch = discord.utils.get(guild.text_channels, name="🚨・team-news") or discord.utils.get(guild.text_channels, name="team-news")
    if not team_news_ch: return
    try:
        async for msg in team_news_ch.history(limit=50):
            if msg.author == guild.me and msg.embeds and "TEAM & AUTHORITY ACTIVE BOT COMMANDS" in (msg.embeds[0].title or ""):
                await msg.delete()
                await asyncio.sleep(0.3)
    except Exception: pass

    commands_embed = discord.Embed(title="💼 TEAM & AUTHORITY ACTIVE BOT COMMANDS", description="Reference manual for bot commands accessible to Authority, Moderators, and Team members:", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
    commands_embed.add_field(name="🛡️ Moderation Tools (Team & Staff)", value=(f"`{prefix}ban <@user> [reason]` — Bans a member from the server.\n`{prefix}kick <@user> [reason]` — Kicks a member from the server.\n`{prefix}mute <@user> <duration> [reason]` — Timeouts a member (e.g., `10m`, `1h`, `1d`).\n`{prefix}unmute <@user>` — Removes an active timeout.\n`{prefix}warn <@user> <reason>` — DMs a formal warning and logs it."), inline=False)
    commands_embed.add_field(name="🧹 Channel Purge & Cleanup (Authority)", value=(f"`{prefix}purge <1-1000> [target]` — Bulk delete messages with user/bot/link filters.\n`{prefix}remove_bot_role <@role/@bot/all>` — Immediately cuts bot access from a room."), inline=False)
    commands_embed.add_field(name="🔒 Channel Security & Overrides (Authority)", value=(f"`{prefix}lock` / `{prefix}unlock` — Mutes or opens the current room for members.\n`{prefix}hide` / `{prefix}show` — Toggles channel visibility from standard members.\n`{prefix}permit <@user/@role>` — Whitelists a member or role into the channel.\n`{prefix}revoke <@user/@role>` — Evicts a member or role from the channel."), inline=False)
    commands_embed.add_field(name="⭐ XP Management & Spawners (Authority)", value=(f"`{prefix}addxp <@user> <amount>` — Grants XP and automatically recalculates rank roles.\n`{prefix}removexp <@user> <amount>` — Deducts XP and updates tier roles accordingly.\n`{prefix}setxp <@user> <amount>` — Sets exact XP and syncs corresponding rank roles.\n`{prefix}superdrop [amount] [#ch]` — Spawns a massive Super XP drop.\n`{prefix}xpdrop [amount] [#ch]` — Spawns a standard wild XP drop."), inline=False)
    commands_embed.add_field(name="📢 Announcements & Community Pacing (Staff & Team)", value=(f"`{prefix}announce [optional #channel] <title> | <text> [--everyone/--here]` — Posts official announcement embeds.\n`{prefix}revive [optional topic]` — Pings the Chat Revive role with an icebreaker prompt.\n`{prefix}afk [reason]` — Sets an AFK status while moderating."), inline=False)
    commands_embed.set_footer(text=f"Prefix: {prefix} • Strictly restricted to Authority and Staff ranks")
    try: await team_news_ch.send(embed=commands_embed)
    except Exception as e: print(f"[Team News Deploy Error]: {e}")

async def deploy_bot_commands_panel(guild: discord.Guild, prefix: str = "."):
    cmd_channel = discord.utils.get(guild.text_channels, name="💼・bot-commands") or discord.utils.get(guild.text_channels, name="bot-commands")
    if not cmd_channel: return
    try:
        async for msg in cmd_channel.history(limit=50):
            if msg.author == guild.me:
                await msg.delete()
                await asyncio.sleep(0.3)
    except (discord.Forbidden, discord.HTTPException): pass

    header_embed = discord.Embed(title="🤖 CHILL-VERSE BOT MASTER COMMAND DIRECTORY", description=("Welcome to the official, complete command index for **Arkbot**.\nBelow is the comprehensive list of all member, staff, moderation, and system commands.\n\n" f"📌 **Default Prefix:** `{prefix}` *(Example: `{prefix}ping`)*"), color=discord.Color.blurple(), timestamp=discord.utils.utcnow())
    if guild.icon: header_embed.set_thumbnail(url=guild.icon.url)

    member_embed = discord.Embed(title="👥 1. General & Member Commands", description="Commands accessible to all verified community members:", color=discord.Color.green())
    member_embed.add_field(name=f"`{prefix}about` / `{prefix}aboutme`", value="Displays information about the bot, its maintainer, and terms of use.", inline=False)
    member_embed.add_field(name=f"`{prefix}ping`", value="Checks the bot websocket heartbeat and gateway latency.", inline=False)
    member_embed.add_field(name=f"`{prefix}bump`", value="Bumps Chill-Verse in `⏰・bump` for **+250 XP**.", inline=False)
    member_embed.add_field(name=f"`{prefix}revive` / `{prefix}chatrevive [topic]`", value="Pings **@Chat Revive** with a random icebreaker or custom topic.", inline=False)
    member_embed.add_field(name=f"`{prefix}xp` / `{prefix}rank` / `{prefix}level [@user]`", value="Inspects your own or another member's level, rank, and XP progress.", inline=False)
    member_embed.add_field(name=f"`{prefix}birthdays` / `{prefix}upcoming_birthdays`", value="Displays upcoming community birthdays and active celebrations.", inline=False)
    member_embed.add_field(name=f"`{prefix}afk [reason]`", value="Sets an AFK status. Notifies anyone who pings you and greets you upon return.", inline=False)

    mod_embed = discord.Embed(title="🛡️ 2. Authority, Moderation & Access Control", description="Reserved for **Authority**, **Highness**, and **Supreme Leader**:", color=discord.Color.orange())
    mod_embed.add_field(name=f"`{prefix}purge <1-1000> [target]`", value="Bulk deletes messages with support for filters (`@user`, `bot`, `links`).", inline=False)
    mod_embed.add_field(name=f"`{prefix}lock [optional #channel]`", value="Locks the channel, preventing regular members from sending messages.", inline=False)
    mod_embed.add_field(name=f"`{prefix}unlock [optional #channel]`", value="Unlocks the channel, restoring normal chatting permissions.", inline=False)
    mod_embed.add_field(name=f"`{prefix}hide [optional #channel]`", value="Hides the channel visibility completely from standard members.", inline=False)
    mod_embed.add_field(name=f"`{prefix}show [optional #channel]`", value="Makes a hidden channel visible to standard members again.", inline=False)
    mod_embed.add_field(name=f"`{prefix}permit <@user / @role>`", value="Explicitly whitelists a user or role to view and speak in the current channel.", inline=False)
    mod_embed.add_field(name=f"`{prefix}revoke <@user / @role>`", value="Removes explicit channel overrides for the target user or role.", inline=False)
    mod_embed.add_field(name=f"`{prefix}remove_bot_role <@role / @bot / all>`", value="Immediately strips room access for external bots.", inline=False)
    mod_embed.add_field(name=f"`{prefix}announce [#channel] <title> | <text> [--everyone/--here]`", value="Dispatches a formatted official announcement embed.", inline=False)

    team_embed = discord.Embed(title="⚖️ 3. Team Moderation Suite", description="Reserved for **Staff Team, Moderators, and Authority**:", color=discord.Color.red())
    team_embed.add_field(name=f"`{prefix}ban <@user> [reason]`", value="Bans a member from the server. Checks role hierarchy.", inline=False)
    team_embed.add_field(name=f"`{prefix}kick <@user> [reason]`", value="Kicks a member from the server.", inline=False)
    team_embed.add_field(name=f"`{prefix}mute <@user> <time> [reason]`", value="Times out a member (Format: `10m`, `1h`, `1d`).", inline=False)
    team_embed.add_field(name=f"`{prefix}unmute <@user> [reason]`", value="Removes an active timeout early.", inline=False)
    team_embed.add_field(name=f"`{prefix}warn <@user> <reason>`", value="DMs a formal warning and logs it to `📜・audit-logs`.", inline=False)

    xp_embed = discord.Embed(title="⭐ 4. XP Engine & Manual Spawners", description="Tools to grant, modify, and manually spawn interactive XP drops:", color=discord.Color.gold())
    xp_embed.add_field(name=f"`{prefix}addxp <@user> <amount>`", value="Grants XP to a member and automatically upgrades rank tier roles.", inline=False)
    xp_embed.add_field(name=f"`{prefix}removexp <@user> <amount>`", value="Deducts XP from a member and demotes rank tier roles if needed.", inline=False)
    xp_embed.add_field(name=f"`{prefix}setxp <@user> <amount>`", value="Directly sets a member's XP to an exact number and recalculates rank tiers.", inline=False)
    xp_embed.add_field(name=f"`{prefix}superdrop [amount] [#ch]`", value="**Manually spawns a Super XP Drop** (defaults to 1,000–5,000 XP).", inline=False)
    xp_embed.add_field(name=f"`{prefix}xpdrop [amount] [#ch]`", value="**Manually spawns a Standard XP Drop** (defaults to 50–150 XP).", inline=False)

    admin_embed = discord.Embed(title="⚙️ 5. Administration, Panels & Disaster Recovery", description="System recovery suite restricted to **Supreme Leader** & **Highness**:", color=discord.Color.dark_red())
    admin_embed.add_field(name=f"`{prefix}clean_start`", value="**Auto-clears all stale bot notifications, warnings, and alerts across the server.**", inline=False)
    admin_embed.add_field(name=f"`{prefix}deploy_panels`", value="Runs and deploys ALL server UI panels across every designated channel.", inline=False)
    admin_embed.add_field(name=f"`{prefix}admin_panel`", value="Spawns the Executive Admin UI Dashboard for forced user edits.", inline=False)
    admin_embed.add_field(name=f"`{prefix}setup_nicknames`", value="Deploys the Level 11+ Nickname Customization panel in `#🏷️️・change-nickname`.", inline=False)
    admin_embed.add_field(name=f"`{prefix}setup_channels`", value="Non-destructively provisions missing blueprint channels & categories.", inline=False)
    admin_embed.add_field(name=f"`{prefix}setup_roles`", value="Provisions missing staff, ping, cosmetic, and tier level roles.", inline=False)
    admin_embed.add_field(name=f"`{prefix}setup_birthdays`", value="Deploys the interactive Birthday Registration panel in `🎂・birthdays`.", inline=False)
    admin_embed.add_field(name=f"`{prefix}setup_tickets`", value="Deploys the persistent Support & Staff Application panel in `🎫・tickets`.", inline=False)
    admin_embed.add_field(name=f"`{prefix}colours`", value="Deploys the cosmetic color selection panel in `🎨・colours`.", inline=False)
    admin_embed.add_field(name=f"`{prefix}setup_confession_panel`", value="Deploys the anonymous confession box in `🚦・confession`.", inline=False)
    admin_embed.add_field(name=f"`{prefix}setup_notifications`", value="Deploys optional community notification role buttons.", inline=False)
    admin_embed.add_field(name=f"`{prefix}setbirthday [@user] [DD/MM]`", value="Manually updates or sets a member's birthday.", inline=False)
    admin_embed.add_field(name=f"`{prefix}refresh_rules`", value="Refreshes guidelines in `#🛡️・team-rules` and command list in `#🚨・team-news`.", inline=False)
    admin_embed.add_field(name=f"`{prefix}refresh_commands`", value="Refreshes this complete master manual in `#💼・bot-commands`.", inline=False)
    admin_embed.add_field(name=f"`{prefix}backup_all`", value="Generates and overwrites the single unified master backup snapshot.", inline=False)
    admin_embed.add_field(name=f"`{prefix}restore_all`", value="Restores channels, permissions, XP, birthdays, and confessions.", inline=False)
    admin_embed.add_field(name=f"`{prefix}restore_xp_from_roles`", value="Scans members and rebuilds lost XP based on their existing tier roles.", inline=False)
    admin_embed.add_field(name=f"`{prefix}maintenance [on/off/status]`", value="Locks or unlocks non-administrative commands for maintenance.", inline=False)
    admin_embed.add_field(name=f"`{prefix}shutdown [reason]`", value="Flushes state, saves master backup, and terminates cleanly.", inline=False)

    try:
        await cmd_channel.send(embed=header_embed)
        await cmd_channel.send(embed=member_embed)
        await cmd_channel.send(embed=mod_embed)
        await cmd_channel.send(embed=team_embed)
        await cmd_channel.send(embed=xp_embed)
        await cmd_channel.send(embed=admin_embed)
    except Exception as e:
        print(f"[Bot Commands Deploy Error]: {e}")

async def deploy_tickets_panel(guild: discord.Guild):
    ch = discord.utils.get(guild.text_channels, name="🎫・tickets")
    if not ch: return
    try:
        async for msg in ch.history(limit=25):
            if msg.author == guild.me and msg.embeds and "Support & Staff Applications" in (msg.embeds[0].title or ""): return
    except Exception: pass
    embed = discord.Embed(title="🎫 Chill-Verse Support & Staff Applications", description="Need staff assistance, want to report an issue, or apply for Team?\n\nChoose an option below:", color=discord.Color.blue())
    try: await ch.send(embed=embed, view=TicketView())
    except Exception: pass

async def deploy_all_system_panels(guild: discord.Guild, prefix: str = "."):
    """Runs and deploys every interface panel across the server in sequence."""
    await deploy_rules_panel(guild)
    await deploy_nickname_panel(guild)
    await deploy_team_rules_panel(guild)
    await deploy_team_news_commands_panel(guild, prefix)
    await deploy_bot_commands_panel(guild, prefix)
    await deploy_tickets_panel(guild)
    await deploy_colours_panel(guild)
    await deploy_confession_panel(guild)
    await deploy_birthday_panel(guild)
    await deploy_notifications_panel(guild)


# ==============================================================================
# SUBCLASSED BOT ENGINE
# ==============================================================================
class ArkBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=".", intents=intents, strip_after_prefix=True)
        self.remove_command("help")
        self.first_run_completed: bool = False
        self.restore_complete = asyncio.Event()

    async def setup_hook(self):
        await restore_runtime_state()
        await init_xp_cache()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try: loop.add_signal_handler(sig, lambda: asyncio.create_task(self.close()))
            except (NotImplementedError, RuntimeError): pass

        self.add_view(RulesView())
        self.add_view(TicketView())
        self.add_view(CloseTicketView())
        self.add_view(ColourSelectionView())
        self.add_view(NotificationRolesView())
        self.add_view(ConfessionPanelView())
        self.add_view(BirthdayPanelView())
        self.add_view(NicknamePanelView())
        self.add_view(AdminControlPanelView()) # Admin Dashboard Registered

        asyncio.create_task(self._auto_restore_all_guilds())

        if not hourly_backup_task.is_running(): hourly_backup_task.start()
        if not birthday_announcer_task.is_running(): birthday_announcer_task.start()
        if not xp_drop_task.is_running(): xp_drop_task.start()
        if not xp_flush_task.is_running(): xp_flush_task.start()

    async def _provision_blueprint_and_roles(self, guild: discord.Guild) -> Tuple[int, int]:
        created_channels = 0
        existing_cats = {normalize_name(cat.name): cat for cat in guild.categories}
        for cat_data in SERVER_BLUEPRINT:
            raw_cat_name = cat_data["category"]
            norm_cat = normalize_name(raw_cat_name)
            if norm_cat in existing_cats:
                category = existing_cats[norm_cat]
            else:
                category = await guild.create_category(name=raw_cat_name)
                existing_cats[norm_cat] = category

            existing_chs = {normalize_name(ch.name): ch for ch in category.channels}
            for ch_info in cat_data["channels"]:
                ch_name = ch_info["name"]
                if normalize_name(ch_name) in existing_chs:
                    continue

                ch_type = ch_info["type"]
                if ch_type == "voice":
                    await guild.create_voice_channel(name=ch_name, category=category, user_limit=ch_info.get("user_limit", 0))
                elif ch_type == "forum":
                    try: await guild.create_forum_channel(name=ch_name, category=category)
                    except Exception: await guild.create_text_channel(name=ch_name, category=category)
                else:
                    await guild.create_text_channel(name=ch_name, category=category)
                created_channels += 1

        created_roles = 0
        existing_roles = {r.name.lower().strip() for r in guild.roles}
        roles_to_deploy = [
            ("Supreme Leader", discord.Color.dark_red(), True, True), ("Highness", discord.Color.gold(), True, True),
            ("Authority", discord.Color.orange(), True, True), ("Head Moderator", discord.Color.red(), True, True),
            ("Moderator", discord.Color.yellow(), True, True), ("Trial Mod", discord.Color.blue(), True, True),
            ("Chill-Verse Team", discord.Color(0x313338), True, False), ("Chat Revive", discord.Color.from_rgb(26, 188, 156), False, True),
            ("Member", discord.Color.default(), False, False), ("Bump Pings", discord.Color.purple(), False, True),
            ("Poll Pings", discord.Color.default(), False, True),
            ("Red", discord.Color.from_rgb(255, 0, 0), False, False), ("Yellow", discord.Color.from_rgb(255, 255, 0), False, False),
            ("Green", discord.Color.from_rgb(0, 128, 0), False, False), ("Blue", discord.Color.from_rgb(0, 0, 255), False, False),
            ("Orange", discord.Color.from_rgb(255, 165, 0), False, False), ("Pink", discord.Color.from_rgb(255, 105, 180), False, False),
        ]
        for r_name, r_color, r_hoist, r_mentionable in roles_to_deploy:
            if r_name.lower().strip() not in existing_roles:
                try:
                    await guild.create_role(name=r_name, color=r_color, hoist=r_hoist, mentionable=r_mentionable, reason="Startup Role Provisioning")
                    created_roles += 1
                except Exception: pass

        return created_channels, created_roles

    async def _auto_restore_all_guilds(self):
        await self.wait_until_ready()
        global BUMP_TIMER_TASK

        try:
            for guild in self.guilds:
                backup_file = MASTER_BACKUP_TEMPLATE.format(guild_id=guild.id)
                boot_backup = await safe_read_json(backup_file, None)
                if not boot_backup or not boot_backup.get("categories"):
                    if remote_backup := await find_latest_backup_from_discord(guild):
                        boot_backup = remote_backup

                if boot_backup:
                    stats = await apply_unified_restore(guild, boot_backup)
                    print(f"[Auto-Boot] Restored {stats['channels_created']} channels, {stats['xp_users']} XP profiles, {stats['birthdays']} birthdays, {stats['confessions']} confessions in {guild.name}.")
                else:
                    for uid_str, xp_val in XP_CACHE.items():
                        if member := guild.get_member(int(uid_str)): await sync_member_level_roles(member, xp_val)

                await self._provision_blueprint_and_roles(guild)
                await clear_all_bot_notifications(guild)
                await deploy_all_system_panels(guild, self.command_prefix)
                await enforce_admin_area_security(guild)

                fresh_payload = await generate_unified_backup_payload(guild)
                await safe_write_json(backup_file, fresh_payload)

                err_channel = discord.utils.get(guild.text_channels, name="🩸・bot-errors") or discord.utils.get(guild.text_channels, name="bot-errors")
                if err_channel:
                    await purge_all_old_backups(err_channel)
                    file_stream = io.BytesIO(json.dumps(fresh_payload, indent=4).encode("utf-8"))
                    await err_channel.send(content="🔒 **Master Single Backup Snapshot (Clean Start & Panels Deployed)**", file=discord.File(file_stream, filename=f"master_backup_{guild.id}.json"))
        except Exception as e:
            print(f"[Auto-Boot Critical Error]: {e}")
            traceback.print_exc()
        finally:
            self.restore_complete.set()

        if LAST_BUMP_TIME:
            elapsed = (datetime.datetime.now(datetime.timezone.utc) - LAST_BUMP_TIME).total_seconds()
            if elapsed < BUMP_COOLDOWN_SECONDS and self.guilds:
                target_g = self.guilds[0]
                target_ch = discord.utils.get(target_g.text_channels, name="⏰・bump")
                if target_ch:
                    if BUMP_TIMER_TASK and not BUMP_TIMER_TASK.done():
                        BUMP_TIMER_TASK.cancel()
                    BUMP_TIMER_TASK = asyncio.create_task(schedule_bump_timers(target_g, target_ch, LAST_BUMP_TIME))

    async def close(self):
        print("[Shutdown Engine] Flushing state and XP cache to disk...")
        await flush_xp_cache()
        await persist_runtime_state()
        await super().close()

bot = ArkBot()

# ==============================================================================
# AUDIT LOGGING & EVENTS
# ==============================================================================
@bot.check
async def check_maintenance_mode(ctx: commands.Context):
    if not MAINTENANCE_MODE: return True
    if ctx.command and ctx.command.name in ["maintenance", "shutdown"]: return True

    is_owner = ctx.guild and ctx.author.id == ctx.guild.owner_id
    is_admin = getattr(getattr(ctx.author, "guild_permissions", None), "administrator", False)
    staff_roles = {"supreme leader", "highness", "authority"}
    user_roles = {r.name.lower().strip() for r in getattr(ctx.author, "roles", [])}
    is_high_command = bool(staff_roles.intersection(user_roles))

    if is_owner or is_admin or is_high_command: return True
    await ctx.send("🛠️ **Maintenance Mode Active:** Non-administrative commands are temporarily disabled.", delete_after=6)
    return False


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} — Chill-Verse operational.")
    global UPDATE_NOTIFIED

    await bot.restore_complete.wait()
    if bot.first_run_completed: return
    bot.first_run_completed = True

    for guild in bot.guilds:
        test_ch = await get_or_create_testing_channel(guild)
        await get_or_create_audit_channel(guild)

        if test_ch:
            embed = discord.Embed(title="🧪 Arkbot Startup Diagnostic Report", description="Clean start active. Stale notifications purged and all panels verified.", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            embed.add_field(name="Gateway Latency", value=f"`{round(bot.latency * 1000)}ms`", inline=True)
            embed.add_field(name="Active XP Profiles", value=f"`{len(XP_CACHE)} loaded`", inline=True)
            embed.add_field(name="Status", value="`Clean Start & Panels Deployed`", inline=True)
            await test_ch.send(embed=embed)

    if not UPDATE_NOTIFIED:
        for guild in bot.guilds:
            team_news_ch = discord.utils.get(guild.text_channels, name="🚨・team-news") or discord.utils.get(guild.text_channels, name="team-news")
            if team_news_ch:
                embed = discord.Embed(title="🚀 Arkbot Operational — Full Engine Online!", description="Clean start executed. Master auto-backups, bump trackers, birthday reminders, and all panels online.", color=discord.Color.green(), timestamp=discord.utils.utcnow())
                try: await team_news_ch.send(embed=embed)
                except Exception: pass
        UPDATE_NOTIFIED = True


@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot or not message.guild: return
    if log_ch := await get_or_create_audit_channel(message.guild):
        content = message.content or "*None (attachment or embed)*"
        if len(content) > 1000: content = content[:1000] + "... [truncated]"
        embed = discord.Embed(title="🗑️ Message Deleted", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Author", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Content", value=content, inline=False)
        embed.set_footer(text=f"Author: {message.author}")
        try: await log_ch.send(embed=embed)
        except (discord.HTTPException, discord.Forbidden): pass

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.author.bot or not before.guild or before.content == after.content: return
    if log_ch := await get_or_create_audit_channel(before.guild):
        b_content = before.content.strip() or "*Empty*"
        a_content = after.content.strip() or "*Empty*"
        if len(b_content) > 1000: b_content = b_content[:1000] + "... [truncated]"
        if len(a_content) > 1000: a_content = a_content[:1000] + "... [truncated]"

        embed = discord.Embed(title="✏️ Message Edited", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Author", value=f"{before.author.mention} (`{before.author.id}`)", inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Jump to Message", value=f"[Click Here]({after.jump_url})", inline=True)
        embed.add_field(name="Before", value=b_content, inline=False)
        embed.add_field(name="After", value=a_content, inline=False)
        embed.set_footer(text=f"Author: {before.author}")
        try: await log_ch.send(embed=embed)
        except (discord.HTTPException, discord.Forbidden): pass

@bot.event
async def on_member_remove(member: discord.Member):
    if log_ch := await get_or_create_audit_channel(member.guild):
        embed = discord.Embed(title="🚪 Member Left Server", color=discord.Color.dark_grey(), timestamp=discord.utils.utcnow())
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        try: await log_ch.send(embed=embed)
        except (discord.HTTPException, discord.Forbidden): pass

@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.CheckFailure):
        err_msg = str(error).strip()
        if err_msg: await ctx.send(err_msg, delete_after=6)
        return
    if isinstance(error, commands.CommandNotFound): return
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(f"⚠️ **Missing argument:** `{error.param.name}`. Run command properly.", delete_after=6)
    if isinstance(error, commands.BadArgument):
        return await ctx.send(f"⚠️ **Invalid argument:** {error}", delete_after=6)

    orig_error = getattr(error, "original", error)
    tb_text = "".join(traceback.format_exception(type(orig_error), orig_error, orig_error.__traceback__))
    if len(tb_text) > 1000: tb_text = tb_text[-1000:]
    await ctx.send(f"⚠️ **Command Error:** `{orig_error}`", delete_after=8)

    if ctx.guild:
        err_channel = discord.utils.get(ctx.guild.text_channels, name="🩸・bot-errors") or discord.utils.get(ctx.guild.text_channels, name="bot-errors")
        if err_channel:
            err_embed = discord.Embed(title="🚨 Command Runtime Error", description="An unhandled exception occurred during command execution.", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
            err_embed.add_field(name="Command", value=f"`{ctx.command}`" if ctx.command else "`Unknown`", inline=True)
            err_embed.add_field(name="Invoker", value=f"{ctx.author} (`{ctx.author.id}`)", inline=True)
            err_embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)
            err_embed.add_field(name="Exception", value=f"```py\n{type(orig_error).__name__}: {orig_error}\n```", inline=False)
            err_embed.add_field(name="Traceback", value=f"```py\n{tb_text}\n```", inline=False)
            try: await err_channel.send(embed=err_embed)
            except discord.HTTPException: pass

@bot.event
async def on_member_join(member: discord.Member):
    embed = discord.Embed(
        title="Welcome to Chill-Verse! 🎉",
        description=("**Basic Server Rules:**\n1. Be respectful, kind, and inclusive to everyone.\n2. No bullying, hate speech, spam, or toxic behavior.\n"
                     "3. Keep conversations teen and family-friendly.\n4. Follow Discord's Terms of Service at all times.\n\n"
                     "To unlock server access, click **Accept** to submit your details via form, or **Decline** to exit."),
        color=discord.Color.purple(),
    )
    sent_dm = False
    try:
        await member.send(embed=embed, view=RulesView())
        sent_dm = True
    except discord.Forbidden: pass

    channel = discord.utils.get(member.guild.text_channels, name="👋・welcome")
    if channel:
        msg = f"{member.mention} Welcome! Please check your DMs to complete verification." if sent_dm else f"{member.mention} (Please enable DMs or click Accept below to verify!)"
        await channel.send(content=msg, embed=embed, view=RulesView())


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot: return

    # --- TRUE MAINTENANCE LOCKDOWN ---
    if MAINTENANCE_MODE:
        is_admin = getattr(getattr(message.author, "guild_permissions", None), "administrator", False)
        if not is_admin:
            return  # Completely halts XP gains, drops, and tracking for non-admins
    # ---------------------------------

    ctx = await bot.get_context(message)

    if message.author.id in AFK_USERS and ctx.command and ctx.command.name == "afk":
        pass
    elif message.author.id in AFK_USERS:
        del AFK_USERS[message.author.id]
        await persist_runtime_state()
        welcome_embed = discord.Embed(description=random.choice(AFK_WELCOME_MESSAGES).format(user=message.author.mention), color=discord.Color.green())
        await message.channel.send(embed=welcome_embed, delete_after=10)

    if message.mentions:
        for mentioned in message.mentions:
            if mentioned.id in AFK_USERS and mentioned.id != message.author.id:
                afk_embed = discord.Embed(description=f"💤 **{mentioned.display_name} is currently AFK:**\n*{AFK_USERS[mentioned.id]['reason']}*", color=discord.Color.dark_purple())
                await message.channel.send(embed=afk_embed, delete_after=10)

    if isinstance(message.author, discord.Member) and not is_team_member(message.author):
        if INVITE_REGEX.search(message.content):
            try: await message.delete()
            except discord.HTTPException: pass
            return await message.channel.send(f"⚠️ {message.author.mention}, posting invite links is prohibited!", delete_after=4)

        now = discord.utils.utcnow().timestamp()
        queue = USER_MESSAGE_TIMESTAMPS[message.author.id]
        queue.append(now)
        if len([t for t in queue if now - t < 4.0]) > 5:
            queue.clear()
            try: await message.delete()
            except discord.HTTPException: pass
            return await message.channel.send(f"⚠️ {message.author.mention}, please slow down! Sending messages too quickly.", delete_after=4)

    if message.guild and not ctx.valid:
        now_ts = discord.utils.utcnow().timestamp()
        if now_ts - USER_CHAT_XP_COOLDOWN.get(message.author.id, 0.0) >= 60.0:
            USER_CHAT_XP_COOLDOWN[message.author.id] = now_ts
            prev_xp, new_xp = await add_user_xp(message.author.id, random.randint(15, 25))
            await handle_level_up(message.author, prev_xp, new_xp, message.channel)

        is_chill_area = (isinstance(message.channel, discord.TextChannel) and message.channel.category and "chill area" in message.channel.category.name.lower() and message.channel.name not in SYSTEM_CHANNELS)
        if is_chill_area:
            activity_queue = CHANNEL_CHAT_ACTIVITY[message.channel.id]
            activity_queue.append((message.author.id, now_ts))
            unique_active_users = {entry[0] for entry in activity_queue if now_ts - entry[1] <= 120.0}

            if len(unique_active_users) >= 3:
                last_super_drop = SUPER_DROP_COOLDOWNS.get(message.channel.id, 0.0)
                if (now_ts - last_super_drop >= SUPER_DROP_COOLDOWN_SECONDS) and (random.random() < 0.05):
                    SUPER_DROP_COOLDOWNS[message.channel.id] = now_ts
                    super_xp = random.randint(1000, 5000)
                    super_embed = discord.Embed(
                        title="🚨 🔥 SUPER XP DROP INCOMING! 🔥 🚨",
                        description=(f"The Chill Area is blazing hot with active members! A **SUPER DROP** has spawned!\n\n🎁 **Reward Range:** `1,000 - 5,000 XP`\n"
                                     f"💎 **This Drop:** `+{super_xp:,} XP`\n\n**Click below immediately to claim it!** *(Disappears in 3 minutes)*"),
                        color=discord.Color.from_rgb(255, 69, 0), timestamp=discord.utils.utcnow(),
                    )
                    super_embed.set_footer(text="Triggered in Chill Area • Chill-Verse")
                    view = SuperXPDropView(xp_amount=super_xp)
                    try:
                        sent_drop = await message.channel.send(embed=super_embed, view=view)
                        view.message = sent_drop
                    except discord.HTTPException: pass

    await bot.process_commands(message)


# ==============================================================================
# AUTOMATED TASKS
# ==============================================================================
@tasks.loop(seconds=60.0)
async def xp_flush_task(): await flush_xp_cache()

@tasks.loop(hours=2.0)
async def xp_drop_task():
    await bot.wait_until_ready()
    if MAINTENANCE_MODE: return
    for guild in bot.guilds:
        chill_cat = discord.utils.find(lambda c: "chill area" in c.name.lower(), guild.categories)
        if not chill_cat: continue

        eligible_channels = [ch for ch in chill_cat.text_channels if ch.name not in SYSTEM_CHANNELS and ch.permissions_for(guild.default_role).view_channel and ch.permissions_for(guild.me).send_messages and ch.permissions_for(guild.me).embed_links]
        if not eligible_channels: continue

        target_channel = random.choice(eligible_channels)
        drop_xp = random.randint(50, 150)
        embed = discord.Embed(title="🎁 A WILD XP DROP APPEARED!", description=f"Quick! Be the first member to click the button below to claim **+{drop_xp} XP**!\n\n*(Disappears in 5 minutes if unclaimed)*", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
        embed.set_footer(text="Chill Area Community Drop (Every 2 Hours) • Chill-Verse")
        view = ClaimXPDropView(xp_amount=drop_xp)
        try:
            sent_msg = await target_channel.send(embed=embed, view=view)
            view.message = sent_msg
        except discord.HTTPException: pass

@tasks.loop(hours=1.0)
async def hourly_backup_task():
    await bot.wait_until_ready()
    for guild in bot.guilds:
        backup_channel = discord.utils.get(guild.text_channels, name="🩸・bot-errors") or discord.utils.get(guild.text_channels, name="bot-errors")
        if not backup_channel: continue

        payload = await generate_unified_backup_payload(guild)
        backup_file_path = MASTER_BACKUP_TEMPLATE.format(guild_id=guild.id)
        await safe_write_json(backup_file_path, payload)

        await purge_all_old_backups(backup_channel)
        file = discord.File(io.BytesIO(json.dumps(payload, indent=4).encode("utf-8")), filename=f"master_backup_{guild.id}.json")
        try: await backup_channel.send(content="🔒 **Master Hourly Single Snapshot (Auto-Overwritten)**", file=file)
        except Exception: pass

@tasks.loop(hours=1.0)
async def birthday_announcer_task():
    await bot.wait_until_ready()
    global ANNOUNCED_BIRTHDAYS_TODAY, REMINDED_BIRTHDAYS_TOMORROW
    now = datetime.datetime.now(datetime.timezone.utc)
    today_str = now.strftime("%d/%m")
    tomorrow_str = (now + datetime.timedelta(days=1)).strftime("%d/%m")

    if now.hour == 0:
        if ANNOUNCED_BIRTHDAYS_TODAY: ANNOUNCED_BIRTHDAYS_TODAY.clear()
        if REMINDED_BIRTHDAYS_TOMORROW: REMINDED_BIRTHDAYS_TOMORROW.clear()
        await persist_runtime_state()

    birthdays = await load_birthdays()
    for guild in bot.guilds:
        bday_ch = discord.utils.get(guild.text_channels, name="🎂・birthdays") or discord.utils.get(guild.text_channels, name="birthdays")
        if not bday_ch: continue

        for uid_str, bdate in birthdays.items():
            uid = int(uid_str)
            member = guild.get_member(uid)
            if not member: continue

            if bdate == today_str and uid not in ANNOUNCED_BIRTHDAYS_TODAY:
                embed = discord.Embed(
                    title="🎂 HAPPY BIRTHDAY! 🎉",
                    description=f"Today is a very special day! Happy Birthday {member.mention}!\n\nWishing you happiness, good health, and an amazing year ahead from all of us at **Chill-Verse**! 💖",
                    color=discord.Color.gold(), timestamp=discord.utils.utcnow()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text="Chill-Verse Daily Birthday Celebration")
                try:
                    await bday_ch.send(content=f"🎉 Wish {member.mention} a Happy Birthday today! 🥳", embed=embed)
                    ANNOUNCED_BIRTHDAYS_TODAY.append(uid)
                    await persist_runtime_state()
                except Exception: pass

            elif bdate == tomorrow_str and uid not in REMINDED_BIRTHDAYS_TOMORROW and now.hour >= 12:
                reminder_embed = discord.Embed(
                    title="⏰ UPCOMING BIRTHDAY ALERT! 🎂",
                    description=f"Heads up everyone! Tomorrow is **{member.mention}**'s birthday (`{tomorrow_str}`)!\n\nGet your wishes ready to celebrate with them tomorrow! 🎈",
                    color=discord.Color.from_rgb(255, 182, 193), timestamp=discord.utils.utcnow()
                )
                reminder_embed.set_thumbnail(url=member.display_avatar.url)
                reminder_embed.set_footer(text="Chill-Verse 24-Hour Birthday Alert")
                try:
                    await bday_ch.send(embed=reminder_embed)
                    REMINDED_BIRTHDAYS_TOMORROW.append(uid)
                    await persist_runtime_state()
                except Exception: pass

# ==============================================================================
# GENERAL & ADMINISTRATIVE COMMANDS
# ==============================================================================
@bot.command(name="ping")
async def ping(ctx: commands.Context): await ctx.send(f"🏓 **Pong!** Latency: `{round(bot.latency * 1000)}ms`")

@bot.command(name="about", aliases=["aboutme", "botinfo"])
async def about_bot(ctx: commands.Context):
    owner_mention = ctx.guild.owner.mention if ctx.guild and ctx.guild.owner else "Unknown"
    
    embed = discord.Embed(
        title="🤖 About Arkbot",
        description="Arkbot is the dedicated, all-in-one proprietary system powering **Chill-Verse**.\nIt handles advanced leveling, secure moderation, automated backups, and dynamic community engagement.",
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="👨‍💻 Bot Maintainer", value="`iamthesubhanahmed`", inline=True)
    embed.add_field(name="🏢 Company", value="**Tier3.pk**", inline=True)
    embed.add_field(name="👑 Server Owner", value=owner_mention, inline=True)
    
    terms = (
        "Arkbot is a proprietary architecture developed exclusively for Chill-Verse. "
        "Unauthorized distribution, modification, reverse-engineering, or commercial reproduction is strictly prohibited. "
        "By interacting with this bot, you consent to the server's guidelines and Discord's Terms of Service."
    )
    embed.add_field(name="📜 Proprietary & Terms of Use", value=terms, inline=False)
    
    if ctx.bot.user.avatar:
        embed.set_thumbnail(url=ctx.bot.user.avatar.url)
        
    embed.set_footer(text="Arkbot Core System • Tier3.pk")
    await ctx.send(embed=embed)

@bot.command(name="bump")
async def bump(ctx: commands.Context):
    global LAST_BUMP_TIME, BUMP_TIMER_TASK
    bump_channel = discord.utils.get(ctx.guild.text_channels, name="⏰・bump") or discord.utils.get(ctx.guild.text_channels, name="bump")
    if bump_channel and ctx.channel.id != bump_channel.id:
        try: await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound, discord.HTTPException): pass
        return await ctx.send(f"⚠️ {ctx.author.mention}, the `.bump` command can only be used in {bump_channel.mention}!", delete_after=6)

    async with BUMP_LOCK:
        now = discord.utils.utcnow()
        if LAST_BUMP_TIME is not None:
            elapsed = (now - LAST_BUMP_TIME).total_seconds()
            if elapsed < BUMP_COOLDOWN_SECONDS:
                try: await ctx.message.delete()
                except (discord.Forbidden, discord.NotFound, discord.HTTPException): pass
                remaining = int(BUMP_COOLDOWN_SECONDS - elapsed)
                hours, minutes, seconds = remaining // 3600, (remaining % 3600) // 60, remaining % 60
                time_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
                lock_embed = discord.Embed(title="⛔ BUMP IS CURRENTLY LOCKED!", description=f"**Chill-Verse is on cooldown.**\n\n⏳ **Time Remaining:** `{time_str}`\n🔔 The bot will ping **@Bump Pings** in this channel **15 minutes prior** and **when ready**!", color=discord.Color.red())
                return await ctx.send(embed=lock_embed, delete_after=7)

        LAST_BUMP_TIME = now
        await persist_runtime_state()
        prev_xp, new_total_xp = await add_user_xp(ctx.author.id, 250)
        
        if BUMP_TIMER_TASK and not BUMP_TIMER_TASK.done(): 
            BUMP_TIMER_TASK.cancel()
        BUMP_TIMER_TASK = asyncio.create_task(schedule_bump_timers(ctx.guild, bump_channel or ctx.channel, LAST_BUMP_TIME))

    embed = discord.Embed(
        title="✨ CHILL-VERSE BUMPED! ✨",
        description=f"{random.choice(BUMP_PRESET_MESSAGES)}\n\n🎁 **Reward:** `{ctx.author.display_name}` earned **+250 XP**!\n📊 **Total XP:** `{new_total_xp:,} XP` (Level {calculate_level(new_total_xp)})\n\n🔒 **Bumping is now locked for the next 2 hours.**",
        color=discord.Color.gold(), timestamp=now,
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text="Dual Reminder Armed: 15m prior alert & final ready ping")
    await ctx.send(embed=embed)
    await handle_level_up(ctx.author, prev_xp, new_total_xp, ctx.channel)

# ------------------------------------------------------------------------------
# TEAM MODERATION COMMANDS (Ban, Kick, Mute, Warn)
# ------------------------------------------------------------------------------
def parse_duration(duration_str: str) -> Optional[datetime.timedelta]:
    match = re.match(r"^(\d+)([smhd])$", duration_str.lower())
    if not match: return None
    val = int(match.group(1))
    unit = match.group(2)
    if unit == 's': return datetime.timedelta(seconds=val)
    if unit == 'm': return datetime.timedelta(minutes=val)
    if unit == 'h': return datetime.timedelta(hours=val)
    if unit == 'd': return datetime.timedelta(days=val)
    return None

@bot.command(name="ban")
@is_team_authorized()
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
    if not can_moderate(ctx, member):
        return await ctx.send("⛔ **Hierarchy Error:** You do not have permission to ban this member.", delete_after=5)
    try:
        await member.send(f"🔨 You have been **banned** from **{ctx.guild.name}**.\n**Reason:** {reason}")
    except discord.Forbidden:
        pass
    await member.ban(reason=f"{ctx.author} (ID: {ctx.author.id}): {reason}")
    await ctx.send(f"🔨 **{member}** has been successfully banned. \n**Reason:** {reason}")

@bot.command(name="kick")
@is_team_authorized()
async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
    if not can_moderate(ctx, member):
        return await ctx.send("⛔ **Hierarchy Error:** You do not have permission to kick this member.", delete_after=5)
    try:
        await member.send(f"👢 You have been **kicked** from **{ctx.guild.name}**.\n**Reason:** {reason}")
    except discord.Forbidden:
        pass
    await member.kick(reason=f"{ctx.author} (ID: {ctx.author.id}): {reason}")
    await ctx.send(f"👢 **{member}** has been successfully kicked. \n**Reason:** {reason}")

@bot.command(name="mute", aliases=["timeout"])
@is_team_authorized()
async def mute(ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided."):
    if not can_moderate(ctx, member):
        return await ctx.send("⛔ **Hierarchy Error:** You do not have permission to mute this member.", delete_after=5)
    delta = parse_duration(duration)
    if not delta:
        return await ctx.send("⚠️ **Invalid duration format.** Use `10m`, `1h`, or `1d`.", delete_after=5)
    until_time = discord.utils.utcnow() + delta
    try:
        await member.timeout(until_time, reason=f"{ctx.author} (ID: {ctx.author.id}): {reason}")
        await ctx.send(f"🔇 **{member}** has been muted for **{duration}**. \n**Reason:** {reason}")
    except discord.Forbidden:
        await ctx.send("⚠️ **Permission Error:** Arkbot's role is not high enough to mute this user.", delete_after=5)

@bot.command(name="unmute", aliases=["removetimeout"])
@is_team_authorized()
async def unmute(ctx: commands.Context, member: discord.Member, *, reason: str = "Manual Unmute."):
    if not can_moderate(ctx, member):
        return await ctx.send("⛔ **Hierarchy Error:** You do not have permission to unmute this member.", delete_after=5)
    try:
        await member.timeout(None, reason=f"{ctx.author} (ID: {ctx.author.id}): {reason}")
        await ctx.send(f"🔊 **{member}** has been successfully unmuted.")
    except discord.Forbidden:
        await ctx.send("⚠️ **Permission Error:** Arkbot's role is not high enough to modify this user.", delete_after=5)

@bot.command(name="warn")
@is_team_authorized()
async def warn(ctx: commands.Context, member: discord.Member, *, reason: str):
    if not can_moderate(ctx, member):
        return await ctx.send("⛔ **Hierarchy Error:** You do not have permission to warn this member.", delete_after=5)
    try:
        await member.send(f"⚠️ You have received a formal warning in **{ctx.guild.name}**.\n**Reason:** {reason}")
    except discord.Forbidden:
        pass
    await ctx.send(f"⚠️ **{member}** has been officially warned. \n**Reason:** {reason}")
    
    if log_ch := await get_or_create_audit_channel(ctx.guild):
        embed = discord.Embed(title="⚠ Member Warned", color=discord.Color.yellow(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=True)
        embed.add_field(name="Moderator", value=f"{ctx.author.mention}", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        try: await log_ch.send(embed=embed)
        except Exception: pass

# ------------------------------------------------------------------------------
# OTHER GENERAL COMMANDS
# ------------------------------------------------------------------------------
@bot.command(name="setbirthday", aliases=["setbday", "updatebday", "updatebirthday"])
@commands.has_permissions(administrator=True)
async def set_birthday(ctx: commands.Context, member: discord.Member, dob: str):
    dob_val = dob.strip()
    dob_match = re.match(r"^(\d{1,2})[/\-.](\d{1,2})", dob_val)
    if not dob_match:
        return await ctx.send("⚠️ Invalid format! Please enter the birthday in `DD/MM` or `DD/MM/YYYY` format (e.g. `14/06`).", delete_after=6)
    
    day, month = int(dob_match.group(1)), int(dob_match.group(2))
    if day < 1 or day > 31 or month < 1 or month > 12:
        return await ctx.send("⚠️ That calendar date is invalid. Please enter a valid date.", delete_after=6)
        
    formatted_bdate = f"{str(day).zfill(2)}/{str(month).zfill(2)}"
    bdays = await load_birthdays()
    bdays[str(member.id)] = formatted_bdate
    await save_birthdays(bdays)
    
    embed = discord.Embed(
        title="🎂 Birthday Updated (Admin)",
        description=f"Successfully set {member.mention}'s birthday to **{formatted_bdate}**.",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    await ctx.send(embed=embed)

@bot.command(name="revive", aliases=["chatrevive"])
@commands.guild_only()
async def chat_revive(ctx: commands.Context, *, topic: Optional[str] = None):
    now = discord.utils.utcnow().timestamp()
    if now - (last_revive := LAST_REVIVE_TIME.get(ctx.guild.id, 0.0)) < REVIVE_COOLDOWN_SECONDS:
        remaining = int(REVIVE_COOLDOWN_SECONDS - (now - last_revive))
        return await ctx.send(f"⏳ **Chat Revive Cooldown:** You can ping the chat again in **{remaining // 60}m {remaining % 60}s**!", delete_after=6)

    revive_role = discord.utils.get(ctx.guild.roles, name="Chat Revive")
    LAST_REVIVE_TIME[ctx.guild.id] = now
    embed = discord.Embed(title="⚡ CHAT REVIVE SUMMONS! ⚡", description=f"**{ctx.author.mention} wants to wake up the chat!**\n\n🗣️ **Topic / Question:**\n> *\"{topic.strip() if topic else random.choice(REVIVE_ICEBREAKERS)}\"*\n\nCome join the conversation and earn some active XP!", color=discord.Color.from_rgb(26, 188, 156), timestamp=discord.utils.utcnow())
    embed.set_footer(text=f"Initiated by {ctx.author.display_name} • Chill-Verse")
    if ctx.author.display_avatar: embed.set_thumbnail(url=ctx.author.display_avatar.url)

    await ctx.send(content=revive_role.mention if revive_role else "@here", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True, everyone=True))
    try: await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException): pass

@bot.command(name="xp", aliases=["rank", "level"])
async def check_xp(ctx: commands.Context, member: Optional[discord.Member] = None):
    target = member or ctx.author
    user_xp = await get_user_xp(target.id)
    lvl, nxt_lvl_xp = calculate_level(user_xp), xp_for_level(calculate_level(user_xp) + 1)
    
    current_tier = "None"
    for min_lvl, r_name in LEVEL_TIERS:
        if lvl >= min_lvl:
            current_tier = r_name
            break

    embed = discord.Embed(title=f"📊 Level & XP Profile — {target.display_name}", color=discord.Color.purple(), timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Current Level", value=f"**Level {lvl}**", inline=True)
    embed.add_field(name="Total XP", value=f"**{user_xp:,} XP**", inline=True)
    embed.add_field(name="Current Rank Tier", value=f"🛡️ **{current_tier}**", inline=False)
    embed.add_field(name="Next Level At", value=f"**{nxt_lvl_xp:,} XP** (*{nxt_lvl_xp - user_xp:,} XP remaining*)", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="birthdays", aliases=["upcoming_birthdays", "upcoming_bdays", "bdayremind"])
async def upcoming_birthdays_cmd(ctx: commands.Context):
    bdays = await load_birthdays()
    if not bdays: return await ctx.send("🎂 No birthdays are currently registered. Click the button in `#🎂・birthdays` to add yours!", delete_after=6)
    
    now = datetime.datetime.now(datetime.timezone.utc)
    today_date = datetime.date(now.year, now.month, now.day)
    upcoming_list = []
    
    for uid_str, bdate in bdays.items():
        try:
            d, m = map(int, bdate.split("/"))
            member = ctx.guild.get_member(int(uid_str))
            if not member: continue
            bday_next = datetime.date(now.year + 1, m, d) if datetime.date(now.year, m, d) < today_date else datetime.date(now.year, m, d)
            upcoming_list.append(((bday_next - today_date).days, member, bdate))
        except Exception: continue

    upcoming_list.sort(key=lambda x: x[0])
    if not (top_upcoming := upcoming_list[:12]): return await ctx.send("🎂 No upcoming birthdays found among current server members.", delete_after=6)

    embed = discord.Embed(title="🎂 Upcoming Chill-Verse Birthdays", description="Here are the upcoming member birthdays recorded in the sanctuary:\n" + "\n".join([f"• {member.mention} — `{bdate}` ({'🎉 **TODAY!**' if days_left == 0 else '⏳ **Tomorrow!**' if days_left == 1 else f'in **{days_left} days**'})" for days_left, member, bdate in top_upcoming]), color=discord.Color.gold(), timestamp=discord.utils.utcnow())
    embed.set_footer(text="Register or update your date anytime in #🎂・birthdays!")
    await ctx.send(embed=embed)

@bot.command(name="addxp", aliases=["givexp", "add-xp"])
@is_authority_holder()
async def addxp(ctx: commands.Context, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("⚠️ Please specify an amount greater than 0.", delete_after=5)
    prev_xp, new_xp = await add_user_xp(member.id, amount)
    current_tier_role = await sync_member_level_roles(member, new_xp)
    old_lvl, new_lvl = calculate_level(prev_xp), calculate_level(new_xp)
    
    embed = discord.Embed(
        title="✨ XP Manually Granted",
        description=f"Successfully added **+{amount:,} XP** to {member.mention}!\n\n📊 **Total XP:** `{new_xp:,} XP`\n🎖 **Level:** `Level {new_lvl}` " + (f"*(Ranked up from Level {old_lvl}!)*" if new_lvl > old_lvl else "") + f"\n🛡️ **Current Tier:** {current_tier_role.mention if current_tier_role else '`None`'}",
        color=discord.Color.green(), timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Action by {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="removexp", aliases=["takexp", "delxp", "remove-xp"])
@is_authority_holder()
async def removexp(ctx: commands.Context, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("⚠️ Please specify an amount greater than 0.", delete_after=5)
    prev_xp, new_xp = await remove_user_xp(member.id, amount)
    current_tier_role = await sync_member_level_roles(member, new_xp)
    old_lvl, new_lvl = calculate_level(prev_xp), calculate_level(new_xp)

    embed = discord.Embed(
        title="🔻 XP Manually Deducted",
        description=f"Successfully deducted **-{amount:,} XP** from {member.mention}.\n\n📊 **Total XP:** `{new_xp:,} XP`\n🎖️ **Level:** `Level {new_lvl}` " + (f"*(Demoted from Level {old_lvl})*" if new_lvl < old_lvl else "") + f"\n🛡️ **Current Tier:** {current_tier_role.mention if current_tier_role else '`None`'}",
        color=discord.Color.red(), timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Action by {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="setxp", aliases=["set-xp"])
@is_authority_holder()
async def setxp(ctx: commands.Context, member: discord.Member, amount: int):
    if amount < 0: return await ctx.send("⚠️ XP cannot be a negative value.", delete_after=5)
    prev_xp, new_xp = await set_user_xp(member.id, amount)
    current_tier_role = await sync_member_level_roles(member, new_xp)

    embed = discord.Embed(
        title="⚙️ XP Manually Overridden",
        description=f"Successfully updated total XP for {member.mention}.\n\n📊 **Previous:** `{prev_xp:,} XP` (Level {calculate_level(prev_xp)})\n📊 **New Total:** `{new_xp:,} XP` (Level {calculate_level(new_xp)})\n🛡️ **Current Tier:** {current_tier_role.mention if current_tier_role else '`None`'}",
        color=discord.Color.blue(), timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Action by {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="superdrop", aliases=["spawndrop", "dropsuper"])
@is_authority_holder()
async def manual_super_drop(ctx: commands.Context, amount: Optional[int] = None, channel: Optional[discord.TextChannel] = None):
    target_ch = channel or ctx.channel
    super_xp = amount if (amount and amount > 0) else random.randint(1000, 5000)
    super_embed = discord.Embed(title="🚨 🔥 SUPER XP DROP INCOMING! 🔥 🚨", description=f"An authorized administrator has summoned a **SUPER DROP**!\n\n🎁 **Reward:** `+{super_xp:,} XP`\n\n**Click below immediately to claim it!** *(Disappears in 3 minutes)*", color=discord.Color.from_rgb(255, 69, 0), timestamp=discord.utils.utcnow())
    super_embed.set_footer(text=f"Summoned by {ctx.author.display_name} • Chill-Verse")
    view = SuperXPDropView(xp_amount=super_xp)
    try:
        sent_drop = await target_ch.send(embed=super_embed, view=view)
        view.message = sent_drop
        if target_ch.id != ctx.channel.id: await ctx.send(f"✅ Super Drop of `{super_xp:,} XP` spawned in {target_ch.mention}!", delete_after=5)
        try: await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound, discord.HTTPException): pass
    except discord.HTTPException as e:
        await ctx.send(f"⚠️ Failed to spawn Super Drop: {e}", delete_after=6)

@bot.command(name="xpdrop", aliases=["dropxp"])
@is_authority_holder()
async def manual_xp_drop(ctx: commands.Context, amount: Optional[int] = None, channel: Optional[discord.TextChannel] = None):
    target_ch = channel or ctx.channel
    drop_xp = amount if (amount and amount > 0) else random.randint(50, 150)
    embed = discord.Embed(title="🎁 A WILD XP DROP APPEARED!", description=f"Quick! Be the first member to click the button below to claim **+{drop_xp:,} XP**!\n\n*(Disappears in 5 minutes if unclaimed)*", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
    embed.set_footer(text=f"Spawned by {ctx.author.display_name} • Chill-Verse")
    view = ClaimXPDropView(xp_amount=drop_xp)
    try:
        sent_msg = await target_ch.send(embed=embed, view=view)
        view.message = sent_msg
        if target_ch.id != ctx.channel.id: await ctx.send(f"✅ Wild XP Drop of `{drop_xp:,} XP` spawned in {target_ch.mention}!", delete_after=5)
        try: await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound, discord.HTTPException): pass
    except discord.HTTPException as e:
        await ctx.send(f"⚠️ Failed to spawn XP Drop: {e}", delete_after=6)

@bot.command(name="lock")
@is_authority_holder()
async def lock_channel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
    target = channel or ctx.channel
    await target.set_permissions(ctx.guild.default_role, send_messages=False, reason=f"Locked by {ctx.author}")
    await ctx.send(f"🔒 {target.mention} has been locked for standard members.")

@bot.command(name="unlock")
@is_authority_holder()
async def unlock_channel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
    target = channel or ctx.channel
    await target.set_permissions(ctx.guild.default_role, send_messages=True, reason=f"Unlocked by {ctx.author}")
    await ctx.send(f"🔓 {target.mention} has been unlocked.")

@bot.command(name="hide")
@is_authority_holder()
async def hide_channel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
    target = channel or ctx.channel
    await target.set_permissions(ctx.guild.default_role, view_channel=False, reason=f"Hidden by {ctx.author}")
    await ctx.send(f"👁️‍‍🗨️ {target.mention} is now hidden from standard members.")

@bot.command(name="show")
@is_authority_holder()
async def show_channel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
    target = channel or ctx.channel
    await target.set_permissions(ctx.guild.default_role, view_channel=True, reason=f"Unhidden by {ctx.author}")
    await ctx.send(f"👁️ {target.mention} is now visible to standard members.")

@bot.command(name="permit")
@is_authority_holder()
async def permit(ctx: commands.Context, target: Union[discord.Member, discord.Role]):
    await ctx.channel.set_permissions(target, view_channel=True, send_messages=True, reason=f"Permitted by {ctx.author}")
    await ctx.send(f"✅ Whitelisted {target.mention} in {ctx.channel.mention}.")

@bot.command(name="revoke")
@is_authority_holder()
async def revoke(ctx: commands.Context, target: Union[discord.Member, discord.Role]):
    await ctx.channel.set_permissions(target, overwrite=None, reason=f"Revoked by {ctx.author}")
    await ctx.send(f"🚫 Cleared specific overrides for {target.mention} in this channel.")

@bot.command(name="remove_bot_role")
@is_authority_holder()
async def remove_bot_role(ctx: commands.Context, target: Union[discord.Role, discord.Member, str]):
    if isinstance(target, (discord.Role, discord.Member)):
        await ctx.channel.set_permissions(target, view_channel=False, send_messages=False, reason=f"Cut by {ctx.author}")
        return await ctx.send(f"✂️ Removed channel permissions for {target.mention}.")
    if isinstance(target, str) and target.lower() == "all":
        for member in ctx.guild.members:
            if member.bot and member.id != bot.user.id: await ctx.channel.set_permissions(member, view_channel=False, send_messages=False)
        return await ctx.send("✂️ Revoked channel visibility from all external bots.")
    await ctx.send("⚠️ Pass a valid `@role`, `@bot`, or `all`.")

@bot.command(name="announce")
@is_authority_holder()
async def announce(ctx: commands.Context, *, raw_content: Optional[str] = None):
    if not raw_content or not raw_content.strip(): return await ctx.send("⚠️ **Usage:** `.announce [optional #channel] <Title> | <Message> [--everyone/--here]`", delete_after=10)
    
    content = raw_content.strip()
    target_channel = None
    if ctx.message.channel_mentions:
        first_mention = ctx.message.channel_mentions[0]
        if content.startswith(first_mention.mention):
            target_channel = first_mention
            content = content[len(first_mention.mention):].strip()

    if not target_channel:
        target_channel = discord.utils.get(ctx.guild.text_channels, name="📢・announcements") or discord.utils.get(ctx.guild.text_channels, name="announcements") or next((ch for ch in ctx.guild.text_channels if "announcement" in ch.name.lower()), None) or ctx.channel

    mention_str = None
    if "--everyone" in content: mention_str, content = "@everyone", content.replace("--everyone", "").strip()
    elif "--here" in content: mention_str, content = "@here", content.replace("--here", "").strip()

    title, body = (content.split("|", 1)[0].strip() or "Community Announcement", content.split("|", 1)[1].strip()) if "|" in content else ("Community Announcement", content.strip())
    body = body or "*No message body provided.*"

    bot_perms = target_channel.permissions_for(ctx.guild.me)
    if not (bot_perms.send_messages and bot_perms.embed_links): return await ctx.send(f"⚠️️ **Permission Error:** I lack `Send Messages` or `Embed Links` in {target_channel.mention}.", delete_after=8)

    embed = discord.Embed(title=title, description=body, color=discord.Color.gold(), timestamp=discord.utils.utcnow())
    embed.set_footer(text=f"Issued by {ctx.author.display_name}")
    if ctx.guild.icon: embed.set_thumbnail(url=ctx.guild.icon.url)

    try:
        await target_channel.send(content=mention_str, embed=embed, allowed_mentions=discord.AllowedMentions(everyone=True, roles=True, users=True))
        try: await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound): pass
        if target_channel.id != ctx.channel.id: await ctx.send(f"✅ Announcement dispatched to {target_channel.mention}.", delete_after=5)
    except discord.HTTPException as e:
        await ctx.send(f"⚠️ Failed to send announcement: `{e}`", delete_after=8)

@bot.command(name="purge")
@is_purge_authorized()
async def purge(ctx: commands.Context, amount: int = 10, target: Optional[Union[discord.Member, str]] = None):
    if amount < 1 or amount > 1000: 
        return await ctx.send("⚠️ Specify a message count between 1 and 1,000.", delete_after=5)
        
    try: 
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException): 
        pass

    def purge_check(m: discord.Message) -> bool:
        if m.pinned: return False
        if isinstance(target, discord.Member): 
            return m.author.id == target.id
        elif isinstance(target, str):
            t_lower = target.lower()
            if t_lower in ["bot", "bots"]: return m.author.bot
            if t_lower in ["link", "links"]: 
                return bool(INVITE_REGEX.search(m.content) or "http://" in m.content.lower() or "https://" in m.content.lower())
        return True

    status_msg = await ctx.send(f"🧹 **Purging messages...**")
    
    deleted = await ctx.channel.purge(limit=amount, check=purge_check, bulk=True)
    
    try: 
        await status_msg.delete()
    except discord.NotFound: 
        pass
        
    await ctx.send(f"🧹 Successfully cleared **{len(deleted)}** message(s).", delete_after=5)

@bot.command(name="clean_start", aliases=["clear_notifications", "clear_notifs", "clearnotifications"])
@commands.has_permissions(administrator=True)
async def cmd_clean_start(ctx: commands.Context):
    status_msg = await ctx.send("🧹 **Executing Clean Start: Purging all previous bot notifications, alerts, and stale panels...**")
    await clear_all_bot_notifications(ctx.guild)
    await deploy_all_system_panels(ctx.guild, bot.command_prefix)
    await status_msg.edit(content="✨ **Clean Start Complete! All stale bot notifications wiped and fresh panels deployed.**")

@bot.command(name="setup_nicknames", aliases=["deploy_nicknames", "nickname_panel"])
@commands.has_permissions(administrator=True)
async def cmd_setup_nicknames(ctx: commands.Context):
    await deploy_nickname_panel(ctx.guild)
    await ctx.send("✅ Nickname changer panel deployed to `#🏷️・change-nickname`!", delete_after=5)

@bot.command(name="deploy_panels", aliases=["setup_all_panels", "run_all_panels"])
@commands.has_permissions(administrator=True)
async def cmd_deploy_all_panels(ctx: commands.Context):
    status_msg = await ctx.send("🔄 **Deploying all system panels across the server...**")
    await deploy_all_system_panels(ctx.guild, bot.command_prefix)
    await status_msg.edit(content="✅ **All system panels have been successfully deployed and verified!**")

@bot.command(name="setup_channels")
@commands.has_permissions(administrator=True)
async def setup_channels(ctx: commands.Context):
    status_msg = await ctx.send("🔍 **Analyzing live structure to guarantee zero duplicates or overwrites...**")
    created_channels, _ = await bot._provision_blueprint_and_roles(ctx.guild)
    await get_or_create_memory_channel(ctx.guild)
    await get_or_create_audit_channel(ctx.guild)
    await get_or_create_testing_channel(ctx.guild)
    await enforce_admin_area_security(ctx.guild)
    embed = discord.Embed(title="✅ Server Blueprint Checked & Synced", description=f"**Safe Provisioning Complete:**\n\n• **New Channels Created:** `{created_channels}`\n• **Admin Area Security:** Strictly Supreme Leader, Highness & Arkbot only\n\n*Zero existing channels or configurations were modified, overwritten, or duplicated.*", color=discord.Color.green(), timestamp=discord.utils.utcnow())
    await status_msg.edit(content=None, embed=embed)

@bot.command(name="setup_roles")
@commands.has_permissions(administrator=True)
async def setup_roles(ctx: commands.Context):
    status_msg = await ctx.send("⚙️ **Checking server roles... Skips existing to prevent duplicates/overwrites.**")
    _, created_roles = await bot._provision_blueprint_and_roles(ctx.guild)
    await status_msg.edit(content=f"✅ **Role Sync Complete:** Created **{created_roles}** missing role(s). Preserved all existing role(s).")

@bot.command(name="setup_birthdays", aliases=["deploy_birthdays", "birthday_panel"])
@commands.has_permissions(administrator=True)
async def cmd_setup_birthdays(ctx: commands.Context):
    await deploy_birthday_panel(ctx.guild)
    await ctx.send("✅ Interactive birthday registration panel deployed to `#🎂・birthdays`!", delete_after=5)

@bot.command(name="colours", aliases=["colors", "setup_colours"])
@commands.has_permissions(administrator=True)
async def cmd_colours(ctx: commands.Context):
    await deploy_colours_panel(ctx.guild)
    await ctx.send("✅ Cosmetic colours panel deployed to `#🎨・colours` (Zero notifications attached)!", delete_after=5)

@bot.command(name="setup_confession_panel")
@commands.has_permissions(administrator=True)
async def cmd_setup_confession(ctx: commands.Context):
    await deploy_confession_panel(ctx.guild)
    await ctx.send("✅ Anonymous confession panel deployed to `#🚦・confession`!", delete_after=5)

@bot.command(name="setup_notifications", aliases=["setup_pings"])
@commands.has_permissions(administrator=True)
async def cmd_notifications(ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
    await deploy_notifications_panel(ctx.guild, channel or ctx.channel)
    await ctx.send("✅ Notification panel deployed!", delete_after=5)

@bot.command(name="setup_tickets")
@commands.has_permissions(administrator=True)
async def setup_tickets(ctx: commands.Context):
    await deploy_tickets_panel(ctx.guild)
    await ctx.send("✅ Support & Application panel deployed to `🎫・tickets`!", delete_after=5)

@bot.command(name="refresh_rules")
@commands.has_permissions(administrator=True)
async def refresh_rules(ctx: commands.Context):
    await deploy_team_rules_panel(ctx.guild)
    await deploy_team_news_commands_panel(ctx.guild, bot.command_prefix)
    await ctx.send("✅ **Team rules updated in `🛡️・team-rules` and command directory posted in `🚨・team-news`!**", delete_after=5)

@bot.command(name="refresh_commands", aliases=["refresh_bot_commands"])
@commands.has_permissions(administrator=True)
async def refresh_commands(ctx: commands.Context):
    await deploy_bot_commands_panel(ctx.guild, bot.command_prefix)
    await ctx.send("✅ **Master bot command manual refreshed in `💼・bot-commands`!**", delete_after=5)

@bot.command(name="admin_panel", aliases=["staff_panel", "dashboard"])
@commands.has_permissions(administrator=True)
async def spawn_admin_panel(ctx: commands.Context):
    embed = discord.Embed(
        title="🛡️ Executive Admin Dashboard", 
        description="Use the dropdown below to select any member in the server and force-edit their Nickname, XP, or Status.", 
        color=discord.Color.dark_red()
    )
    await ctx.send(embed=embed, view=AdminControlPanelView())
    try: 
        await ctx.message.delete()
    except: 
        pass

@bot.command(name="restore_xp_from_roles", aliases=["recover_xp"])
@commands.has_permissions(administrator=True)
async def restore_xp_from_roles(ctx: commands.Context):
    status_msg = await ctx.send("🔄 **Scanning members to restore XP based on existing rank roles...**")
    
    restored_count = 0
    total_xp_restored = 0
    
    sorted_tiers = sorted(LEVEL_TIERS, key=lambda x: x[0], reverse=True)
    
    for member in ctx.guild.members:
        if member.bot: 
            continue
            
        highest_level = 0
        member_role_names = {r.name for r in member.roles}
        
        for min_lvl, r_name in sorted_tiers:
            if r_name in member_role_names:
                highest_level = min_lvl
                break
                
        if highest_level > 0:
            base_xp = xp_for_level(highest_level)
            current_xp = await get_user_xp(member.id)
            
            if current_xp < base_xp:
                await set_user_xp(member.id, base_xp)
                restored_count += 1
                total_xp_restored += (base_xp - current_xp)

    await flush_xp_cache()
    
    embed = discord.Embed(
        title="✅ XP Recovery Complete",
        description=(
            f"Successfully restored lost XP by scanning member tier roles.\n\n"
            f"• **Members Recovered:** `{restored_count}`\n"
            f"• **Total XP Restored:** `{total_xp_restored:,} XP`\n\n"
            f"*Members were granted the baseline XP required to hold their current rank.*"
        ),
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text=f"Disaster Recovery initiated by {ctx.author.display_name}")
    await status_msg.edit(content=None, embed=embed)

@bot.command(name="afk")
async def afk(ctx: commands.Context, *, reason: Optional[str] = None):
    selected_status = reason.strip() if reason else random.choice(AFK_PRESET_MESSAGES)
    AFK_USERS[ctx.author.id] = {"reason": selected_status, "time": discord.utils.utcnow()}
    await persist_runtime_state()
    embed = discord.Embed(description=f"🌙 **{ctx.author.display_name} is now AFK**\n*{selected_status}*", color=discord.Color.purple())
    await ctx.send(embed=embed, delete_after=10)
    try: await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException): pass

@bot.command(name="backup_all")
@commands.has_permissions(administrator=True)
async def backup_all(ctx: commands.Context):
    status_msg = await ctx.send("🔄 **Generating single master backup & overwriting previous snapshots...**")
    payload = await generate_unified_backup_payload(ctx.guild)
    await safe_write_json(MASTER_BACKUP_TEMPLATE.format(guild_id=ctx.guild.id), payload)

    file_stream = io.BytesIO(json.dumps(payload, indent=4).encode("utf-8"))
    embed = discord.Embed(
        title="🔒 Single Master Backup Overwritten",
        description=f"Successfully archived all server systems into one master file:\n• **Categories & Channels:** `{len(payload['categories'])}`\n• **Blueprint Layouts:** Synchronized\n• **User XP Profiles:** `{len(payload['user_xp'])}`\n• **Birthdays Recorded:** `{len(payload['user_birthdays'])}`\n• **Confessions Stored:** `{len(payload['confessions'].get('entries', []))}`\n\n*Previous backups cleared. This is now the sole recovery point.*",
        color=discord.Color.blue(), timestamp=discord.utils.utcnow(),
    )
    await status_msg.delete()
    await ctx.send(embed=embed, file=discord.File(file_stream, filename=f"master_backup_{ctx.guild.id}.json"))

    err_channel = discord.utils.get(ctx.guild.text_channels, name="🩸・bot-errors") or discord.utils.get(ctx.guild.text_channels, name="bot-errors")
    if err_channel:
        await purge_all_old_backups(err_channel)
        file_stream.seek(0)
        await err_channel.send(content="🔒 **Master System Backup (Single Instance)**", file=discord.File(file_stream, filename=f"master_backup_{ctx.guild.id}.json"))

@bot.command(name="restore_all")
@commands.has_permissions(administrator=True)
async def restore_all(ctx: commands.Context):
    status_msg = await ctx.send("🔄 **Scanning for single master backup source...**")
    backup_data, source_description = None, ""

    if ctx.message.attachments and ctx.message.attachments[0].filename.endswith(".json"):
        try:
            content = await ctx.message.attachments[0].read()
            backup_data, source_description = json.loads(content.decode("utf-8")), f"Uploaded File `{ctx.message.attachments[0].filename}`"
        except Exception as e: return await status_msg.edit(content=f"⚠️ Failed to parse attached JSON: `{e}`")

    if not backup_data:
        err_channel = discord.utils.get(ctx.guild.text_channels, name="🩸・bot-errors") or discord.utils.get(ctx.guild.text_channels, name="bot-errors")
        if err_channel:
            await status_msg.edit(content="🔍 **Searching master snapshot in `🩸・bot-errors`...**")
            async for msg in err_channel.history(limit=50):
                if msg.author == ctx.guild.me and msg.attachments:
                    for att in msg.attachments:
                        if att.filename.endswith(".json"):
                            try:
                                content = await att.read()
                                backup_data, source_description = json.loads(content.decode("utf-8")), f"Discord Master Snapshot `{att.filename}`"
                                break
                            except Exception: continue
                if backup_data: break

    if not backup_data:
        local_path = MASTER_BACKUP_TEMPLATE.format(guild_id=ctx.guild.id)
        if backup_data := await safe_read_json(local_path, None): source_description = f"Local Master File `{local_path}`"

    if not backup_data: return await status_msg.edit(content="⚠️ **No master backup found!** Either attach a `.json` backup file or ensure one exists in `🩸・bot-errors`.")

    await status_msg.edit(content=f"🔄 **Restoring system from {source_description}...**")
    stats = await apply_unified_restore(ctx.guild, backup_data)
    await bot._provision_blueprint_and_roles(ctx.guild)
    await clear_all_bot_notifications(ctx.guild)
    await deploy_all_system_panels(ctx.guild, bot.command_prefix)

    fresh_payload = await generate_unified_backup_payload(ctx.guild)
    await safe_write_json(MASTER_BACKUP_TEMPLATE.format(guild_id=ctx.guild.id), fresh_payload)
    err_channel = discord.utils.get(ctx.guild.text_channels, name="🩸・bot-errors") or discord.utils.get(ctx.guild.text_channels, name="bot-errors")
    if err_channel:
        await purge_all_old_backups(err_channel)
        file_stream = io.BytesIO(json.dumps(fresh_payload, indent=4).encode("utf-8"))
        await err_channel.send(content="🔒 **Master System Backup (Overwritten Post-Restore & Clean Start)**", file=discord.File(file_stream, filename=f"master_backup_{ctx.guild.id}.json"))

    embed = discord.Embed(
        title="✅ System Restored & Clean Start Completed",
        description=f"Restoration from **{source_description}** complete:\n\n• **Missing Channels Rebuilt:** `{stats['channels_created']}`\n• **Missing Permissions Applied:** `{stats['perms_applied']}`\n• **User XP Profiles Synchronized:** `{stats['xp_users']}`\n• **Birthdays Restored:** `{stats['birthdays']}`\n• **Confessions Restored:** `{stats['confessions']}`\n• **Clean Start:** Stale alerts purged & fresh UI panels deployed\n• **Admin Area Security:** Strictly Supreme Leader, Highness & Arkbot only\n\n*The single master backup has been overwritten with current verified server state.*",
        color=discord.Color.green(), timestamp=discord.utils.utcnow(),
    )
    await status_msg.edit(content=None, embed=embed)

@bot.command(name="maintenance")
@commands.has_permissions(administrator=True)
async def maintenance_toggle(ctx: commands.Context, state: Optional[str] = None):
    global MAINTENANCE_MODE
    if state is None: MAINTENANCE_MODE = not MAINTENANCE_MODE
    elif state.lower() in ["on", "enable", "true"]: MAINTENANCE_MODE = True
    elif state.lower() in ["off", "disable", "false"]: MAINTENANCE_MODE = False
    elif state.lower() == "status": pass
    else: return await ctx.send("⚠️ Usage: `.maintenance [on/off/status]`", delete_after=5)

    await persist_runtime_state()
    embed = discord.Embed(
        title="🛠️ Maintenance Mode Status",
        description=f"Maintenance state is currently: {'🔴 **ENABLED** (Commands locked to High Command only)' if MAINTENANCE_MODE else '🟢 **DISABLED** (All commands active)'}",
        color=discord.Color.red() if MAINTENANCE_MODE else discord.Color.green(), timestamp=discord.utils.utcnow(),
    )
    await ctx.send(embed=embed)

@bot.command(name="shutdown")
@commands.has_permissions(administrator=True)
async def shutdown(ctx: commands.Context, *, reason: str = "Scheduled system maintenance and upgrade."):
    confirm_msg = await ctx.send("⚠️ **Initiating Maintenance Shutdown Protocol...**\n• Flushing database states to disk\n• Archiving single master backup\n• Shutting down runtime process...")
    try: await bot.change_presence(status=discord.Status.dnd, activity=discord.Game(name="⚠️ System Shutting Down"))
    except Exception: pass

    await persist_runtime_state()
    await flush_xp_cache()

    for guild in bot.guilds:
        try:
            payload = await generate_unified_backup_payload(guild)
            await safe_write_json(MASTER_BACKUP_TEMPLATE.format(guild_id=guild.id), payload)
            err_channel = discord.utils.get(guild.text_channels, name="🩸・bot-errors") or discord.utils.get(guild.text_channels, name="bot-errors")
            if err_channel:
                await purge_all_old_backups(err_channel)
                file_stream = io.BytesIO(json.dumps(payload, indent=4).encode("utf-8"))
                shutdown_embed = discord.Embed(title="🛑 SYSTEM MAINTENANCE SHUTDOWN", description=f"**Authorized by:** {ctx.author.mention}\n**Reason:** *{reason}*\n\n🔒 **Pre-Shutdown Single Master Backup Attached.**\nAll runtime states, XP databases, channel configurations, and birthdays have been preserved.\nThe bot process is now disconnecting from Discord.", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
                shutdown_embed.set_footer(text="Arkbot Architecture Shutdown Engine")
                await err_channel.send(embed=shutdown_embed, file=discord.File(file_stream, filename=f"master_backup_{guild.id}.json"))
        except Exception as e: print(f"[Maintenance Shutdown Error] Guild {guild.id}: {e}")

    final_embed = discord.Embed(title="🛑 Process Termination Completed", description="✅ Single master snapshot archived to disk.\n✅ Clean master backup uploaded to `🩸・bot-errors`.\n🔌 Disconnecting gateway and exiting process now.", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    await confirm_msg.edit(content=None, embed=final_embed)

    if hourly_backup_task.is_running(): hourly_backup_task.cancel()
    if birthday_announcer_task.is_running(): birthday_announcer_task.cancel()
    if xp_drop_task.is_running(): xp_drop_task.cancel()
    if xp_flush_task.is_running(): xp_flush_task.cancel()

    await asyncio.sleep(1.0)
    await bot.close()
    sys.exit(0)

# ==============================================================================
# RUN BOT
# ==============================================================================
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN: print("⚠️ CRITICAL ERROR: 'DISCORD_BOT_TOKEN' environment variable is missing!")
    else: bot.run(TOKEN)
