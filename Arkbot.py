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

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️ [AI Engine] 'google-genai' not installed. Run: pip install google-genai")

# ==============================================================================
# BOT SETUP, INTENTS & AI ENGINE
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

UPDATE_NOTIFIED = False
MAINTENANCE_MODE = False
AI_ENABLED = True

STATE_FILE = "bot_runtime_state.json"
XP_DATABASE_FILE = "user_xp.json"
BIRTHDAYS_FILE = "birthdays.json"
CONFESSIONS_FILE = "confessions.json"
MASTER_BACKUP_TEMPLATE = "master_backup_{guild_id}.json"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ai_client = genai.Client(api_key=GEMINI_API_KEY) if (GENAI_AVAILABLE and GEMINI_API_KEY) else None
AI_MODEL = "gemini-2.5-flash"
AI_BETA_MODEL = "gemini-2.5-pro"

AI_CHANNELS = {"🍸・chat-ai", "chat-ai", "✨・chat-ai-beta", "chat-ai-beta"}
AI_CHAT_HISTORY: Dict[int, deque] = defaultdict(lambda: deque(maxlen=16))
AI_USER_COOLDOWNS: Dict[int, float] = {}
AI_COOLDOWN_SECONDS = 5.0

AI_SYSTEM_PROMPT = (
    "You are Arkbot AI, the witty, warm, and intelligent community companion for the 'Chill-Verse' Discord server. "
    "Keep responses engaging, teen-friendly, and concise. Engineered by iamthesubhanahmed (Tier3.pk)."
)

async def ai_dynamic_text(task_prompt: str, fallback: str) -> str:
    """Generates dynamic one-line preset messages via AI instead of hardcoded lists."""
    if not AI_ENABLED or not ai_client:
        return fallback
    try:
        resp = await ai_client.aio.models.generate_content(
            model=AI_MODEL,
            contents=task_prompt,
            config=types.GenerateContentConfig(
                system_instruction="You write short, vivid 1-sentence Discord server messages with 1-2 emojis. Output ONLY the message text, no quotes.",
                temperature=0.9,
                max_output_tokens=80,
            ),
        )
        return (resp.text or "").strip().strip('"') or fallback
    except Exception:
        return fallback

async def generate_ai_reply(channel_id: int, user_name: str, prompt_text: str, use_beta: bool = False) -> str:
    if not AI_ENABLED:
        return "⚠️ **AI Engine is currently paused** by server administrators."
    if not ai_client:
        return "⚠️ **AI Engine Offline:** Ensure `GEMINI_API_KEY` is set and `google-genai` is installed."

    history = AI_CHAT_HISTORY[channel_id]
    formatted_input = f"{user_name}: {prompt_text}"
    contents = [types.Content(role=r, parts=[types.Part.from_text(text=t)]) for r, t in history]
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=formatted_input)]))

    try:
        response = await ai_client.aio.models.generate_content(
            model=AI_BETA_MODEL if use_beta else AI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=AI_SYSTEM_PROMPT,
                temperature=0.75,
                max_output_tokens=1024,
            ),
        )
        reply = (response.text or "").strip() or "🤔 I couldn't come up with a response for that. Try rephrasing!"
        history.append(("user", formatted_input))
        history.append(("model", reply))
        return reply
    except Exception as e:
        return f"⚠️ **AI Generation Error:** `{type(e).__name__}` — Please try again shortly."

# ==============================================================================
# CACHES, CONSTANTS & BLUEPRINT
# ==============================================================================
AFK_USERS: Dict[int, Dict[str, Any]] = {}
LAST_BUMP_TIME: Optional[datetime.datetime] = None
BUMP_TIMER_TASK: Optional[asyncio.Task] = None
BUMP_LOCK = asyncio.Lock()
BUMP_COOLDOWN_SECONDS = 7200
ANNOUNCED_BIRTHDAYS_TODAY: List[int] = []
REMINDED_BIRTHDAYS_TOMORROW: List[int] = []

LAST_REVIVE_TIME: Dict[int, float] = {}
REVIVE_COOLDOWN_SECONDS = 2700

XP_CACHE: Dict[str, int] = {}
XP_CACHE_DIRTY = False

CHANNEL_CHAT_ACTIVITY: Dict[int, deque] = defaultdict(lambda: deque(maxlen=50))
SUPER_DROP_COOLDOWNS: Dict[int, float] = {}
SUPER_DROP_COOLDOWN_SECONDS = 14400

USER_MESSAGE_TIMESTAMPS: Dict[int, deque] = defaultdict(lambda: deque(maxlen=10))
USER_CHAT_XP_COOLDOWN: Dict[int, float] = {}
INVITE_REGEX = re.compile(r"(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discord(?:app)?\.com/invite)/[a-zA-Z0-9_-]+", re.IGNORECASE)

SYSTEM_CHANNELS = {"bot-memory", "📜・audit-logs", "audit-logs", "🩸・bot-errors", "bot-errors", "🧪・bot-testing", "bot-testing", "📢・discord-news", "discord-news"}

LEVEL_TIERS: List[Tuple[int, str]] = [
    (60, "Sovereign (Levels 60-70)"), (50, "Legend (Levels 50-59)"), (40, "Champion (Levels 40-49)"),
    (30, "Elite (Levels 30-39)"), (20, "Vanguard (Levels 20-29)"), (10, "Explorer (Levels 10-19)"), (1, "Newbie (Levels 1-9)"),
]
COLOR_ROLES = ["Red", "Yellow", "Green", "Blue", "Orange", "Pink"]

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
# ASYNC STORAGE & LEVELING ENGINE
# ==============================================================================
FILE_LOCKS: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

def _read_file_sync(path: str, default: Any) -> Any:
    if not os.path.exists(path): return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def _write_file_sync(path: str, data: Any) -> None:
    temp_path = f"{path}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)
        os.replace(temp_path, path)
    except Exception as e:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except OSError: pass
        print(f"[Storage Engine] Failed writing {path}: {e}")

async def safe_read_json(path: str, default: Any) -> Any:
    async with FILE_LOCKS[path]: return await asyncio.to_thread(_read_file_sync, path, default)

async def safe_write_json(path: str, data: Any) -> None:
    async with FILE_LOCKS[path]: return await asyncio.to_thread(_write_file_sync, path, data)

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

async def modify_user_xp(user_id: int, amount: int, mode: str = "add") -> Tuple[int, int]:
    global XP_CACHE_DIRTY
    uid = str(user_id)
    prev_xp = XP_CACHE.get(uid, 0)
    if mode == "add": new_xp = prev_xp + amount
    elif mode == "remove": new_xp = max(0, prev_xp - amount)
    else: new_xp = max(0, amount)
    XP_CACHE[uid] = new_xp
    XP_CACHE_DIRTY = True
    return prev_xp, new_xp

def calculate_level(xp: int) -> int:
    return int((xp / 75) ** 0.5) if xp > 0 else 0

def xp_for_level(level: int) -> int:
    return int(75 * (level ** 2))

async def load_birthdays() -> Dict[str, str]: return await safe_read_json(BIRTHDAYS_FILE, {})
async def save_birthdays(data: Dict[str, str]) -> None: await safe_write_json(BIRTHDAYS_FILE, data)

async def record_confession(user_id: int, content: str) -> int:
    data = await safe_read_json(CONFESSIONS_FILE, {"last_id": 0, "entries": []})
    new_id = data.get("last_id", 0) + 1
    data["last_id"] = new_id
    if not isinstance(data.get("entries"), list): data["entries"] = []
    data["entries"].append({"id": new_id, "user_id": user_id, "content": content, "timestamp": discord.utils.utcnow().isoformat()})
    await safe_write_json(CONFESSIONS_FILE, data)
    return new_id

async def persist_runtime_state():
    state = {
        "last_bump_time": LAST_BUMP_TIME.timestamp() if LAST_BUMP_TIME else None,
        "afk_users": {str(uid): {"reason": info["reason"], "time": info["time"].isoformat()} for uid, info in AFK_USERS.items()},
        "announced_birthdays_today": ANNOUNCED_BIRTHDAYS_TODAY,
        "reminded_birthdays_tomorrow": REMINDED_BIRTHDAYS_TOMORROW,
        "maintenance_mode": MAINTENANCE_MODE,
        "ai_enabled": AI_ENABLED,
    }
    await safe_write_json(STATE_FILE, state)

async def restore_runtime_state():
    global LAST_BUMP_TIME, AFK_USERS, ANNOUNCED_BIRTHDAYS_TODAY, REMINDED_BIRTHDAYS_TOMORROW, MAINTENANCE_MODE, AI_ENABLED
    state = await safe_read_json(STATE_FILE, {})
    if not state: return
    if raw_ts := state.get("last_bump_time"):
        LAST_BUMP_TIME = datetime.datetime.fromtimestamp(raw_ts, datetime.timezone.utc)
    AFK_USERS.clear()
    for uid_str, data in state.get("afk_users", {}).items():
        try: AFK_USERS[int(uid_str)] = {"reason": data.get("reason", "AFK"), "time": datetime.datetime.fromisoformat(data["time"])}
        except Exception: continue
    ANNOUNCED_BIRTHDAYS_TODAY = state.get("announced_birthdays_today", [])
    REMINDED_BIRTHDAYS_TOMORROW = state.get("reminded_birthdays_tomorrow", [])
    MAINTENANCE_MODE = state.get("maintenance_mode", False)
    AI_ENABLED = state.get("ai_enabled", True)

async def sync_member_level_roles(member: discord.Member, new_xp: int) -> Optional[discord.Role]:
    guild, current_lvl = member.guild, calculate_level(new_xp)
    target_tier_name = next((r_name for min_lvl, r_name in LEVEL_TIERS if current_lvl >= min_lvl), None)
    target_role = discord.utils.get(guild.roles, name=target_tier_name) if target_tier_name else None
    tier_role_names = {r_name for _, r_name in LEVEL_TIERS}
    to_remove = [r for r in member.roles if r.name in tier_role_names and r != target_role and r < guild.me.top_role]
    try:
        if to_remove: await member.remove_roles(*to_remove, reason="Level Tier Recalibration")
        if target_role and target_role not in member.roles and target_role < guild.me.top_role:
            await member.add_roles(target_role, reason=f"Level Tier Sync (Level {current_lvl})")
    except (discord.Forbidden, discord.HTTPException): pass
    return target_role

