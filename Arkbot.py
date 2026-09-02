import os
import asyncio
import datetime
import random
import discord
from discord.ext import commands

# Bot Setup & Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.moderation = True

bot = commands.Bot(command_prefix=".", intents=intents)

# Configuration
NEW_MEMBER_ROLE = "Newbie"
DISBOARD_BOT_ID = 302050872383422240
ANNOUNCEMENT_CHANNEL_ID = 0  # Managed automatically or set manually
BUMP_CHANNEL_ID = 0          # Strictly locks bump functionality to a single channel

# Storage Dictionaries
afk_users = {}
afk_mentions = {}
user_xp = {}
user_levels = {}
user_warnings = {}
user_mute_counts = {}

# Bump Management Variables
last_bump_time = 0
bump_cooldown_seconds = 7200  # 2 Hours

# Cute Bump Phrases
CUTE_BUMP_MESSAGES = [
    "You're absolute perfection! Thanks for helping us grow! 💖✨",
    "Sending you virtual warm hugs and lots of appreciation! 🧸🌸",
    "You just brightened up the whole server's day! 🌟✨",
    "Thank you for being so amazing and keeping our cozy home alive! 🐾💌",
    "You're a superstar! Server sparkles everywhere for you! ✨💖"
]

PRO_HEX_COLORS = [
    "Pro Hex Red",
    "Pro Hex Green",
    "Pro Hex Blue",
    "Pro Hex Pink",
    "Pro Hex Yellow",
    "Pro Hex Orange",
]

BASE_XP_LEVEL_1 = 500
MAX_LEVEL = 60

PURGE_ALLOWED_ROLES = ["head moderator", "authority"]

# Helper Functions
def is_purge_authorized():
    async def predicate(ctx):
        if ctx.author.id == ctx.guild.owner_id:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        user_roles = [r.name.lower() for r in ctx.author.roles]
        if any(role_name in user_roles for role_name in PURGE_ALLOWED_ROLES):
            return True
        raise commands.CheckFailure("You do not have permission to use the purge command.")
    return commands.check(predicate)

def get_xp_for_level(level):
    if level >= MAX_LEVEL:
        return BASE_XP_LEVEL_1 * (2 ** (MAX_LEVEL - 2))
    return BASE_XP_LEVEL_1 * (2 ** (level - 1))

async def get_or_create_announcement_channel(guild):
    global ANNOUNCEMENT_CHANNEL_ID
    if ANNOUNCEMENT_CHANNEL_ID:
        channel = guild.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if channel:
            return channel

    for channel in guild.text_channels:
        if channel.name.lower() in ["announcements", "level-announcements"]:
            ANNOUNCEMENT_CHANNEL_ID = channel.id
            return channel

    try:
        new_channel = await guild.create_text_channel("level-announcements")
        ANNOUNCEMENT_CHANNEL_ID = new_channel.id
        await new_channel.send("📢 **Leveling Announcement Channel Initialized!** All level updates will broadcast here.")
        return new_channel
    except discord.Forbidden:
        return None

async def get_or_create_bump_channel(guild):
    global BUMP_CHANNEL_ID
    if BUMP_CHANNEL_ID:
        channel = guild.get_channel(BUMP_CHANNEL_ID)
        if channel:
            return channel

    for channel in guild.text_channels:
        if channel.name.lower() == "bump":
            BUMP_CHANNEL_ID = channel.id
            return channel

    try:
        new_channel = await guild.create_text_channel("bump")
        BUMP_CHANNEL_ID = new_channel.id
        await new_channel.send("🚀 **Dedicated Bump Channel Initialized!** Use `.bump` here to boost the server.")
        return new_channel
    except discord.Forbidden:
        return None

async def add_xp(user, amount, guild, fallback_channel):
    user_id = user.id
    current_level = user_levels.get(user_id, 1)

    if current_level >= MAX_LEVEL:
        return

    current_xp = user_xp.get(user_id, 0) + amount
    user_xp[user_id] = current_xp

    xp_needed = get_xp_for_level(current_level)

    if current_xp >= xp_needed:
        new_level = min(current_level + 1, MAX_LEVEL)
        user_levels[user_id] = new_level
        
        target_channel = await get_or_create_announcement_channel(guild) or fallback_channel
        if target_channel:
            await target_channel.send(
                f"🎉 **[LEVEL UP]** {user.mention} has gained enough XP and is now **Level {new_level}**!"
            )

# Events
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    for guild in bot.guilds:
        await get_or_create_bump_channel(guild)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ **Access Denied**: Only the Server Owner, Administrators, Head Moderators, or Authority can use this command.")
    else:
        raise error

