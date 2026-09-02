import os
import asyncio
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
DISBOARD_BOT_ID = 302050872383422240  # Disboard Bot User ID
MOD_LOG_CHANNEL_ID = 123456789012345678  # Replace with your Mod Log / Banned Notification Channel ID

# Storage Dictionaries
afk_users = {}
user_xp = {}
user_levels = {}
user_warns = {}

# XP Threshold to reach Level 2 (and subsequent levels)
XP_PER_LEVEL = 500

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
async def add_xp(user, amount, channel):
    """Adds XP to a user and handles level-up logic & notifications."""
    user_id = user.id
    current_xp = user_xp.get(user_id, 0) + amount
    user_xp[user_id] = current_xp

    current_level = user_levels.get(user_id, 1)
    new_level = (current_xp // XP_PER_LEVEL) + 1

    if new_level > current_level:
        user_levels[user_id] = new_level
        await channel.send(
            f"🎉 **LEVEL UP!** {user.mention} has leveled up to **Level {new_level}**! 🚀"
        )

# ---------------------------------------------------------
# Events
# ---------------------------------------------------------

# 1. On Member Join: Auto Level 1 Notification & Role
@bot.event
async def on_member_join(member):
    user_levels[member.id] = 1
    user_xp[member.id] = 0

    # Auto Role Assignment
    role = discord.utils.get(member.guild.roles, name=NEW_MEMBER_ROLE)
    if role:
        await member.add_roles(role)

    # Public Welcome & Level 1 Notification
    system_channel = member.guild.system_channel or member.guild.text_channels[0]
    if system_channel:
        await system_channel.send(
            f"👋 Welcome to the server, {member.mention}! You are starting at **Level 1**."
        )

# 2. Member Ban Notification
@bot.event
async def on_member_ban(guild, user):
    log_channel = guild.get_channel(MOD_LOG_CHANNEL_ID) or guild.system_channel
    if log_channel:
        await log_channel.send(
            f"🚨 **User Banned:** {user.name}#{user.discriminator} ({user.mention}) has been banned from the server."
        )

# 3. Main Message Handler (Disboard Bump, AFK, XP Tracker)
@bot.event
async def on_message(message):
    if message.author.id == bot.user.id or message.author.bot:
        return

    # A. Award XP for active messaging
    await add_xp(message.author, 15, message.channel)

    # B. Detect Disboard Bump Success
    if message.author.id == DISBOARD_BOT_ID and message.embeds:
        for embed in message.embeds:
            description = embed.description or ""
            if "Bump done" in description:
                bumper = message.interaction.user if message.interaction else None

                if bumper:
                    await add_xp(bumper, 200, message.channel)
                    await message.channel.send(
                        f"🎉 Thank you for bumping, {bumper.mention}! You earned **200 XP**."
                    )
                else:
                    await message.channel.send("🎉 Thank you for bumping! You earned **200 XP**.")

                # 2-Hour Timer Notification
                await message.channel.send("⏱️ I will notify everyone in this channel to bump again in 2 hours!")
                await asyncio.sleep(7200)
                await message.channel.send("🔔 **Time to bump!** Use `/bump` to boost the server again!")

    # C. AFK Mention Notification
    if message.mentions:
        for mention in message.mentions:
            if mention.id in afk_users:
                reason = afk_users[mention.id]
                await message.channel.send(f"{mention.display_name} is currently AFK: {reason}")

    # D. Auto-Remove AFK Status
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(f"Welcome back, {message.author.display_name}! I removed your AFK status.")

    await bot.process_commands(message)

# ---------------------------------------------------------
# Commands
# ---------------------------------------------------------

# AFK Command
@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    await ctx.send(f"{ctx.author.mention}, I set your AFK status to: {reason}")

# Moderation: Warn
@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    user_warns[member.id] = user_warns.get(member.id, 0) + 1
    total_warns = user_warns[member.id]
    await ctx.send(
        f"⚠️ {member.mention} has been warned for: **{reason}**. Total warnings: **{total_warns}**."
    )

# Moderation: Kick
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member.mention} has been kicked. Reason: **{reason}**.")

# Moderation: Ban
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member.mention} has been banned. Reason: **{reason}**.")

# Check Level / XP
@bot.command()
async def level(ctx, member: discord.Member = None):
    target = member or ctx.author
    lvl = user_levels.get(target.id, 1)
    xp = user_xp.get(target.id, 0)
    await ctx.send(f"📊 **{target.display_name}** is **Level {lvl}** ({xp} total XP).")

# Run Bot
bot.run(os.getenv("DISCORD_TOKEN"))