async def handle_level_up(member: discord.Member, prev_xp: int, new_xp: int, fallback_ch: Optional[discord.abc.Messageable] = None):
    old_lvl, new_lvl = calculate_level(prev_xp), calculate_level(new_xp)
    if new_lvl <= old_lvl: return
    unlocked_role = await sync_member_level_roles(member, new_xp)
    lvl_channel = discord.utils.get(member.guild.text_channels, name="📢・level-announcements") or fallback_ch
    if lvl_channel and hasattr(lvl_channel, "send"):
        ai_congrats = await ai_dynamic_text(
            f"Write an hyped 1-sentence level-up congratulations for {member.display_name} reaching Level {new_lvl} in Chill-Verse!",
            f"Congratulations {member.mention}! You leveled up from **Level {old_lvl}** to **Level {new_lvl}**!"
        )
        embed = discord.Embed(title="🎊 LEVEL UP! 🎊", description=ai_congrats, color=discord.Color.gold(), timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Total XP", value=f"**{new_xp:,} XP**", inline=True)
        embed.add_field(name="Current Level", value=f"**Level {new_lvl}**", inline=True)
        if unlocked_role: embed.add_field(name="⭐ New Rank Unlocked", value=f"**{unlocked_role.mention}**", inline=False)
        embed.add_field(name="Next Level At", value=f"`{xp_for_level(new_lvl + 1):,} XP`", inline=False)
        try: await lvl_channel.send(content=f"🎉 {member.mention} just hit **Level {new_lvl}**!", embed=embed)
        except (discord.HTTPException, discord.Forbidden): pass

# ==============================================================================
# AUTHORITY CHECKS & SYSTEM CHANNEL HELPERS
# ==============================================================================
def has_high_command_access(member: Union[discord.Member, discord.User], guild: Optional[discord.Guild]) -> bool:
    if not guild or not isinstance(member, discord.Member): return False
    if member.id == guild.owner_id or getattr(member.guild_permissions, "administrator", False): return True
    return bool({"supreme leader", "highness", "authority"}.intersection({r.name.lower().strip() for r in getattr(member, "roles", [])}))

def is_authority_holder():
    async def predicate(ctx: commands.Context):
        if has_high_command_access(ctx.author, ctx.guild): return True
        raise commands.CheckFailure("⛔ **Restricted:** Only Administrators and Authority holders can execute this command.")
    return commands.check(predicate)

def is_team_authorized():
    async def predicate(ctx: commands.Context):
        if ctx.guild and is_team_member(ctx.author): return True
        raise commands.CheckFailure("⛔ **Restricted:** Only Staff Team members can execute this command.")
    return commands.check(predicate)

def can_moderate(ctx: commands.Context, target: discord.Member) -> bool:
    if target.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id: return False
    if target.top_role >= ctx.guild.me.top_role or target.id in (ctx.guild.owner_id, ctx.author.id): return False
    return True

def is_team_member(member: Union[discord.Member, discord.User]) -> bool:
    if not isinstance(member, discord.Member): return False
    if getattr(member.guild_permissions, "administrator", False): return True
    team_roles = {"supreme leader", "highness", "authority", "head moderator", "moderator", "trial mod", "chill-verse team"}
    return bool(team_roles.intersection({r.name.lower().strip() for r in getattr(member, "roles", [])}))

async def resolve_guild_context(interaction: discord.Interaction) -> Optional[discord.Guild]:
    if interaction.guild: return interaction.guild
    for g in interaction.client.guilds:
        if g.get_member(interaction.user.id): return g
        try:
            if await g.fetch_member(interaction.user.id): return g
        except (discord.NotFound, discord.HTTPException): continue
    return None

def normalize_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", name).lower()

async def enforce_admin_area_security(guild: discord.Guild):
    admin_cat = discord.utils.get(guild.categories, name="Admin Area 🔒")
    if not admin_cat: return
    strict_overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, embed_links=True, manage_channels=True, manage_permissions=True, attach_files=True),
    }
    for r_name in ("Supreme Leader", "Highness"):
        if role := discord.utils.get(guild.roles, name=r_name):
            strict_overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    try:
        for target in list(admin_cat.overwrites.keys()):
            if target not in strict_overwrites: await admin_cat.set_permissions(target, overwrite=None)
        await admin_cat.edit(overwrites=strict_overwrites)
        for ch in admin_cat.channels:
            for target in list(ch.overwrites.keys()):
                if target not in strict_overwrites: await ch.set_permissions(target, overwrite=None)
            await ch.edit(overwrites=strict_overwrites)
    except Exception: pass

async def get_or_create_system_channel(guild: discord.Guild, primary_name: str, alt_name: str, in_admin_cat: bool = True) -> discord.TextChannel:
    ch = discord.utils.get(guild.text_channels, name=primary_name) or discord.utils.get(guild.text_channels, name=alt_name)
    if ch: return ch
    admin_cat = discord.utils.get(guild.categories, name="Admin Area 🔒") if in_admin_cat else None
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, embed_links=True, attach_files=True, manage_channels=True),
    }
    for rname in ("Supreme Leader", "Highness"):
        if r := discord.utils.get(guild.roles, name=rname):
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    return await guild.create_text_channel(name=primary_name, category=admin_cat, overwrites=overwrites, reason="System Channel Provisioning")

# ==============================================================================
# BACKUP, RESTORE & CLEAN START ENGINE
# ==============================================================================
async def find_latest_backup_from_discord(guild: discord.Guild) -> Optional[Dict[str, Any]]:
    for ch_name in ("🩸・bot-errors", "bot-errors", "bot-memory"):
        if ch := discord.utils.get(guild.text_channels, name=ch_name):
            try:
                async for msg in ch.history(limit=50):
                    if msg.author == guild.me and msg.attachments:
                        for att in msg.attachments:
                            if att.filename.endswith(".json"):
                                data = json.loads((await att.read()).decode("utf-8"))
                                if isinstance(data, dict) and ("user_xp" in data or "categories" in data): return data
            except Exception: pass
    return None

async def purge_all_old_backups(channel: discord.TextChannel):
    try:
        async for msg in channel.history(limit=100):
            if msg.author == channel.guild.me and (any(a.filename.endswith(".json") for a in msg.attachments) or "backup" in msg.content.lower() or "snapshot" in msg.content.lower()):
                try:
                    await msg.delete()
                    await asyncio.sleep(0.3)
                except (discord.NotFound, discord.HTTPException): pass
    except Exception: pass

async def clear_all_bot_notifications(guild: discord.Guild):
    wipe_names = ["🚨・team-news", "team-news", "⏰・bump", "bump", "🧪・bot-testing", "bot-testing", "💼・bot-commands", "bot-commands", "🛡️・team-rules", "team-rules", "🛡️・server-rules", "server-rules", "🎨・colours", "colours", "🎫・tickets", "tickets", "🏷️・change-nickname", "change-nickname"]
    for ch_name in wipe_names:
        if ch := discord.utils.get(guild.text_channels, name=ch_name):
            try:
                await ch.purge(limit=100, check=lambda m: m.author == guild.me)
                await asyncio.sleep(0.2)
            except (discord.Forbidden, discord.HTTPException): pass

    targeted_panels = [
        (["🚦・confession", "confessions"], ["Confession Box"]),
        (["🎂・birthdays", "birthdays"], ["Birthday Calendar & Registration", "UPCOMING BIRTHDAY ALERT", "HAPPY BIRTHDAY"]),
        (["📢・announcements", "announcements"], ["Community Notification Preferences"]),
    ]
    for names, titles in targeted_panels:
        ch = next((discord.utils.get(guild.text_channels, name=n) for n in names if discord.utils.get(guild.text_channels, name=n)), None)
        if ch:
            try:
                async for msg in ch.history(limit=50):
                    if msg.author == guild.me and msg.embeds and any(kw in (msg.embeds[0].title or "") for kw in titles):
                        await msg.delete()
                        await asyncio.sleep(0.2)
            except (discord.Forbidden, discord.HTTPException): pass

async def generate_unified_backup_payload(guild: discord.Guild) -> Dict[str, Any]:
    await flush_xp_cache()
    categories_data, current_blueprint = [], []
    for cat in guild.categories:
        cat_ow = {str(t.id): {"name": t.name, "type": "role" if isinstance(t, discord.Role) else "member", "allow": ow.pair()[0].value, "deny": ow.pair()[1].value} for t, ow in cat.overwrites.items()}
        cat_entry = {"name": cat.name, "position": cat.position, "overwrites": cat_ow, "channels": []}
        cat_bp = {"category": cat.name, "channels": []}
        for ch in cat.channels:
            ch_ow = {str(t.id): {"name": t.name, "type": "role" if isinstance(t, discord.Role) else "member", "allow": ow.pair()[0].value, "deny": ow.pair()[1].value} for t, ow in ch.overwrites.items()}
            cat_entry["channels"].append({"name": ch.name, "type": str(ch.type), "position": ch.position, "user_limit": getattr(ch, "user_limit", 0), "overwrites": ch_ow})
            if ch.name not in SYSTEM_CHANNELS:
                ch_type = "voice" if isinstance(ch, discord.VoiceChannel) else ("forum" if isinstance(ch, getattr(discord, "ForumChannel", ())) else "text")
                def_ow = ch.overwrites.get(guild.default_role)
                is_rest = (def_ow.view_channel is False) if def_ow else (cat.name in ["Team Area", "Admin Area 🔒"])
                is_ro = (def_ow.send_messages is False) if def_ow else False
                item = {"name": ch.name, "type": ch_type, "restricted": is_rest, "read_only": is_ro}
                if ch_type == "voice" and getattr(ch, "user_limit", 0) > 0: item["user_limit"] = ch.user_limit
                cat_bp["channels"].append(item)
        categories_data.append(cat_entry)
        if cat_bp["channels"]: current_blueprint.append(cat_bp)

    return {
        "guild_id": guild.id, "guild_name": guild.name, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "categories": categories_data, "blueprint": current_blueprint,
        "roles": [{"name": r.name, "permissions": r.permissions.value, "color": r.color.value, "hoist": r.hoist} for r in guild.roles if not r.is_default() and not r.managed],
        "user_xp": XP_CACHE.copy(), "user_birthdays": await load_birthdays(),
        "confessions": await safe_read_json(CONFESSIONS_FILE, {"last_id": 0, "entries": []}),
        "last_bump_time": LAST_BUMP_TIME.timestamp() if LAST_BUMP_TIME else None,
    }