@bot.event
async def on_member_join(member):
    user_levels[member.id] = 1
    user_xp[member.id] = 0

    newbie_role = discord.utils.get(member.guild.roles, name=NEW_MEMBER_ROLE)
    if newbie_role:
        await member.add_roles(newbie_role)

    target_channel = await get_or_create_announcement_channel(member.guild) or member.guild.system_channel
    if target_channel:
        await target_channel.send(
            f"Welcome to the server, {member.mention}! You have been assigned the **{NEW_MEMBER_ROLE}** role and automatically started at **Level 1**."
        )

@bot.event
async def on_message(message):
    if message.author.id == bot.user.id or message.author.bot or not message.guild:
        return

    # Award XP for active messaging
    await add_xp(message.author, 15, message.guild, message.channel)

    bump_channel = await get_or_create_bump_channel(message.guild)

    # Detect Disboard Bump Success ONLY inside the dedicated bump channel
    if bump_channel and message.channel.id == bump_channel.id:
        if message.author.id == DISBOARD_BOT_ID and message.embeds:
            for embed in message.embeds:
                description = embed.description or ""
                if "Bump done" in description:
                    global last_bump_time
                    current_time = asyncio.get_event_loop().time()
                    time_passed = current_time - last_bump_time

                    if last_bump_time != 0 and time_passed < bump_cooldown_seconds:
                        remaining_seconds = int(bump_cooldown_seconds - time_passed)
                        minutes, seconds = divmod(remaining_seconds, 60)
                        hours, minutes = divmod(minutes, 60)
                        await message.channel.send(
                            f"⚠️ **Bump Cooldown Active**: No XP awarded! Please wait **{hours}h {minutes}m {seconds}s** until the next bump notification."
                        )
                        return

                    last_bump_time = current_time
                    bumper = message.interaction.user if message.interaction else None
                    cute_line = random.choice(CUTE_BUMP_MESSAGES)

                    if bumper:
                        await add_xp(bumper, 200, message.guild, message.channel)
                        await message.channel.send(f"Thank you for bumping, {bumper.mention}! You earned **200 XP**.\n*{cute_line}*")
                    else:
                        await message.channel.send(f"Thank you for bumping! You earned **200 XP**.\n*{cute_line}*")

                    await message.channel.send("I will notify everyone in this channel to bump again in 2 hours!")
                    await asyncio.sleep(bump_cooldown_seconds)
                    await message.channel.send("⏰ **Time to bump!** Use `.bump` or Disboard to boost the server again!")

    # AFK Mention Notification Collection
    if message.mentions:
        for mention in message.mentions:
            if mention.id in afk_users:
                reason = afk_users[mention.id]
                if mention.id not in afk_mentions:
                    afk_mentions[mention.id] = []
                afk_mentions[mention.id].append(f"From {message.author.display_name} in {message.channel.mention}: {message.content}")
                await message.channel.send(f"{mention.display_name} is currently AFK: {reason}")

    # Auto-Remove AFK Status
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        welcome_msg = f"Welcome back, {message.author.display_name}! Your AFK status has been removed."
        
        if message.author.id in afk_mentions and afk_mentions[message.author.id]:
            missed = "\n".join(afk_mentions[message.author.id][-5:])
            welcome_msg += f"\n\n📬 **While you were AFK, you received these messages:**\n{missed}"
            del afk_mentions[message.author.id]

        await message.channel.send(welcome_msg)

    await bot.process_commands(message)

