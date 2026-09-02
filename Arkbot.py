import os
import asyncio
import time
import discord
from discord.ext import commands

# Bot Setup & Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration
NEW_MEMBER_ROLE = "Newbie"
MOD_LOG_CHANNEL_ID = 123456789012345678  # Replace with your log channel ID
BUMP_CHANNEL_ID = YOUR_BUMP_CHANNEL_ID_HERE  # Replace with your bump channel ID

# Storage Dictionaries & Timers
afk_users = {}
user_xp = {}
user_levels = {}
user_warns = {}
last_bump_time = 0  # Timestamp of the last successful bump

BASE_XP_LEVEL_1 = 500  # XP required to reach Level 2

# Helper Functions
def get_xp_for_level(level):
    """Calculates XP needed to pass the current level (doubles each level)."""
    return BASE_XP_LEVEL_1 * (2 ** (level - 1))

async def add_xp(user, amount, channel):
    """Adds XP to a user and handles exponential level-up logic."""
    user_id = user.id
    current_xp = user_xp.get(user_id, 0) + amount
    user_xp[user_id] = current_xp

    current_level = user_levels.get(user_id, 1)
    xp_needed = get_xp_for_level(current_level)

    if current_xp >= xp_needed:
        user_levels[user_id] = current_level + 1
        await channel.send(f"🎉 **LEVEL UP!** {user.mention} has leveled up to **Level {current_level + 1}**!")

# Events
@bot.event
async def on_member_join(member):
    user_levels[member.id] = 1
    user_xp[member.id] = 0

    role = discord.utils.get(member.guild.roles, name=NEW_MEMBER_ROLE)
    if role:
        await member.add_roles(role)

    system_channel = member.guild.system_channel
    if system_channel:
        await system_channel.send(f"👋 Welcome to the server, {member.mention}!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Award XP for active messaging
    await add_xp(message.author, 15, message.channel)

    # Auto-Remove AFK Status
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(f"Welcome back {message.author.mention}, I removed your AFK status.")

    await bot.process_commands(message)

# Commands
@bot.command()
async def bump(ctx):
    global last_bump_time

    # 1. Channel Restriction
    if ctx.channel.id != BUMP_CHANNEL_ID:
        await ctx.send(f"⚠️ This command can only be used in <#{BUMP_CHANNEL_ID}>.")
        return

    # 2. Cooldown Check (2 hours = 7200 seconds)
    current_time = time.time()
    cooldown = 7200
    time_passed = current_time - last_bump_time

    if time_passed < cooldown:
        remaining_seconds = int(cooldown - time_passed)
        minutes, seconds = divmod(remaining_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        await ctx.send(f"⏳ Please wait **{hours}h {minutes}m {seconds}s** before bumping again.")
        return

    # 3. Successful Bump Execution
    last_bump_time = current_time
    await add_xp(ctx.author, 200, ctx.channel)
    await ctx.send(f"🚀 **Bump successful!** Thanks {ctx.author.mention}! (+200 XP)")

@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    await ctx.send(f"I set your AFK status to: {reason}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    user_warns[member.id] = user_warns.get(member.id, 0) + 1
    total_warns = user_warns[member.id]
    await ctx.send(f"⚠️ {member.mention} has been warned. Total warnings: {total_warns}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member.mention} has been kicked. Reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member.mention} has been banned. Reason: {reason}")

@bot.command()
async def level(ctx, member: discord.Member = None):
    target = member or ctx.author
    lvl = user_levels.get(target.id, 1)
    xp = user_xp.get(target.id, 0)
    needed = get_xp_for_level(lvl)
    await ctx.send(f"📊 {target.display_name} is Level **{lvl}** ({xp}/{needed} XP)")

bot.run(os.getenv("DISCORD_TOKEN"))