async def apply_unified_restore(guild: discord.Guild, data: Dict[str, Any]) -> Dict[str, int]:
    global SERVER_BLUEPRINT, LAST_BUMP_TIME, XP_CACHE, XP_CACHE_DIRTY
    stats = {"channels_created": 0, "perms_applied": 0, "perms_skipped": 0, "xp_users": 0, "birthdays": 0, "confessions": 0}
    if isinstance(data.get("blueprint"), list): SERVER_BLUEPRINT = data["blueprint"]
    if raw_xp := data.get("user_xp"):
        for uid, val in raw_xp.items():
            try: XP_CACHE[str(uid)] = max(XP_CACHE.get(str(uid), 0), int(val))
            except (ValueError, TypeError): continue
        XP_CACHE_DIRTY = True
        stats["xp_users"] = len(raw_xp)
        await flush_xp_cache()
        for uid_str, xp_val in XP_CACHE.items():
            if member := guild.get_member(int(uid_str)): await sync_member_level_roles(member, xp_val)

    if raw_bdays := data.get("user_birthdays"):
        curr_bdays = await load_birthdays()
        curr_bdays.update(raw_bdays)
        await save_birthdays(curr_bdays)
        stats["birthdays"] = len(curr_bdays)

    if isinstance(raw_conf := data.get("confessions"), dict):
        curr_conf = await safe_read_json(CONFESSIONS_FILE, {"last_id": 0, "entries": []})
        merged_id = max(curr_conf.get("last_id", 0), raw_conf.get("last_id", 0))
        existing_ids = {e["id"] for e in curr_conf.get("entries", []) if isinstance(e, dict) and "id" in e}
        combined = list(curr_conf.get("entries", []))
        for e in raw_conf.get("entries", []):
            if isinstance(e, dict) and e.get("id") not in existing_ids:
                combined.append(e)
                existing_ids.add(e["id"])
        await safe_write_json(CONFESSIONS_FILE, {"last_id": merged_id, "entries": combined})
        stats["confessions"] = len(combined)

    if raw_bump := data.get("last_bump_time"):
        LAST_BUMP_TIME = datetime.datetime.fromtimestamp(raw_bump, datetime.timezone.utc)
        await persist_runtime_state()

    existing_cats = {normalize_name(c.name): c for c in guild.categories}
    for cat_data in data.get("categories", []):
        norm_cat = normalize_name(cat_data["name"])
        category = existing_cats.get(norm_cat) or await guild.create_category(name=cat_data["name"])
        existing_cats[norm_cat] = category
        for tid, ow_info in cat_data.get("overwrites", {}).items():
            target = (guild.get_role(int(tid)) or discord.utils.get(guild.roles, name=ow_info.get("name"))) if ow_info["type"] == "role" else guild.get_member(int(tid))
            if target and target not in category.overwrites:
                try:
                    await category.set_permissions(target, overwrite=discord.PermissionOverwrite.from_pair(discord.Permissions(ow_info["allow"]), discord.Permissions(ow_info["deny"])))
                    stats["perms_applied"] += 1
                except Exception: pass
        existing_chs = {normalize_name(ch.name): ch for ch in category.channels}
        for ch_data in cat_data.get("channels", []):
            norm_ch, ch_type_str = normalize_name(ch_data["name"]), ch_data.get("type", "text")
            if norm_ch in existing_chs: channel = existing_chs[norm_ch]
            else:
                if "voice" in ch_type_str: channel = await guild.create_voice_channel(name=ch_data["name"], category=category, user_limit=ch_data.get("user_limit", 0))
                else: channel = await guild.create_text_channel(name=ch_data["name"], category=category)
                existing_chs[norm_ch] = channel
                stats["channels_created"] += 1
                await asyncio.sleep(0.3)
            for tid, ow_info in ch_data.get("overwrites", {}).items():
                target = (guild.get_role(int(tid)) or discord.utils.get(guild.roles, name=ow_info.get("name"))) if ow_info["type"] == "role" else guild.get_member(int(tid))
                if target and target not in channel.overwrites:
                    try:
                        await channel.set_permissions(target, overwrite=discord.PermissionOverwrite.from_pair(discord.Permissions(ow_info["allow"]), discord.Permissions(ow_info["deny"])))
                        stats["perms_applied"] += 1
                    except Exception: pass

    await enforce_admin_area_security(guild)
    return stats

# ==============================================================================
# AI-POWERED BUMP NOTIFICATION ENGINE
# ==============================================================================
def get_bump_role_mentions(guild: discord.Guild) -> str:
    bump_role = discord.utils.find(lambda r: r.name.lower().strip() in ["bump pings", "bump ping", "bumping"], guild.roles)
    return bump_role.mention if bump_role else "@here"