# Commands
@bot.command()
async def bump(ctx):
    bump_channel = await get_or_create_bump_channel(ctx.guild)

    if bump_channel and ctx.channel.id != bump_channel.id:
        await ctx.send(f"❌ The `.bump` command can only be used in {bump_channel.mention}!")
        return

    global last_bump_time
    current_time = asyncio.get_event_loop().time()
    time_passed = current_time - last_bump_time

    if last_bump_time != 0 and time_passed < bump_cooldown_seconds:
        remaining_seconds = int(bump_cooldown_seconds - time_passed)
        minutes, seconds = divmod(remaining_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        await ctx.send(f"❌ **No XP Awarded**: Bump cooldown active! Please wait **{hours}h {minutes}m {seconds}s** until the next bump notification.")
        return

    last_bump_time = current_time
    await add_xp(ctx.author, 200, ctx.guild, ctx.channel)
    
    cute_line = random.choice(CUTE_BUMP_MESSAGES)
    await ctx.send(f"Thank you for bumping, {ctx.author.mention}! (**+200 XP**)\n*{cute_line}*\n\nI will notify everyone in this channel to bump again in 2 hours!")
    
    await asyncio.sleep(bump_cooldown_seconds)
    await ctx.send("⏰ **Time to bump!** Use `.bump` to boost the server again!")

@bot.command()
@is_purge_authorized()
async def purge(ctx, amount: int):
    if amount < 1 or amount > 100:
        await ctx.send("❌ Please specify a number of messages to purge between **1 and 100**.")
        return

    deleted = await ctx.channel.purge(limit=amount + 1)
    confirm_msg = await ctx.send(f"🧹 Successfully purged **{len(deleted) - 1}** messages.")
    await asyncio.sleep(3)
    await confirm_msg.delete()

@bot.command()
async def setup_bump(ctx):
    channel = await get_or_create_bump_channel(ctx.guild)
    if channel:
        await ctx.send(f"✅ Dedicated bump channel is active at {channel.mention}!")
    else:
        await ctx.send("❌ Failed to set up the bump channel. Check my server permissions.")

@bot.command()
async def setup_announcements(ctx):
    channel = await get_or_create_announcement_channel(ctx.guild)
    if channel:
        await ctx.send(f"✅ Leveling announcements channel is configured to {channel.mention}!")
    else:
        await ctx.send("❌ Failed to create channel. Please check my server permissions.")

@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    await ctx.send(f"{ctx.author.mention}, I set your AFK status to: {reason}")

@bot.command()
async def color(ctx, *, color_name: str):
    matched_role_name = None
    for valid_color in PRO_HEX_COLORS:
        if color_name.lower() in valid_color.lower():
            matched_role_name = valid_color
            break

    if not matched_role_name:
        available = ", ".join(PRO_HEX_COLORS)
        await ctx.send(f"Invalid color choice. Available options: {available}")
        return

    role = discord.utils.get(ctx.guild.roles, name=matched_role_name)
    if not role:
        await ctx.send(f"The role `{matched_role_name}` does not exist on this server yet.")
        return

    roles_to_remove = [r for r in ctx.author.roles if r.name in PRO_HEX_COLORS]
    if roles_to_remove:
        await ctx.author.remove_roles(*roles_to_remove)

    await ctx.author.add_roles(role)
    await ctx.send(f"Successfully applied the {role.name} color role to you!")

# Moderation Commands
@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, *, reason="No reason provided"):
    if member.bot:
        await ctx.send("You cannot mute bots.")
        return

    user_id = member.id
    current_mutes = user_mute_counts.get(user_id, 0) + 1
    user_mute_counts[user_id] = current_mutes

    if current_mutes == 1:
        duration = datetime.timedelta(hours=1)
        duration_label = "1 hour"
    elif current_mutes == 2:
        duration = datetime.timedelta(hours=6)
        duration_label = "6 hours"
    else:
        duration = datetime.timedelta(hours=12)
        duration_label = "12 hours"

    try:
        await member.timeout(duration, reason=reason)
        await ctx.send(
            f"🔇 {member.mention} has been muted for **{duration_label}** (Mute #{current_mutes}). Reason: {reason}"
        )
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to timeout/mute this user.")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    try:
        await member.timeout(None)
        await ctx.send(f"🔊 {member.mention} has been unmuted.")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to unmute this user.")

@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    if member.bot:
        await ctx.send("You cannot warn bots.")
        return

    user_id = member.id
    current_warns = user_warnings.get(user_id, 0) + 1
    user_warnings[user_id] = current_warns

    await ctx.send(f"⚠️ {member.mention} has been warned! **Warning {current_warns}/3**. Reason: {reason}")

    if current_warns >= 3:
        user_warnings[user_id] = 0
        auto_ban_reason = f"Automated Ban: Reached 3/3 warnings. Last warning reason: {reason}"
        await member.ban(reason=auto_ban_reason)
        await ctx.send(f"🔨 **AUTOMATIC BAN**: {member.mention} has reached 3 warnings and was automatically banned!")

@bot.command()
@commands.has_permissions(kick_members=True)
async def clearwarns(ctx, member: discord.Member):
    user_warnings[member.id] = 0
    await ctx.send(f"✅ Cleared all warnings for {member.mention}.")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f"{member.mention} has been kicked. Reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member.mention} has been banned by {ctx.author.mention}. Violation Reason: **{reason}**")

@bot.command()
async def level(ctx, member: discord.Member = None):
    target = member or ctx.author
    lvl = user_levels.get(target.id, 1)
    xp = user_xp.get(target.id, 0)
    
    if lvl >= MAX_LEVEL:
        await ctx.send(f"{target.display_name} has reached the maximum **Level {MAX_LEVEL}**! ({xp} total XP).")
    else:
        needed = get_xp_for_level(lvl)
        await ctx.send(f"{target.display_name} is Level **{lvl}** ({xp} / {needed} XP).")

bot.run(os.getenv("DISCORD_TOKEN"))