async def schedule_bump_timers(guild: discord.Guild, origin_channel: discord.TextChannel, expected_bump_time: datetime.datetime):
    target_channel = discord.utils.get(guild.text_channels, name="⏰・bump") or discord.utils.get(guild.text_channels, name="bump") or origin_channel
    if not target_channel: return
    elapsed = (datetime.datetime.now(datetime.timezone.utc) - expected_bump_time).total_seconds()
    try:
        if (fifteen_min_mark := 6300 - int(elapsed)) > 0:
            await asyncio.sleep(fifteen_min_mark)
            if LAST_BUMP_TIME != expected_bump_time: return
            msg_15m = await ai_dynamic_text(
                "Write an exciting 1-sentence alert that the Chill-Verse server bump cooldown ends in 15 minutes and +250 XP is up for grabs.",
                "⏳ **15-Minute Alert!** The 2-hour bump cooldown is almost over—get ready to claim +250 XP!"
            )
            embed = discord.Embed(title="⏰ Bump Reminder — 15 Minutes Remaining!", description=f"{msg_15m}\n\n🎁 First to type `.bump` in 15m earns **+250 XP**!", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
            await target_channel.send(content=get_bump_role_mentions(guild), embed=embed)

        remaining = BUMP_COOLDOWN_SECONDS - (datetime.datetime.now(datetime.timezone.utc) - expected_bump_time).total_seconds()
        if remaining > 0: await asyncio.sleep(remaining)
        if LAST_BUMP_TIME != expected_bump_time: return

        msg_ready = await ai_dynamic_text(
            "Write an urgent, hyped 1-sentence announcement that the 2-hour bump cooldown is over and members should type .bump now for +250 XP!",
            "🔔 **TIME TO BUMP!** The 2-hour cooldown is officially over! First to type `.bump` takes **+250 XP**!"
        )
        embed = discord.Embed(title="🔔 Chill-Verse is Ready to Bump!", description=f"{msg_ready}\n\nType **`.bump`** right now to boost the server!", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        await target_channel.send(content=get_bump_role_mentions(guild), embed=embed)
    except asyncio.CancelledError: pass

# ==============================================================================
# UI COMPONENTS & MODALS
# ==============================================================================
async def _schedule_message_deletion(message: Optional[discord.Message], delay: float = 7.0):
    if not message: return
    await asyncio.sleep(delay)
    try: await message.delete()
    except (discord.NotFound, discord.HTTPException): pass

class NicknameModal(Modal, title="Update Server Nickname"):
    new_nick = TextInput(label="New Server Nickname", placeholder="Enter your new nickname (max 32 chars)...", required=True, max_length=32)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
        if not member: return await interaction.followup.send("⚠️ Failed to resolve member profile.", ephemeral=True)
        if member.id == interaction.guild.owner_id or member.top_role >= interaction.guild.me.top_role:
            return await interaction.followup.send("⚠️ Discord role hierarchy prevents me from editing your nickname.", ephemeral=True)
        try:
            old_name, new_name = member.display_name, self.new_nick.value.strip()
            await member.edit(nick=new_name, reason="Self-service nickname changer (Level 11+)")
            await interaction.followup.send(f"✅ Nickname updated from **{old_name}** to **{new_name}**!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"⚠️ Could not update nickname: {e}", ephemeral=True)

class NicknamePanelView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🏷️ Change Nickname", style=discord.ButtonStyle.primary, custom_id="persistent_change_nickname")
    async def change_nick_btn(self, interaction: discord.Interaction, button: Button):
        lvl = calculate_level(await get_user_xp(interaction.user.id))
        if lvl < 11 and not getattr(getattr(interaction.user, "guild_permissions", None), "administrator", False):
            return await interaction.response.send_message(f"⛔ **Level 11+ Required!** You are currently **Level {lvl}**.", ephemeral=True)
        await interaction.response.send_modal(NicknameModal())

    @discord.ui.button(label="🔄 Reset to Default", style=discord.ButtonStyle.secondary, custom_id="persistent_reset_nickname")
    async def reset_nick_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        lvl = calculate_level(await get_user_xp(interaction.user.id))
        if lvl < 11 and not getattr(getattr(interaction.user, "guild_permissions", None), "administrator", False):
            return await interaction.followup.send(f"⛔ **Level 11+ Required!** You are currently **Level {lvl}**.", ephemeral=True)
        member = interaction.guild.get_member(interaction.user.id)
        if not member or member.id == interaction.guild.owner_id or member.top_role >= interaction.guild.me.top_role:
            return await interaction.followup.send("⚠️ Cannot reset nickname due to hierarchy restrictions.", ephemeral=True)
        await member.edit(nick=None, reason="Nickname reset")
        await interaction.followup.send("✅ Nickname reset to default!", ephemeral=True)

class XPDropView(View):
    def __init__(self, xp_amount: int, is_super: bool = False):
        super().__init__(timeout=180.0 if is_super else 300.0)
        self.xp_amount = xp_amount
        self.is_super = is_super
        self.claimed = False
        self.message: Optional[discord.Message] = None
        btn = Button(label="⚡ CLAIM SUPER DROP ⚡" if is_super else "🎁 Claim XP", style=discord.ButtonStyle.danger if is_super else discord.ButtonStyle.green)
        btn.callback = self.claim_callback
        self.add_item(btn)

    async def on_timeout(self):
        if not self.claimed and self.message:
            try: await self.message.delete()
            except (discord.NotFound, discord.HTTPException): pass

    async def claim_callback(self, interaction: discord.Interaction):
        if self.claimed: return await interaction.response.send_message("❌ Already claimed!", ephemeral=True)
        self.claimed = True
        for item in self.children:
            item.disabled = True
            item.label = "Claimed!"
            item.style = discord.ButtonStyle.secondary
        prev_xp, new_xp = await modify_user_xp(interaction.user.id, self.xp_amount, "add")
        embed = discord.Embed(
            title="💥 SUPER XP DROP SECURED! 💥" if self.is_super else "🎉 XP DROP CLAIMED!",
            description=f"⚡ {interaction.user.mention} grabbed **`+{self.xp_amount:,} XP`**!\n📊 **Total XP:** `{new_xp:,} XP` (Level {calculate_level(new_xp)})",
            color=discord.Color.from_rgb(255, 69, 0) if self.is_super else discord.Color.green(), timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=self)
        asyncio.create_task(_schedule_message_deletion(interaction.message, delay=7.0))
        if isinstance(interaction.user, discord.Member):
            await handle_level_up(interaction.user, prev_xp, new_xp, interaction.channel)

class ConfessionModal(Modal, title="Submit Anonymous Confession"):
    confession = TextInput(label="Your Secret Confession", style=discord.TextStyle.paragraph, placeholder="Type your confession here...", required=True, max_length=1500)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = await resolve_guild_context(interaction)
        confession_ch = (discord.utils.get(guild.text_channels, name="🚦・confession") or discord.utils.get(guild.text_channels, name="confessions")) if guild else None
        if not confession_ch: return await interaction.followup.send("⚠️ Confession channel not found!", ephemeral=True)
        cid = await record_confession(interaction.user.id, self.confession.value)
        embed = discord.Embed(title=f"💌 Anonymous Confession #{cid}", description=self.confession.value, color=discord.Color.from_rgb(255, 105, 180), timestamp=discord.utils.utcnow())
        embed.set_footer(text="Anonymous Submission • Chill-Verse Confessions")
        await confession_ch.send(embed=embed)
        if audit_ch := await get_or_create_system_channel(guild, "📜・audit-logs", "audit-logs"):
            log_embed = discord.Embed(title=f"🕵️ Confession #{cid} Trace", description=self.confession.value, color=discord.Color.dark_grey(), timestamp=discord.utils.utcnow())
            log_embed.add_field(name="Author", value=f"{interaction.user.mention} (`{interaction.user.id}`)")
            try: await audit_ch.send(embed=log_embed)
            except discord.HTTPException: pass
        await interaction.followup.send(f"✅ Confession posted anonymously as **#{cid}**!", ephemeral=True)

class ConfessionPanelView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🤫 Submit Confession", style=discord.ButtonStyle.secondary, custom_id="persistent_submit_confession", emoji="💌")
    async def submit_btn(self, interaction: discord.Interaction, button: Button): await interaction.response.send_modal(ConfessionModal())

class BirthdayModal(Modal, title="Register Your Birthday"):
    birthday_input = TextInput(label="Date of Birth (DD/MM)", placeholder="e.g. 24/09", required=True, max_length=10)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})", self.birthday_input.value.strip())
        if not m or not (1 <= int(m.group(1)) <= 31 and 1 <= int(m.group(2)) <= 12):
            return await interaction.followup.send("⚠️ Invalid format! Use `DD/MM` (e.g. `14/06`).", ephemeral=True)
        formatted = f"{int(m.group(1)):02d}/{int(m.group(2)):02d}"
        bdays = await load_birthdays()
        bdays[str(interaction.user.id)] = formatted
        await save_birthdays(bdays)
        await interaction.followup.send(f"🎂 **Birthday Registered** as **{formatted}**!", ephemeral=True)

class BirthdayPanelView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🎂 Register / Update Birthday", style=discord.ButtonStyle.primary, custom_id="persistent_register_birthday", emoji="🎉")
    async def register_birthday_btn(self, interaction: discord.Interaction, button: Button): await interaction.response.send_modal(BirthdayModal())

class ColourSelectionView(View):
    def __init__(self):
        super().__init__(timeout=None)
        emojis = {"Red": "🔴", "Yellow": "🟡", "Green": "🟢", "Blue": "🔵", "Orange": "🟠", "Pink": "🩷"}
        for idx, c_name in enumerate(COLOR_ROLES):
            btn = Button(label=f"{emojis[c_name]} {c_name}", style=discord.ButtonStyle.secondary, custom_id=f"pure_color_{c_name.lower()}", row=idx // 3)
            btn.callback = self._make_color_cb(c_name)
            self.add_item(btn)
        clear_btn = Button(label="⚪ Remove Colour", style=discord.ButtonStyle.danger, custom_id="pure_color_clear", row=2)
        clear_btn.callback = self.clear_color
        self.add_item(clear_btn)

    def _make_color_cb(self, role_name: str):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            target_role = discord.utils.get(interaction.guild.roles, name=role_name) if interaction.guild else None
            if not target_role: return await interaction.followup.send(f"⚠️ Role `{role_name}` not found.", ephemeral=True)
            member = interaction.guild.get_member(interaction.user.id)
            to_remove = [r for r in member.roles if r.name in COLOR_ROLES and r.name != role_name and r < interaction.guild.me.top_role]
            if to_remove: await member.remove_roles(*to_remove)
            if target_role in member.roles:
                await member.remove_roles(target_role)
                await interaction.followup.send(f"⚪ Removed **{role_name}**.", ephemeral=True)
            else:
                await member.add_roles(target_role)
                await interaction.followup.send(f"🎨 Equipped **{role_name}**!", ephemeral=True)
        return callback

    async def clear_color(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        member = interaction.guild.get_member(interaction.user.id)
        current = [r for r in member.roles if r.name in COLOR_ROLES and r < interaction.guild.me.top_role]
        if current: await member.remove_roles(*current)
        await interaction.followup.send("⚪ Colour roles removed.", ephemeral=True)

class NotificationRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)
        for label, r_name, cid in [("⏰ Bump Pings", "Bump Pings", "ping_bump"), ("📊 Poll Pings", "Poll Pings", "ping_polls"), ("💬 Chat Revive", "Chat Revive", "ping_revive")]:
            btn = Button(label=label, style=discord.ButtonStyle.primary, custom_id=cid)
            btn.callback = self._make_toggle(r_name)
            self.add_item(btn)

    def _make_toggle(self, role_name: str):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            member = interaction.guild.get_member(interaction.user.id)
            if not role or not member: return await interaction.followup.send("⚠️ Role not found.", ephemeral=True)
            if role in member.roles:
                await member.remove_roles(role)
                await interaction.followup.send(f"🔕 Removed **{role.name}**", ephemeral=True)
            else:
                await member.add_roles(role)
                await interaction.followup.send(f"🔔 Added **{role.name}**", ephemeral=True)
        return callback

class VerificationModal(Modal, title="Server Verification Form"):
    real_full_name = TextInput(label="Real Full Name", placeholder="John Doe", required=True, max_length=50)
    nickname = TextInput(label="Nickname", placeholder="Johnny", required=True, max_length=30)
    dob = TextInput(label="Date of Birth (DD/MM/YYYY)", placeholder="01/01/2005", required=True, max_length=10)
    reason = TextInput(label="Why do you want to join?", style=discord.TextStyle.paragraph, required=True, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = await resolve_guild_context(interaction)
        member = guild.get_member(interaction.user.id) if guild else None
        if not member: return await interaction.followup.send("⚠️ Member profile not found.", ephemeral=True)
        if m := re.match(r"^(\d{1,2})[/\-.](\d{1,2})", self.dob.value.strip()):
            bdays = await load_birthdays()
            bdays[str(interaction.user.id)] = f"{int(m.group(1)):02d}/{int(m.group(2)):02d}"
            await save_birthdays(bdays)
        if (role := discord.utils.get(guild.roles, name="Member")) and role < guild.me.top_role:
            try: await member.add_roles(role, reason="Verified")
            except discord.Forbidden: pass
        if log_ch := await get_or_create_system_channel(guild, "📜・audit-logs", "audit-logs"):
            embed = discord.Embed(title="✅ New Member Verified", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            embed.add_field(name="User", value=interaction.user.mention)
            embed.add_field(name="Name / Nick", value=f"{self.real_full_name.value} ({self.nickname.value})")
            embed.add_field(name="DOB", value=self.dob.value)
            embed.add_field(name="Reason", value=self.reason.value, inline=False)
            try: await log_ch.send(embed=embed)
            except discord.HTTPException: pass
        await interaction.followup.send("✅ Verification complete! Welcome to Chill-Verse.", ephemeral=True)

class TeamApplicationModal(Modal, title="Staff Team Application"):
    age_tz = TextInput(label="Age & Timezone", placeholder="18, PKT", required=True, max_length=50)
    experience = TextInput(label="Previous Experience", style=discord.TextStyle.paragraph, required=True, max_length=300)
    reason = TextInput(label="Why do you want to join the Team?", style=discord.TextStyle.paragraph, required=True, max_length=500)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = await resolve_guild_context(interaction)
        team_ch = (discord.utils.get(guild.text_channels, name="💬・team-chat") or discord.utils.get(guild.text_channels, name="team-news")) if guild else None
        if team_ch:
            embed = discord.Embed(title="🚨 New Staff Application", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
            embed.add_field(name="Applicant", value=interaction.user.mention)
            embed.add_field(name="Age & TZ", value=self.age_tz.value)
            embed.add_field(name="Experience", value=self.experience.value, inline=False)
            embed.add_field(name="Reason", value=self.reason.value, inline=False)
            try: await team_ch.send(embed=embed)
            except discord.HTTPException: pass
        await interaction.followup.send("✅ Application submitted for review!", ephemeral=True)

class RulesView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, custom_id="persistent_accept_rules")
    async def accept(self, interaction: discord.Interaction, button: Button): await interaction.response.send_modal(VerificationModal())
    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red, custom_id="persistent_decline_rules")
    async def decline(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        if guild := await resolve_guild_context(interaction):
            try: await guild.kick(interaction.user, reason="Declined server rules.")
            except Exception: pass

class CloseTicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="persistent_close_ticket", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...")
        await asyncio.sleep(5)
        try: await interaction.channel.delete(reason="Ticket closed")
        except Exception: pass

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.blurple, custom_id="persistent_open_ticket", emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        channel_name = f"ticket-{re.sub(r'[^a-zA-Z0-9_-]', '', interaction.user.name).lower() or 'user'}"
        if existing := discord.utils.get(guild.text_channels, name=channel_name):
            return await interaction.followup.send(f"⚠️ Active ticket already open: {existing.mention}", ephemeral=True)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True),
        }
        for rname in ("Supreme Leader", "Highness", "Authority", "Head Moderator", "Moderator"):
            if r := discord.utils.get(guild.roles, name=rname): overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        ticket_ch = await guild.create_text_channel(name=channel_name, category=discord.utils.get(guild.categories, name="Team Area"), overwrites=overwrites)
        await ticket_ch.send(embed=discord.Embed(title="🎫 Support Ticket", description=f"Welcome {interaction.user.mention}! Describe your inquiry below.", color=discord.Color.blue()), view=CloseTicketView())
        await interaction.followup.send(f"✅ Ticket created: {ticket_ch.mention}", ephemeral=True)

    @discord.ui.button(label="Apply for Team", style=discord.ButtonStyle.green, custom_id="persistent_apply_team", emoji="🛡️")
    async def apply_team(self, interaction: discord.Interaction, button: Button): await interaction.response.send_modal(TeamApplicationModal())

class AdminActionModal(Modal):
    def __init__(self, action: str, member: discord.Member):
        super().__init__(title=f"{action}: {member.display_name}")
        self.action, self.member = action, member
        self.val = TextInput(label="New Value (Leave blank to reset nickname)" if action == "Edit Nickname" else "New XP Amount", required=(action != "Edit Nickname"), max_length=32)
        self.add_item(self.val)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not has_high_command_access(interaction.user, interaction.guild): return await interaction.followup.send("⛔ Restricted.", ephemeral=True)
        if self.action == "Edit Nickname":
            await self.member.edit(nick=self.val.value.strip() or None)
            await interaction.followup.send("✅ Nickname updated.", ephemeral=True)
        else:
            _, new_xp = await modify_user_xp(self.member.id, int(self.val.value.strip()), "set")
            await sync_member_level_roles(self.member, new_xp)
            await interaction.followup.send(f"✅ Set XP to **{new_xp:,} XP**.", ephemeral=True)

class AdminUserActionsView(View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=300)
        self.member = member
    @discord.ui.button(label="Force Change Nickname", style=discord.ButtonStyle.primary, emoji="🏷️")
    async def change_nick(self, interaction: discord.Interaction, button: Button): await interaction.response.send_modal(AdminActionModal("Edit Nickname", self.member))
    @discord.ui.button(label="Override XP", style=discord.ButtonStyle.success, emoji="⭐")
    async def override_xp(self, interaction: discord.Interaction, button: Button): await interaction.response.send_modal(AdminActionModal("Set XP", self.member))
    @discord.ui.button(label="Kick User", style=discord.ButtonStyle.danger, emoji="👢")
    async def kick_user(self, interaction: discord.Interaction, button: Button):
        if not has_high_command_access(interaction.user, interaction.guild): return await interaction.response.send_message("⛔ Restricted.", ephemeral=True)
        await self.member.kick(reason=f"Admin Dashboard kick by {interaction.user}")
        await interaction.response.send_message(f"✅ Kicked **{self.member}**.", ephemeral=True)

class AdminControlPanelView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Select a Member to Manage...", min_values=1, max_values=1, custom_id="admin_dashboard_select")
    async def select_user(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        if not has_high_command_access(interaction.user, interaction.guild): return await interaction.response.send_message("⛔ Restricted.", ephemeral=True)
        member = interaction.guild.get_member(select.values[0].id)
        if not member: return await interaction.response.send_message("⚠️ Member not found.", ephemeral=True)
        await interaction.response.send_message(f"🛠️ **Managing:** {member.mention}", ephemeral=True, view=AdminUserActionsView(member))

# ==============================================================================
# COMPACT PANEL DEPLOYERS
# ==============================================================================
async def _deploy_panel_if_missing(guild: discord.Guild, ch_names: List[str], title_match: str, embed: discord.Embed, view: Optional[View] = None):
    ch = next((discord.utils.get(guild.text_channels, name=n) for n in ch_names if discord.utils.get(guild.text_channels, name=n)), None)
    if not ch: return
    try:
        async for msg in ch.history(limit=25):
            if msg.author == guild.me and msg.embeds and title_match in (msg.embeds[0].title or ""): return
        if guild.icon and not embed.thumbnail: embed.set_thumbnail(url=guild.icon.url)
        await ch.send(embed=embed, view=view)
    except Exception as e: print(f"[Panel Deploy Error] {ch_names[0]}: {e}")

async def deploy_all_system_panels(guild: discord.Guild, prefix: str = "."):
    await _deploy_panel_if_missing(guild, ["🛡️・server-rules", "server-rules"], "Official Server Rules",
        discord.Embed(title="📜 Official Server Rules & Member Verification", description="1. Be respectful and supportive.\n2. No harassment, hate speech, or toxicity.\n3. Keep content teen-friendly.\n4. No spam or unauthorized invites.\n5. Follow Discord ToS.\n\n👉 Click **Accept** below to verify!", color=discord.Color.purple()), RulesView())
    await _deploy_panel_if_missing(guild, ["🏷️・change-nickname", "change-nickname"], "Nickname Customization",
        discord.Embed(title="🏷️ Chill-Verse Nickname Customization (Level 11+)", description="Reach **Level 11+** through chatting or bumping to customize your nickname anytime!", color=discord.Color.gold()), NicknamePanelView())
    await _deploy_panel_if_missing(guild, ["🎂・birthdays", "birthdays"], "Birthday Calendar",
        discord.Embed(title="🎂 Chill-Verse Birthday Calendar & Registration", description="Click below to register your birthday (`DD/MM`) for automated server celebrations!", color=discord.Color.gold()), BirthdayPanelView())
    await _deploy_panel_if_missing(guild, ["🚦・confession", "confessions"], "Confession Box",
        discord.Embed(title="💌 Chill-Verse Anonymous Confession Box", description="Click **Submit Confession** below to post your thought 100% anonymously!", color=discord.Color.from_rgb(255, 105, 180)), ConfessionPanelView())
    await _deploy_panel_if_missing(guild, ["🎨・colours", "colours"], "Username Colours",
        discord.Embed(title="🎨 Chill-Verse Username Colours", description="Pick a cosmetic username colour below. No pings attached!", color=discord.Color.magenta()), ColourSelectionView())
    await _deploy_panel_if_missing(guild, ["📢・announcements", "announcements"], "Community Notification Preferences",
        discord.Embed(title="🔔 Community Notification Preferences", description="Opt-in or out of community pings below:", color=discord.Color.blurple()), NotificationRolesView())
    await _deploy_panel_if_missing(guild, ["🎫・tickets", "tickets"], "Support & Staff Applications",
        discord.Embed(title="🎫 Chill-Verse Support & Staff Applications", description="Open a private support ticket or apply for the Staff Team below:", color=discord.Color.blue()), TicketView())
    await _deploy_panel_if_missing(guild, ["🛡️・team-rules", "team-rules"], "TEAM GUIDELINES",
        discord.Embed(title="🛡️ CHILL-VERSE TEAM GUIDELINES & PROTOCOL", description="**1. Impartiality:** Moderate objectively.\n**2. Confidentiality:** Never leak internal channels.\n**3. Hierarchy:** Respect Supreme Leader, Highness, and Authority directives.", color=discord.Color.dark_red()))
    await _deploy_panel_if_missing(guild, ["🚨・team-news", "team-news"], "ACTIVE BOT COMMANDS",
        discord.Embed(title="💼 TEAM & AUTHORITY ACTIVE BOT COMMANDS", description=(
            f"**Moderation:** `{prefix}ban`, `{prefix}kick`, `{prefix}mute`, `{prefix}unmute`, `{prefix}warn`\n"
            f"**Channels:** `{prefix}purge`, `{prefix}lock`, `{prefix}unlock`, `{prefix}hide`, `{prefix}show`, `{prefix}permit`, `{prefix}revoke`\n"
            f"**XP & Drops:** `{prefix}addxp`, `{prefix}removexp`, `{prefix}setxp`, `{prefix}superdrop`, `{prefix}xpdrop`\n"
            f"**AI Controls:** `{prefix}ai <prompt>`, `{prefix}clear_ai`, `{prefix}ai_toggle`"
        ), color=discord.Color.gold()))
    await _deploy_panel_if_missing(guild, ["💼・bot-commands", "bot-commands"], "MASTER COMMAND DIRECTORY",
        discord.Embed(title="🤖 CHILL-VERSE BOT MASTER COMMAND DIRECTORY", description=(
            f"**General:** `{prefix}ping`, `{prefix}about`, `{prefix}bump`, `{prefix}revive`, `{prefix}xp`, `{prefix}birthdays`, `{prefix}afk`\n"
            f"**AI Companion:** `{prefix}ai <prompt>`, `{prefix}clear_ai`, `{prefix}ai_toggle` (Auto-active in `#🍸・chat-ai` & `#✨・chat-ai-beta`)\n"
            f"**Staff & Authority:** `{prefix}ban`, `{prefix}kick`, `{prefix}mute`, `{prefix}unmute`, `{prefix}warn`, `{prefix}purge`, `{prefix}lock`, `{prefix}unlock`, `{prefix}announce`\n"
            f"**System & Recovery:** `{prefix}clean_start`, `{prefix}deploy_panels`, `{prefix}admin_panel`, `{prefix}backup_all`, `{prefix}restore_all`, `{prefix}restore_xp_from_roles`, `{prefix}maintenance`, `{prefix}shutdown`"
        ), color=discord.Color.blurple()))

# ==============================================================================
# SUBCLASSED BOT ENGINE
# ==============================================================================
class ArkBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=".", intents=intents, strip_after_prefix=True)
        self.remove_command("help")
        self.first_run_completed = False
        self.restore_complete = asyncio.Event()

    async def setup_hook(self):
        await restore_runtime_state()
        await init_xp_cache()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try: loop.add_signal_handler(sig, lambda: asyncio.create_task(self.close()))
            except (NotImplementedError, RuntimeError): pass

        for v in (RulesView(), TicketView(), CloseTicketView(), ColourSelectionView(), NotificationRolesView(), ConfessionPanelView(), BirthdayPanelView(), NicknamePanelView(), AdminControlPanelView()):
            self.add_view(v)

        asyncio.create_task(self._auto_restore_all_guilds())
        for task in (hourly_backup_task, birthday_announcer_task, xp_drop_task, xp_flush_task):
            if not task.is_running(): task.start()

    async def _provision_blueprint_and_roles(self, guild: discord.Guild) -> Tuple[int, int]:
        created_channels, created_roles = 0, 0
        existing_cats = {normalize_name(c.name): c for c in guild.categories}
        for cat_data in SERVER_BLUEPRINT:
            norm_cat = normalize_name(cat_data["category"])
            category = existing_cats.get(norm_cat) or await guild.create_category(name=cat_data["category"])
            existing_cats[norm_cat] = category
            existing_chs = {normalize_name(ch.name): ch for ch in category.channels}
            for ch_info in cat_data["channels"]:
                if normalize_name(ch_info["name"]) in existing_chs: continue
                if ch_info["type"] == "voice": await guild.create_voice_channel(name=ch_info["name"], category=category, user_limit=ch_info.get("user_limit", 0))
                else: await guild.create_text_channel(name=ch_info["name"], category=category)
                created_channels += 1

        existing_roles = {r.name.lower().strip() for r in guild.roles}
        roles_spec = [
            ("Supreme Leader", discord.Color.dark_red(), True, True), ("Highness", discord.Color.gold(), True, True),
            ("Authority", discord.Color.orange(), True, True), ("Head Moderator", discord.Color.red(), True, True),
            ("Moderator", discord.Color.yellow(), True, True), ("Trial Mod", discord.Color.blue(), True, True),
            ("Chill-Verse Team", discord.Color(0x313338), True, False), ("Chat Revive", discord.Color.from_rgb(26, 188, 156), False, True),
            ("Member", discord.Color.default(), False, False), ("Bump Pings", discord.Color.purple(), False, True), ("Poll Pings", discord.Color.default(), False, True),
            ("Red", discord.Color.from_rgb(255, 0, 0), False, False), ("Yellow", discord.Color.from_rgb(255, 255, 0), False, False),
            ("Green", discord.Color.from_rgb(0, 128, 0), False, False), ("Blue", discord.Color.from_rgb(0, 0, 255), False, False),
            ("Orange", discord.Color.from_rgb(255, 165, 0), False, False), ("Pink", discord.Color.from_rgb(255, 105, 180), False, False),
        ] + [(t_name, discord.Color.teal(), False, False) for _, t_name in LEVEL_TIERS]

        for r_name, r_col, r_hoist, r_ment in roles_spec:
            if r_name.lower().strip() not in existing_roles:
                try:
                    await guild.create_role(name=r_name, color=r_col, hoist=r_hoist, mentionable=r_ment)
                    created_roles += 1
                except Exception: pass
        return created_channels, created_roles

    async def _auto_restore_all_guilds(self):
        await self.wait_until_ready()
        global BUMP_TIMER_TASK
        try:
            for guild in self.guilds:
                backup_file = MASTER_BACKUP_TEMPLATE.format(guild_id=guild.id)
                boot_backup = await safe_read_json(backup_file, None) or await find_latest_backup_from_discord(guild)
                await self._provision_blueprint_and_roles(guild)
                if boot_backup: await apply_unified_restore(guild, boot_backup)
                await clear_all_bot_notifications(guild)
                await deploy_all_system_panels(guild, self.command_prefix)
                await enforce_admin_area_security(guild)
                fresh_payload = await generate_unified_backup_payload(guild)
                await safe_write_json(backup_file, fresh_payload)
                if err_ch := (discord.utils.get(guild.text_channels, name="🩸・bot-errors") or discord.utils.get(guild.text_channels, name="bot-errors")):
                    await purge_all_old_backups(err_ch)
                    await err_ch.send(content="🔒 **Master Single Backup Snapshot (Clean Start & AI Online)**", file=discord.File(io.BytesIO(json.dumps(fresh_payload, indent=4).encode("utf-8")), filename=backup_file))
        except Exception as e:
            print(f"[Auto-Boot Error]: {e}")
        finally:
            self.restore_complete.set()

        if LAST_BUMP_TIME and self.guilds:
            if (datetime.datetime.now(datetime.timezone.utc) - LAST_BUMP_TIME).total_seconds() < BUMP_COOLDOWN_SECONDS:
                if target_ch := discord.utils.get(self.guilds[0].text_channels, name="⏰・bump"):
                    BUMP_TIMER_TASK = asyncio.create_task(schedule_bump_timers(self.guilds[0], target_ch, LAST_BUMP_TIME))

    async def close(self):
        await flush_xp_cache()
        await persist_runtime_state()
        await super().close()

bot = ArkBot()

# ==============================================================================
# EVENTS & AI MESSAGE LISTENER
# ==============================================================================
@bot.check
async def check_maintenance_mode(ctx: commands.Context):
    if not MAINTENANCE_MODE or (ctx.command and ctx.command.name in ["maintenance", "shutdown"]) or has_high_command_access(ctx.author, ctx.guild):
        return True
    await ctx.send("🛠️ **Maintenance Mode Active:** Non-administrative commands are temporarily disabled.", delete_after=6)
    return False

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} — Chill-Verse AI Engine Operational.")
    await bot.restore_complete.wait()
    if bot.first_run_completed: return
    bot.first_run_completed = True
    for guild in bot.guilds:
        test_ch = await get_or_create_system_channel(guild, "🧪・bot-testing", "bot-testing")
        await get_or_create_system_channel(guild, "📜・audit-logs", "audit-logs")
        if test_ch:
            embed = discord.Embed(title="🧪 Arkbot Startup Diagnostic", description="Clean start & AI dynamic generation active.", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            embed.add_field(name="Latency", value=f"`{round(bot.latency * 1000)}ms`")
            embed.add_field(name="AI Engine", value="`Online`" if ai_client else "`Missing API Key`")
            await test_ch.send(embed=embed)

@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot or not message.guild: return
    if log_ch := await get_or_create_system_channel(message.guild, "📜・audit-logs", "audit-logs"):
        embed = discord.Embed(title="🗑️ Message Deleted", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Author", value=f"{message.author.mention} (`{message.author.id}`)")
        embed.add_field(name="Channel", value=message.channel.mention)
        embed.add_field(name="Content", value=(message.content or "*Empty*")[:1000], inline=False)
        try: await log_ch.send(embed=embed)
        except Exception: pass

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.author.bot or not before.guild or before.content == after.content: return
    if log_ch := await get_or_create_system_channel(before.guild, "📜・audit-logs", "audit-logs"):
        embed = discord.Embed(title="✏️ Message Edited", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Author", value=f"{before.author.mention}")
        embed.add_field(name="Channel", value=f"{before.channel.mention} ([Jump]({after.jump_url}))")
        embed.add_field(name="Before", value=(before.content or "*Empty*")[:1000], inline=False)
        embed.add_field(name="After", value=(after.content or "*Empty*")[:1000], inline=False)
        try: await log_ch.send(embed=embed)
        except Exception: pass

@bot.event
async def on_member_join(member: discord.Member):
    ai_welcome = await ai_dynamic_text(f"Write a warm 1-sentence welcome greeting for {member.display_name} joining the Chill-Verse Discord server!", f"Welcome to **Chill-Verse**, {member.mention}! 🎉")
    embed = discord.Embed(title="Welcome to Chill-Verse! 🎉", description=f"{ai_welcome}\n\nClick **Accept** below to complete verification and unlock the server!", color=discord.Color.purple())
    sent_dm = False
    try:
        await member.send(embed=embed, view=RulesView())
        sent_dm = True
    except discord.Forbidden: pass
    if ch := discord.utils.get(member.guild.text_channels, name="👋・welcome"):
        await ch.send(content=f"{member.mention} Check your DMs or click **Accept** below to verify!" if not sent_dm else f"{member.mention} Welcome! Check your DMs to verify.", embed=embed, view=RulesView())

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot: return
    if MAINTENANCE_MODE and not has_high_command_access(message.author, message.guild):
        ctx = await bot.get_context(message)
        if ctx.valid: await bot.process_commands(message)
        return

    ctx = await bot.get_context(message)

    # AI-Powered AFK Return & Mention Alerts
    if message.author.id in AFK_USERS and (not ctx.command or ctx.command.name != "afk"):
        del AFK_USERS[message.author.id]
        await persist_runtime_state()
        welcome_line = await ai_dynamic_text(
            f"Write a warm, enthusiastic 1-sentence welcome back message for {message.author.display_name} who just returned from AFK in Chill-Verse.",
            f"☀️ Welcome back, {message.author.mention}! The chat missed your energy!"
        )
        await message.channel.send(embed=discord.Embed(description=welcome_line, color=discord.Color.green()), delete_after=10)

    for mentioned in message.mentions:
        if mentioned.id in AFK_USERS and mentioned.id != message.author.id:
            await message.channel.send(embed=discord.Embed(description=f"💤 **{mentioned.display_name} is AFK:**\n*{AFK_USERS[mentioned.id]['reason']}*", color=discord.Color.dark_purple()), delete_after=10)

    # Anti-Invite & Anti-Spam
    if isinstance(message.author, discord.Member) and not is_team_member(message.author):
        if INVITE_REGEX.search(message.content):
            try: await message.delete()
            except discord.HTTPException: pass
            return await message.channel.send(f"⚠️ {message.author.mention}, invite links are prohibited!", delete_after=4)
        now = discord.utils.utcnow().timestamp()
        q = USER_MESSAGE_TIMESTAMPS[message.author.id]
        q.append(now)
        if len([t for t in q if now - t < 4.0]) > 5:
            q.clear()
            try: await message.delete()
            except discord.HTTPException: pass
            return await message.channel.send(f"⚠️ {message.author.mention}, slow down!", delete_after=4)

    # XP Gain, Super Drops & AI Chat Handling
    if message.guild and not ctx.valid:
        now_ts = discord.utils.utcnow().timestamp()
        if now_ts - USER_CHAT_XP_COOLDOWN.get(message.author.id, 0.0) >= 60.0:
            USER_CHAT_XP_COOLDOWN[message.author.id] = now_ts
            prev_xp, new_xp = await modify_user_xp(message.author.id, random.randint(15, 25), "add")
            await handle_level_up(message.author, prev_xp, new_xp, message.channel)

        ch_name = getattr(message.channel, "name", "")
        is_ai_channel = ch_name in AI_CHANNELS
        is_bot_mentioned = bot.user in message.mentions

        if (is_ai_channel or is_bot_mentioned) and AI_ENABLED:
            if now_ts - AI_USER_COOLDOWNS.get(message.author.id, 0.0) >= AI_COOLDOWN_SECONDS:
                AI_USER_COOLDOWNS[message.author.id] = now_ts
                clean_prompt = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
                if clean_prompt:
                    use_beta = "beta" in ch_name
                    async with message.channel.typing():
                        reply = await generate_ai_reply(message.channel.id, message.author.display_name, clean_prompt, use_beta=use_beta)
                    await message.reply(reply[:1950], mention_author=False)

        if isinstance(message.channel, discord.TextChannel) and message.channel.category and "chill area" in message.channel.category.name.lower() and ch_name not in SYSTEM_CHANNELS:
            act_q = CHANNEL_CHAT_ACTIVITY[message.channel.id]
            act_q.append((message.author.id, now_ts))
            if len({u for u, t in act_q if now_ts - t <= 120.0}) >= 3:
                if (now_ts - SUPER_DROP_COOLDOWNS.get(message.channel.id, 0.0) >= SUPER_DROP_COOLDOWN_SECONDS) and (random.random() < 0.05):
                    SUPER_DROP_COOLDOWNS[message.channel.id] = now_ts
                    super_xp = random.randint(1000, 5000)
                    view = XPDropView(super_xp, is_super=True)
                    sent = await message.channel.send(embed=discord.Embed(title="🚨 🔥 SUPER XP DROP! 🔥 🚨", description=f"Claim **`+{super_xp:,} XP`** now!", color=discord.Color.from_rgb(255, 69, 0)), view=view)
                    view.message = sent

    await bot.process_commands(message)

# ==============================================================================
# AUTOMATED BACKGROUND TASKS
# ==============================================================================
@tasks.loop(seconds=60.0)
async def xp_flush_task(): await flush_xp_cache()

@tasks.loop(hours=2.0)
async def xp_drop_task():
    await bot.wait_until_ready()
    if MAINTENANCE_MODE: return
    for guild in bot.guilds:
        if chill_cat := discord.utils.find(lambda c: "chill area" in c.name.lower(), guild.categories):
            eligible = [ch for ch in chill_cat.text_channels if ch.name not in SYSTEM_CHANNELS and ch.permissions_for(guild.default_role).view_channel]
            if eligible:
                target, drop_xp = random.choice(eligible), random.randint(50, 150)
                view = XPDropView(drop_xp)
                try: view.message = await target.send(embed=discord.Embed(title="🎁 WILD XP DROP!", description=f"Be the first to claim **+{drop_xp} XP**!", color=discord.Color.gold()), view=view)
                except discord.HTTPException: pass

@tasks.loop(hours=1.0)
async def hourly_backup_task():
    await bot.wait_until_ready()
    for guild in bot.guilds:
        payload = await generate_unified_backup_payload(guild)
        b_file = MASTER_BACKUP_TEMPLATE.format(guild_id=guild.id)
        await safe_write_json(b_file, payload)
        if b_ch := (discord.utils.get(guild.text_channels, name="🩸・bot-errors") or discord.utils.get(guild.text_channels, name="bot-errors")):
            await purge_all_old_backups(b_ch)
            try: await b_ch.send(content="🔒 **Master Hourly Single Snapshot**", file=discord.File(io.BytesIO(json.dumps(payload, indent=4).encode("utf-8")), filename=b_file))
            except Exception: pass

@tasks.loop(hours=1.0)
async def birthday_announcer_task():
    await bot.wait_until_ready()
    now = datetime.datetime.now(datetime.timezone.utc)
    if now.hour == 0:
        ANNOUNCED_BIRTHDAYS_TODAY.clear()
        REMINDED_BIRTHDAYS_TOMORROW.clear()
        await persist_runtime_state()
    today_s, tom_s = now.strftime("%d/%m"), (now + datetime.timedelta(days=1)).strftime("%d/%m")
    bdays = await load_birthdays()
    for guild in bot.guilds:
        bday_ch = discord.utils.get(guild.text_channels, name="🎂・birthdays") or discord.utils.get(guild.text_channels, name="birthdays")
        if not bday_ch: continue
        for uid_str, bdate in bdays.items():
            member = guild.get_member(int(uid_str))
            if not member: continue
            if bdate == today_s and member.id not in ANNOUNCED_BIRTHDAYS_TODAY:
                wish = await ai_dynamic_text(f"Write a celebratory birthday wish for {member.display_name} from the Chill-Verse community!", f"Happy Birthday {member.mention}! Wishing you an amazing year ahead! 🎂")
                await bday_ch.send(content=f"🎉 Wish {member.mention} a Happy Birthday! 🥳", embed=discord.Embed(title="🎂 HAPPY BIRTHDAY! 🎉", description=wish, color=discord.Color.gold()).set_thumbnail(url=member.display_avatar.url))
                ANNOUNCED_BIRTHDAYS_TODAY.append(member.id)
                await persist_runtime_state()
            elif bdate == tom_s and member.id not in REMINDED_BIRTHDAYS_TOMORROW and now.hour >= 12:
                await bday_ch.send(embed=discord.Embed(title="⏰ UPCOMING BIRTHDAY ALERT! 🎂", description=f"Tomorrow is {member.mention}'s birthday (`{tom_s}`)! Get your wishes ready! 🎈", color=discord.Color.from_rgb(255, 182, 193)))
                REMINDED_BIRTHDAYS_TOMORROW.append(member.id)
                await persist_runtime_state()

# ==============================================================================
# AI, MEMBER & MODERATION COMMANDS
# ==============================================================================
@bot.command(name="ai", aliases=["ask", "chat"])
async def ai_command(ctx: commands.Context, *, prompt: str):
    async with ctx.typing():
        reply = await generate_ai_reply(ctx.channel.id, ctx.author.display_name, prompt, use_beta=("beta" in getattr(ctx.channel, "name", "")))
    await ctx.reply(reply[:1950], mention_author=False)

@bot.command(name="clear_ai", aliases=["reset_ai"])
async def clear_ai_memory(ctx: commands.Context):
    AI_CHAT_HISTORY[ctx.channel.id].clear()
    await ctx.send("🧹 **Cleared AI conversation memory for this channel!**", delete_after=6)

@bot.command(name="ai_toggle", aliases=["toggle_ai"])
@is_authority_holder()
async def toggle_ai_engine(ctx: commands.Context):
    global AI_ENABLED
    AI_ENABLED = not AI_ENABLED
    await persist_runtime_state()
    await ctx.send(f"🤖 **Arkbot AI Engine is now {'🟢 ENABLED' if AI_ENABLED else '🔴 DISABLED'}.**")

@bot.command(name="ping")
async def ping(ctx: commands.Context): await ctx.send(f"🏓 **Pong!** Latency: `{round(bot.latency * 1000)}ms`")

@bot.command(name="about", aliases=["aboutme", "botinfo"])
async def about_bot(ctx: commands.Context):
    embed = discord.Embed(title="🤖 About Arkbot (AI-Enabled)", description="Proprietary AI-powered community, leveling, and security system for **Chill-Verse**.", color=discord.Color.blurple(), timestamp=discord.utils.utcnow())
    embed.add_field(name="👨‍💻 Maintainer", value="`iamthesubhanahmed`")
    embed.add_field(name="🏢 Company", value="**Tier3.pk**")
    embed.add_field(name="🧠 AI Model", value=f"`{AI_MODEL}`")
    await ctx.send(embed=embed)

@bot.command(name="afk")
async def afk(ctx: commands.Context, *, reason: Optional[str] = None):
    selected_status = reason.strip() if reason else await ai_dynamic_text(
        f"Write a poetic, cozy 1-sentence AFK status message for {ctx.author.display_name} stepping away from chat.",
        "🌙 Stepping away into the quiet twilight for a bit... catch you all soon."
    )
    AFK_USERS[ctx.author.id] = {"reason": selected_status, "time": discord.utils.utcnow()}
    await persist_runtime_state()
    await ctx.send(embed=discord.Embed(description=f"🌙 **{ctx.author.display_name} is now AFK**\n*{selected_status}*", color=discord.Color.purple()), delete_after=10)
    try: await ctx.message.delete()
    except Exception: pass

@bot.command(name="bump")
async def bump(ctx: commands.Context):
    global LAST_BUMP_TIME, BUMP_TIMER_TASK
    bump_ch = discord.utils.get(ctx.guild.text_channels, name="⏰・bump") or discord.utils.get(ctx.guild.text_channels, name="bump")
    if bump_ch and ctx.channel.id != bump_ch.id:
        return await ctx.send(f"⚠️ Use `.bump` in {bump_ch.mention}!", delete_after=6)
    async with BUMP_LOCK:
        now = discord.utils.utcnow()
        if LAST_BUMP_TIME and (elapsed := (now - LAST_BUMP_TIME).total_seconds()) < BUMP_COOLDOWN_SECONDS:
            rem = int(BUMP_COOLDOWN_SECONDS - elapsed)
            return await ctx.send(embed=discord.Embed(title="⛔ BUMP LOCKED!", description=f"⏳ Remaining: `{rem // 3600}h {(rem % 3600) // 60}m {rem % 60}s`", color=discord.Color.red()), delete_after=7)
        LAST_BUMP_TIME = now
        await persist_runtime_state()
        prev_xp, new_xp = await modify_user_xp(ctx.author.id, 250, "add")
        if BUMP_TIMER_TASK and not BUMP_TIMER_TASK.done(): BUMP_TIMER_TASK.cancel()
        BUMP_TIMER_TASK = asyncio.create_task(schedule_bump_timers(ctx.guild, bump_ch or ctx.channel, LAST_BUMP_TIME))

    bump_line = await ai_dynamic_text(
        f"Write an energetic 1-sentence cosmic celebration thanking {ctx.author.display_name} for bumping the Chill-Verse server!",
        "🚀 **Server Bumped!** Chill-Verse has been blasted into the cosmos—thank you for supporting the community!"
    )
    embed = discord.Embed(title="✨ CHILL-VERSE BUMPED! ✨", description=f"{bump_line}\n\n🎁 **Reward:** **+250 XP** (`{new_xp:,} XP` Total)", color=discord.Color.gold(), timestamp=now)
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)
    await handle_level_up(ctx.author, prev_xp, new_xp, ctx.channel)

@bot.command(name="revive", aliases=["chatrevive"])
@commands.guild_only()
async def chat_revive(ctx: commands.Context, *, topic: Optional[str] = None):
    now = discord.utils.utcnow().timestamp()
    if now - LAST_REVIVE_TIME.get(ctx.guild.id, 0.0) < REVIVE_COOLDOWN_SECONDS:
        rem = int(REVIVE_COOLDOWN_SECONDS - (now - LAST_REVIVE_TIME[ctx.guild.id]))
        return await ctx.send(f"⏳ **Cooldown:** `{rem // 60}m {rem % 60}s` remaining!", delete_after=6)
    LAST_REVIVE_TIME[ctx.guild.id] = now
    question = topic.strip() if topic else await ai_dynamic_text(
        "Generate a fun, debatable, teen-friendly icebreaker question to wake up a quiet Discord chat.",
        "If you could teleport anywhere in the world right now for 24 hours, where would you go?"
    )
    revive_role = discord.utils.get(ctx.guild.roles, name="Chat Revive")
    embed = discord.Embed(title="⚡ CHAT REVIVE SUMMONS! ⚡", description=f"**{ctx.author.mention} wants to wake up the chat!**\n\n🗣️ **Topic:**\n> *\"{question}\"*", color=discord.Color.from_rgb(26, 188, 156), timestamp=discord.utils.utcnow())
    await ctx.send(content=revive_role.mention if revive_role else "@here", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True, everyone=True))
    try: await ctx.message.delete()
    except Exception: pass

@bot.command(name="xp", aliases=["rank", "level"])
async def check_xp(ctx: commands.Context, member: Optional[discord.Member] = None):
    target = member or ctx.author
    user_xp = await get_user_xp(target.id)
    lvl, nxt = calculate_level(user_xp), xp_for_level(calculate_level(user_xp) + 1)
    tier = next((r_name for min_lvl, r_name in LEVEL_TIERS if lvl >= min_lvl), "None")
    embed = discord.Embed(title=f"📊 Level & XP — {target.display_name}", color=discord.Color.purple())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Level", value=f"**Level {lvl}**")
    embed.add_field(name="Total XP", value=f"**{user_xp:,} XP**")
    embed.add_field(name="Rank Tier", value=f"🛡️ **{tier}**", inline=False)
    embed.add_field(name="Next Level", value=f"**{nxt:,} XP** (*{nxt - user_xp:,} XP left*)", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="birthdays", aliases=["upcoming_birthdays"])
async def upcoming_birthdays_cmd(ctx: commands.Context):
    bdays = await load_birthdays()
    if not bdays: return await ctx.send("🎂 No birthdays registered yet!", delete_after=6)
    now = datetime.datetime.now(datetime.timezone.utc)
    today = datetime.date(now.year, now.month, now.day)
    upcoming = []
    for uid_str, bdate in bdays.items():
        if member := ctx.guild.get_member(int(uid_str)):
            d, m = map(int, bdate.split("/"))
            b_next = datetime.date(now.year + (1 if datetime.date(now.year, m, d) < today else 0), m, d)
            upcoming.append(((b_next - today).days, member, bdate))
    upcoming.sort(key=lambda x: x[0])
    lines = [f"• {m.mention} — `{b}` ({'🎉 **TODAY!**' if days == 0 else f'in **{days}d**'})" for days, m, b in upcoming[:12]]
    await ctx.send(embed=discord.Embed(title="🎂 Upcoming Chill-Verse Birthdays", description="\n".join(lines) or "None found.", color=discord.Color.gold()))

@bot.command(name="addxp")
@is_authority_holder()
async def addxp(ctx: commands.Context, member: discord.Member, amount: int):
    _, new_xp = await modify_user_xp(member.id, amount, "add")
    await sync_member_level_roles(member, new_xp)
    await ctx.send(f"✅ Added **+{amount:,} XP** to {member.mention} (Now `{new_xp:,} XP` • Level {calculate_level(new_xp)}).")

@bot.command(name="removexp")
@is_authority_holder()
async def removexp(ctx: commands.Context, member: discord.Member, amount: int):
    _, new_xp = await modify_user_xp(member.id, amount, "remove")
    await sync_member_level_roles(member, new_xp)
    await ctx.send(f"🔻 Removed **-{amount:,} XP** from {member.mention} (Now `{new_xp:,} XP` • Level {calculate_level(new_xp)}).")

@bot.command(name="setxp")
@is_authority_holder()
async def setxp(ctx: commands.Context, member: discord.Member, amount: int):
    _, new_xp = await modify_user_xp(member.id, amount, "set")
    await sync_member_level_roles(member, new_xp)
    await ctx.send(f"⚙️ Set {member.mention}'s XP to **`{new_xp:,} XP`** (Level {calculate_level(new_xp)}).")

@bot.command(name="superdrop")
@is_authority_holder()
async def manual_super_drop(ctx: commands.Context, amount: Optional[int] = None, channel: Optional[discord.TextChannel] = None):
    target_ch, xp_val = channel or ctx.channel, amount or random.randint(1000, 5000)
    view = XPDropView(xp_val, is_super=True)
    view.message = await target_ch.send(embed=discord.Embed(title="🚨 🔥 SUPER XP DROP! 🔥 🚨", description=f"Summoned by {ctx.author.mention}! Claim **`+{xp_val:,} XP`**!", color=discord.Color.from_rgb(255, 69, 0)), view=view)

@bot.command(name="xpdrop")
@is_authority_holder()
async def manual_xp_drop(ctx: commands.Context, amount: Optional[int] = None, channel: Optional[discord.TextChannel] = None):
    target_ch, xp_val = channel or ctx.channel, amount or random.randint(50, 150)
    view = XPDropView(xp_val)
    view.message = await target_ch.send(embed=discord.Embed(title="🎁 WILD XP DROP!", description=f"Claim **`+{xp_val:,} XP`**!", color=discord.Color.gold()), view=view)

@bot.command(name="ban")
@is_team_authorized()
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
    if not can_moderate(ctx, member): return await ctx.send("⛔ Hierarchy error.", delete_after=5)
    await member.ban(reason=f"{ctx.author}: {reason}")
    await ctx.send(f"🔨 Banned **{member}** — {reason}")

@bot.command(name="kick")
@is_team_authorized()
async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
    if not can_moderate(ctx, member): return await ctx.send("⛔ Hierarchy error.", delete_after=5)
    await member.kick(reason=f"{ctx.author}: {reason}")
    await ctx.send(f"👢 Kicked **{member}** — {reason}")

@bot.command(name="mute", aliases=["timeout"])
@is_team_authorized()
async def mute(ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided."):
    if not can_moderate(ctx, member): return await ctx.send("⛔ Hierarchy error.", delete_after=5)
    m = re.match(r"^(\d+)([smhd])$", duration.lower())
    if not m: return await ctx.send("⚠️ Use `10m`, `1h`, or `1d`.", delete_after=5)
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    await member.timeout(discord.utils.utcnow() + datetime.timedelta(seconds=int(m.group(1)) * units[m.group(2)]), reason=reason)
    await ctx.send(f"🔇 Muted **{member}** for **{duration}** — {reason}")

@bot.command(name="unmute")
@is_team_authorized()
async def unmute(ctx: commands.Context, member: discord.Member):
    if not can_moderate(ctx, member): return await ctx.send("⛔ Hierarchy error.", delete_after=5)
    await member.timeout(None)
    await ctx.send(f"🔊 Unmuted **{member}**.")

@bot.command(name="warn")
@is_team_authorized()
async def warn(ctx: commands.Context, member: discord.Member, *, reason: str):
    if not can_moderate(ctx, member): return await ctx.send("⛔ Hierarchy error.", delete_after=5)
    try: await member.send(f"⚠️ Formal warning in **{ctx.guild.name}**: {reason}")
    except discord.Forbidden: pass
    await ctx.send(f"⚠️ Warned **{member}** — {reason}")

@bot.command(name="purge")
@is_authority_holder()
async def purge(ctx: commands.Context, amount: int = 10):
    await ctx.message.delete()
    deleted = await ctx.channel.purge(limit=max(1, min(1000, amount)), check=lambda m: not m.pinned)
    await ctx.send(f"🧹 Cleared **{len(deleted)}** messages.", delete_after=5)

@bot.command(name="lock")
@is_authority_holder()
async def lock_ch(ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
    ch = channel or ctx.channel
    await ch.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"🔒 Locked {ch.mention}.")

@bot.command(name="unlock")
@is_authority_holder()
async def unlock_ch(ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
    ch = channel or ctx.channel
    await ch.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓 Unlocked {ch.mention}.")

@bot.command(name="hide")
@is_authority_holder()
async def hide_ch(ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
    ch = channel or ctx.channel
    await ch.set_permissions(ctx.guild.default_role, view_channel=False)
    await ctx.send(f"👁️‍🗨️ Hidden {ch.mention}.")

@bot.command(name="show")
@is_authority_holder()
async def show_ch(ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
    ch = channel or ctx.channel
    await ch.set_permissions(ctx.guild.default_role, view_channel=True)
    await ctx.send(f"👁️ Unhidden {ch.mention}.")

@bot.command(name="permit")
@is_authority_holder()
async def permit(ctx: commands.Context, target: Union[discord.Member, discord.Role]):
    await ctx.channel.set_permissions(target, view_channel=True, send_messages=True)
    await ctx.send(f"✅ Permitted {target.mention}.")

@bot.command(name="revoke")
@is_authority_holder()
async def revoke(ctx: commands.Context, target: Union[discord.Member, discord.Role]):
    await ctx.channel.set_permissions(target, overwrite=None)
    await ctx.send(f"🚫 Revoked overrides for {target.mention}.")

@bot.command(name="announce")
@is_authority_holder()
async def announce(ctx: commands.Context, *, raw_content: str):
    content = raw_content.strip()
    target_ch = ctx.message.channel_mentions[0] if (ctx.message.channel_mentions and content.startswith(ctx.message.channel_mentions[0].mention)) else (discord.utils.get(ctx.guild.text_channels, name="📢・announcements") or ctx.channel)
    if ctx.message.channel_mentions and content.startswith(target_ch.mention): content = content[len(target_ch.mention):].strip()
    ping_str = "@everyone" if "--everyone" in content else ("@here" if "--here" in content else None)
    content = content.replace("--everyone", "").replace("--here", "").strip()
    title, body = (content.split("|", 1)[0].strip(), content.split("|", 1)[1].strip()) if "|" in content else ("Community Announcement", content)
    await target_ch.send(content=ping_str, embed=discord.Embed(title=title, description=body, color=discord.Color.gold(), timestamp=discord.utils.utcnow()), allowed_mentions=discord.AllowedMentions(everyone=True, roles=True))

@bot.command(name="clean_start")
@commands.has_permissions(administrator=True)
async def cmd_clean_start(ctx: commands.Context):
    msg = await ctx.send("🧹 **Executing Clean Start...**")
    await clear_all_bot_notifications(ctx.guild)
    await deploy_all_system_panels(ctx.guild, bot.command_prefix)
    await msg.edit(content="✨ **Clean Start Complete!**")

@bot.command(name="deploy_panels")
@commands.has_permissions(administrator=True)
async def cmd_deploy_panels(ctx: commands.Context):
    await deploy_all_system_panels(ctx.guild, bot.command_prefix)
    await ctx.send("✅ **All panels deployed!**", delete_after=5)

@bot.command(name="admin_panel", aliases=["dashboard"])
@commands.has_permissions(administrator=True)
async def spawn_admin_panel(ctx: commands.Context):
    await ctx.send(embed=discord.Embed(title="🛡️ Executive Admin Dashboard", description="Select a member below to override Nickname, XP, or Status.", color=discord.Color.dark_red()), view=AdminControlPanelView())

@bot.command(name="backup_all")
@commands.has_permissions(administrator=True)
async def backup_all(ctx: commands.Context):
    payload = await generate_unified_backup_payload(ctx.guild)
    fname = MASTER_BACKUP_TEMPLATE.format(guild_id=ctx.guild.id)
    await safe_write_json(fname, payload)
    await ctx.send("✅ **Master Backup Generated!**", file=discord.File(io.BytesIO(json.dumps(payload, indent=4).encode("utf-8")), filename=fname))

@bot.command(name="restore_all")
@commands.has_permissions(administrator=True)
async def restore_all(ctx: commands.Context):
    msg = await ctx.send("🔄 **Restoring system...**")
    data = None
    if ctx.message.attachments and ctx.message.attachments[0].filename.endswith(".json"):
        data = json.loads((await ctx.message.attachments[0].read()).decode("utf-8"))
    else:
        data = await find_latest_backup_from_discord(ctx.guild) or await safe_read_json(MASTER_BACKUP_TEMPLATE.format(guild_id=ctx.guild.id), None)
    if not data: return await msg.edit(content="⚠️ No backup found!")
    await bot._provision_blueprint_and_roles(ctx.guild)
    stats = await apply_unified_restore(ctx.guild, data)
    await deploy_all_system_panels(ctx.guild, bot.command_prefix)
    await msg.edit(content=f"✅ **Restore Complete!** (`{stats['xp_users']}` XP profiles, `{stats['birthdays']}` birthdays synced).")

@bot.command(name="restore_xp_from_roles")
@commands.has_permissions(administrator=True)
async def restore_xp_from_roles(ctx: commands.Context):
    restored = 0
    for m in ctx.guild.members:
        if m.bot: continue
        r_names = {r.name for r in m.roles}
        lvl = next((min_l for min_l, r_n in sorted(LEVEL_TIERS, reverse=True) if r_n in r_names), 0)
        if lvl > 0 and await get_user_xp(m.id) < xp_for_level(lvl):
            await modify_user_xp(m.id, xp_for_level(lvl), "set")
            restored += 1
    await flush_xp_cache()
    await ctx.send(f"✅ Recovered baseline XP for **{restored}** member(s).")

@bot.command(name="maintenance")
@commands.has_permissions(administrator=True)
async def maintenance_toggle(ctx: commands.Context):
    global MAINTENANCE_MODE
    MAINTENANCE_MODE = not MAINTENANCE_MODE
    await persist_runtime_state()
    await ctx.send(f"🛠️ **Maintenance Mode: {'🔴 ON' if MAINTENANCE_MODE else '🟢 OFF'}**")

@bot.command(name="shutdown")
@commands.has_permissions(administrator=True)
async def shutdown(ctx: commands.Context):
    await ctx.send("🛑 **Saving state and shutting down...**")
    await bot.close()
    sys.exit(0)

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN: print("⚠️ Missing DISCORD_BOT_TOKEN!")
    else: bot.run(TOKEN)
