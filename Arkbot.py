import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput
from typing import Union, Dict, Any, List, Optional
import datetime
import json
import io
import asyncio
import os
import re
import random
from collections import defaultdict

# ==============================================================================
# BOT SETUP & INTENTS
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# State tracking
UPDATE_NOTIFIED = False
MAINTENANCE_MODE = False
AFK_USERS: Dict[int, Dict[str, Any]] = {}

# Custom AFK Messages
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
    "🌧️ Drifting into silent solitude to heal and recharge. Keep a warm thought for me."
]

AFK_WELCOME_MESSAGES = [
    "☀️ You're back! The entire room just lit up. Welcome back, {user}!",
    "💖 Welcome back, {user}! The server felt far too quiet without your energy!",
    "🎉 Look who returned! We missed you so much, {user}!",
    "🥳 You're finally back! Everything feels complete again. Welcome home, {user}!",
    "✨ Warmest welcome back, {user}! So genuinely happy to see you chatting again!"
]

# AutoMod tracking caches
USER_MESSAGE_TIMESTAMPS = defaultdict(list)
INVITE_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discord(?:app)?\.com/invite)/[a-zA-Z0-9_-]+",
    re.IGNORECASE
)

# ==============================================================================
# SERVER BLUEPRINT CONFIGURATION
# ==============================================================================
SERVER_BLUEPRINT: List[Dict[str, Any]] = [
    {
        "category": "Welcome",
        "channels": [
            {"name": "📢・announcements", "type": "text", "restricted": False, "read_only": True},
            {"name": "server-rules", "type": "text", "restricted": False, "read_only": True},
            {"name": "👋・welcome", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Team <3",
        "channels": [
            {"name": "team-news", "type": "text", "restricted": True},
            {"name": "🛡️・team-rules", "type": "text", "restricted": True},
            {"name": "💬・team-chat", "type": "text", "restricted": True},
            {"name": "⏰・bump", "type": "text", "restricted": True},
            {"name": "team-news-forum", "type": "forum", "restricted": True}
        ]
    },
    {
        "category": "Events <3",
        "channels": [
            {"name": "🎉・gwys", "type": "text", "restricted": False},
            {"name": "⭐・vouch", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Chill Area <3",
        "channels": [
            {"name": "discussions-🐣", "type": "forum", "restricted": False},
            {"name": "☁️・chat", "type": "text", "restricted": False},
            {"name": "🍸・chat-ai", "type": "text", "restricted": False},
            {"name": "🪄・chat-en", "type": "text", "restricted": False},
            {"name": "🐥・discussions", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Media <3",
        "channels": [
            {"name": "pfp-share🛼", "type": "text", "restricted": False},
            {"name": "media-share🪹", "type": "text", "restricted": False},
            {"name": "selfies🫂", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Fun Area <3",
        "channels": [
            {"name": "playground-🥊", "type": "text", "restricted": False},
            {"name": "birthdays", "type": "text", "restricted": False},
            {"name": "🚦confession-🖇️", "type": "text", "restricted": False},
            {"name": "memes🤪", "type": "text", "restricted": False},
            {"name": "🖇️-daily-polls", "type": "text", "restricted": False},
            {"name": "🖇️-roblox-elites", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Hobbies <3",
        "channels": [
            {"name": "shayari-and-poetry💗-forum", "type": "forum", "restricted": False},
            {"name": "photography📷", "type": "text", "restricted": False},
            {"name": "arts-and-crafts🎨", "type": "text", "restricted": False},
            {"name": "🎤drop-your-songs", "type": "text", "restricted": False},
            {"name": "shayari-and-poetry💗", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Voice Chat <3",
        "channels": [
            {"name": "🍕 | chit-chat", "type": "voice", "restricted": False, "user_limit": 12},
            {"name": "🍔 | Duo", "type": "voice", "restricted": False, "user_limit": 2},
            {"name": "🍞 | Trio", "type": "voice", "restricted": False, "user_limit": 3},
            {"name": "🧀 | squad", "type": "voice", "restricted": False, "user_limit": 4},
            {"name": "🍺 | Vip", "type": "voice", "restricted": False, "user_limit": 50}
        ]
    },
    {
        "category": "Music <3",
        "channels": [
            {"name": "🎵 Hade Music", "type": "voice", "restricted": False},
            {"name": "🎸 -Atom Music", "type": "voice", "restricted": False}
        ]
    },
    {
        "category": "Info 🩵",
        "channels": [
            {"name": "📢・level-announcements", "type": "text", "restricted": False, "read_only": True},
            {"name": "🎫・tickets", "type": "text", "restricted": False},
            {"name": "🎨・colours", "type": "text", "restricted": False}
        ]
    },
    {
        "category": "Admin Area 🔒",
        "channels": [
            {"name": "💼・bot-commands", "type": "text", "restricted": True},
            {"name": "🩸・bot-errors", "type": "text", "restricted": True}
        ]
    }
]

# ==============================================================================
# AUTHORITY CHECKS & HELPERS
# ==============================================================================
def is_authority_holder():
    """Command check restricted to Administrators and top Authority roles."""
    async def predicate(ctx):
        if not ctx.guild:
            return False
        if getattr(ctx.author.guild_permissions, "administrator", False):
            return True
        authority_roles = {"Supreme Leader", "Highness", "Authority"}
        user_roles = getattr(ctx.author, "roles", [])
        if any(role.name in authority_roles for role in user_roles):
            return True
        raise commands.CheckFailure("⛔ **Restricted:** Only Administrators and Authority holders can execute this command.")
    return commands.check(predicate)

def is_team_member(member: Union[discord.Member, discord.User]) -> bool:
    """Checks if a user has any staff or administrative hierarchy role."""
    if not isinstance(member, discord.Member):
        return False
    if member.guild_permissions.administrator:
        return True
    team_roles = {"Supreme Leader", "Highness", "Authority", "Head Moderator", "Moderator", "Trial Mod", "Chill-Verse Team"}
    return any(role.name in team_roles for role in member.roles)

def is_allowed_channel(channel, member: Union[discord.Member, discord.User] = None) -> bool:
    """Restricts regular members from running bot commands in designated fun/music channels."""
    if member and is_team_member(member):
        return True
    ch_name = getattr(channel, "name", "").lower()
    if "playground" in ch_name:
        return False
    category = getattr(channel, "category", None)
    if category and "music" in category.name.lower():
        return False
    return True

def resolve_guild_context(interaction: discord.Interaction, fallback_guild: Optional[discord.Guild] = None) -> Optional[discord.Guild]:
    """Resolves guild context securely without blindly defaulting to an arbitrary server."""
    if interaction.guild:
        return interaction.guild
    if fallback_guild:
        return fallback_guild
    # Restrict to matching guilds where the member is actively present
    matched = [g for g in interaction.client.guilds if g.get_member(interaction.user.id)]
    if len(matched) == 1:
        return matched[0]
    return None

async def get_or_create_memory_channel(guild: discord.Guild) -> discord.TextChannel:
    """Finds or constructs the bot-memory channel for persistence backups."""
    memory_ch = discord.utils.get(guild.text_channels, name="bot-memory")
    if memory_ch:
        return memory_ch

    admin_roles = ["Supreme Leader", "Highness", "Authority"]
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
    }
    for rname in admin_roles:
        r = discord.utils.get(guild.roles, name=rname)
        if r:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, read_message_history=True)

    return await guild.create_text_channel(name="bot-memory", overwrites=overwrites, reason="Arkbot State Persistence Engine")

async def get_or_create_announcements_channel(guild: discord.Guild) -> discord.TextChannel:
    """Finds or automatically creates the public announcements channel with read-only permissions."""
    ch = discord.utils.get(guild.text_channels, name="📢・announcements") or discord.utils.get(guild.text_channels, name="announcements")
    if ch:
        return ch

    welcome_cat = discord.utils.get(guild.categories, name="Welcome")
    admin_roles = ["Supreme Leader", "Highness", "Authority", "Head Moderator", "Moderator", "Trial Mod", "Chill-Verse Team"]

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False, add_reactions=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)
    }
    for rname in admin_roles:
        r = discord.utils.get(guild.roles, name=rname)
        if r:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    return await guild.create_text_channel(
        name="📢・announcements",
        category=welcome_cat,
        overwrites=overwrites,
        reason="Automatic Public Announcement Channel Provisioning"
    )

async def prune_old_backups(channel: discord.TextChannel, keep_count: int = 3):
    """Retains only the newest `keep_count` backup messages and purges older ones."""
    try:
        backup_messages = []
        async for msg in channel.history(limit=100):
            if msg.author == channel.guild.me:
                has_backup_file = any(att.filename == "server_backup.json" for att in msg.attachments)
                has_backup_text = "backup" in msg.content.lower()
                if has_backup_file or has_backup_text:
                    backup_messages.append(msg)

        if len(backup_messages) > keep_count:
            to_delete = backup_messages[keep_count:]
            for old_msg in to_delete:
                try:
                    await old_msg.delete()
                    await asyncio.sleep(0.35)
                except (discord.NotFound, discord.HTTPException):
                    pass
    except Exception as e:
        print(f"Failed to prune old backups in #{channel.name}: {e}")

async def auto_configure_channel(channel):
    """Configures read-only states, staff access, and restrictions on a channel."""
    if isinstance(channel, discord.CategoryChannel):
        return

    guild = channel.guild
    admin_roles = ["Supreme Leader", "Highness", "Authority", "Head Moderator", "Moderator", "Trial Mod", "Chill-Verse Team"]

    cat_name = channel.category.name if channel.category else ""
    is_restricted = cat_name in ["Team <3", "Admin Area 🔒"] or channel.name == "bot-memory"
    is_read_only = channel.name in ["📢・announcements", "server-rules", "📢・level-announcements"]

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False if is_restricted else True,
            send_messages=False if (is_restricted or is_read_only) else True,
            add_reactions=True,
            read_message_history=True
        ),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)
    }

    for rname in admin_roles:
        r = discord.utils.get(guild.roles, name=rname)
        if r:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    try:
        await channel.edit(overwrites=overwrites, reason="Precise Channel Permission & Read-Only Sync")
    except Exception:
        pass

# ==============================================================================
# UI COMPONENTS (MODALS, TICKETS, APPLICATIONS & REACTION ROLES)
# ==============================================================================
class VerificationModal(Modal, title="Server Verification Form"):
    real_full_name = TextInput(label="Real Full Name", placeholder="John Doe", required=True, max_length=50)
    nickname = TextInput(label="Nickname", placeholder="Johnny", required=True, max_length=30)
    dob = TextInput(label="Date of Birth (DD/MM/YYYY)", placeholder="01/01/2005", required=True, max_length=10)
    reason = TextInput(label="Why do you want to join?", style=discord.TextStyle.paragraph, placeholder="Tell us a bit about yourself...", required=True, max_length=500)

    def __init__(self, target_guild: Optional[discord.Guild] = None):
        super().__init__()
        self.target_guild = target_guild

    async def on_submit(self, interaction: discord.Interaction):
        guild = resolve_guild_context(interaction, self.target_guild)
        if not guild:
            return await interaction.response.send_message("⚠️ Error: Could not determine server context. Please verify inside the server channel.", ephemeral=True)

        member = guild.get_member(interaction.user.id)
        if not member:
            try:
                member = await guild.fetch_member(interaction.user.id)
            except discord.HTTPException:
                member = None

        if not member:
            return await interaction.response.send_message("⚠️ Error: Could not find your member profile in the server.", ephemeral=True)

        role = discord.utils.get(guild.roles, name="Member")
        if role:
            try:
                await member.add_roles(role, reason="Completed Verification Modal")
            except discord.Forbidden:
                pass

        log_channel = discord.utils.get(guild.text_channels, name="💼・bot-commands")
        if log_channel:
            embed = discord.Embed(title="New Member Verified", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            embed.add_field(name="User", value=interaction.user.mention, inline=False)
            embed.add_field(name="Real Full Name", value=self.real_full_name.value, inline=True)
            embed.add_field(name="Nickname", value=self.nickname.value, inline=True)
            embed.add_field(name="Date of Birth", value=self.dob.value, inline=True)
            embed.add_field(name="Reason to Join", value=self.reason.value, inline=False)
            try:
                await log_channel.send(embed=embed)
            except discord.HTTPException:
                pass

        await interaction.response.send_message("Verification complete! You now have access to Chill-Verse.", ephemeral=True)

class TeamApplicationModal(Modal, title="Staff Team Application"):
    age_tz = TextInput(label="Age & Timezone", placeholder="18, EST", required=True, max_length=50)
    experience = TextInput(label="Previous Experience", style=discord.TextStyle.paragraph, placeholder="List past moderation experience...", required=True, max_length=300)
    reason = TextInput(label="Why do you want to join the Team?", style=discord.TextStyle.paragraph, placeholder="Tell us why we should choose you...", required=True, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        guild = resolve_guild_context(interaction)
        if not guild:
            return await interaction.response.send_message("⚠️ Error: Server context not found.", ephemeral=True)

        team_channel = discord.utils.get(guild.text_channels, name="💬・team-chat") or discord.utils.get(guild.text_channels, name="team-news")

        embed = discord.Embed(title="🚨 New Staff Application Submitted", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Applicant", value=interaction.user.mention, inline=False)
        embed.add_field(name="Age & Timezone", value=self.age_tz.value, inline=True)
        embed.add_field(name="Previous Experience", value=self.experience.value, inline=False)
        embed.add_field(name="Reason to Join", value=self.reason.value, inline=False)

        if team_channel:
            try:
                await team_channel.send(embed=embed)
            except discord.HTTPException:
                pass

        await interaction.response.send_message("✅ Your application has been successfully submitted to the Team for review!", ephemeral=True)

class RulesView(View):
    def __init__(self, target_guild: Optional[discord.Guild] = None):
        super().__init__(timeout=None)
        self.target_guild = target_guild

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, custom_id="accept_rules")
    async def accept(self, interaction: discord.Interaction, button: Button):
        guild = resolve_guild_context(interaction, self.target_guild)
        if not guild:
            return await interaction.response.send_message("⚠️ Error: Server context not found. Please click Accept inside the server.", ephemeral=True)
        await interaction.response.send_modal(VerificationModal(target_guild=guild))

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red, custom_id="decline_rules")
    async def decline(self, interaction: discord.Interaction, button: Button):
        guild = resolve_guild_context(interaction, self.target_guild)
        if not guild:
            return await interaction.response.send_message("⚠️ Error: Server context ambiguous. Please decline inside the server.", ephemeral=True)

        try:
            await guild.ban(interaction.user, reason="Declined server terms and rules.")
            await interaction.response.send_message("You have been banned for declining the rules.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Error: Bot is missing permission to ban.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"Error handling ban: {e}", ephemeral=True)

class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔒 This ticket will be deleted in 5 seconds...")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason="User closed ticket.")
        except (discord.HTTPException, discord.NotFound):
            pass

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.blurple, custom_id="open_ticket", emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message("Tickets can only be opened inside the server.", ephemeral=True)

        category = discord.utils.get(guild.categories, name="Team <3")
        if not category:
            return await interaction.response.send_message("Error: Team category not found. Run `.setup_channels` first.", ephemeral=True)

        clean_user_name = re.sub(r"[^a-zA-Z0-9_-]", "", interaction.user.name).lower() or "user"
        channel_name = f"ticket-{clean_user_name}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)
        }

        staff_roles = ["Supreme Leader", "Highness", "Authority"]
        for rname in staff_roles:
            role = discord.utils.get(guild.roles, name=rname)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        try:
            ticket_ch = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Ticket opened by {interaction.user.name}"
            )
        except discord.HTTPException as e:
            return await interaction.response.send_message(f"⚠️ Failed to create ticket: {e}", ephemeral=True)

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=f"Welcome {interaction.user.mention}! Please describe your issue here. Only high command can see this ticket.",
            color=discord.Color.blue()
        )

        await ticket_ch.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket created successfully: {ticket_ch.mention}", ephemeral=True)

    @discord.ui.button(label="Apply for Team", style=discord.ButtonStyle.green, custom_id="apply_team", emoji="🛡️")
    async def apply_team(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TeamApplicationModal())

class ReactionRoleView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def toggle_role(self, interaction: discord.Interaction, role_name: str):
        if not interaction.guild:
            return await interaction.response.send_message("Roles can only be toggled in server channels.", ephemeral=True)

        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            return await interaction.response.send_message(f"⚠️ Error: The role `{role_name}` does not exist yet! Run `.setup_roles` first.", ephemeral=True)

        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        if not member:
            return await interaction.response.send_message("Could not verify your membership.", ephemeral=True)

        try:
            if role in member.roles:
                await member.remove_roles(role)
                await interaction.response.send_message(f"❌ Removed role: **{role.name}**", ephemeral=True)
            else:
                await member.add_roles(role)
                await interaction.response.send_message(f"✅ Added role: **{role.name}**", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("⚠️ Error: Bot lacks permission to assign this role (check hierarchy).", ephemeral=True)

    @discord.ui.button(label="🔴 Red", style=discord.ButtonStyle.secondary, custom_id="role_red", row=0)
    async def red_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Red")

    @discord.ui.button(label="🟡 Yellow", style=discord.ButtonStyle.secondary, custom_id="role_yellow", row=0)
    async def yellow_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Yellow")

    @discord.ui.button(label="🟢 Green", style=discord.ButtonStyle.secondary, custom_id="role_green", row=0)
    async def green_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Green")

    @discord.ui.button(label="🔵 Blue", style=discord.ButtonStyle.secondary, custom_id="role_blue", row=1)
    async def blue_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Blue")

    @discord.ui.button(label="🟠 Orange", style=discord.ButtonStyle.secondary, custom_id="role_orange", row=1)
    async def orange_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Orange")

    @discord.ui.button(label="🩷 Pink", style=discord.ButtonStyle.secondary, custom_id="role_pink", row=1)
    async def pink_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Pink")

    @discord.ui.button(label="⏰ Bump Pings", style=discord.ButtonStyle.primary, custom_id="role_bump", row=2)
    async def bump_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Bump Pings")

    @discord.ui.button(label="📊 Poll Pings", style=discord.ButtonStyle.primary, custom_id="role_poll", row=2)
    async def poll_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Poll Pings")

    @discord.ui.button(label="🎮 Roblox Members", style=discord.ButtonStyle.primary, custom_id="role_roblox", row=2)
    async def roblox_role(self, interaction: discord.Interaction, button: Button):
        await self.toggle_role(interaction, "Roblox Members")

# ==============================================================================
# SUBCLASSED BOT & SETUP HOOK
# ==============================================================================
class ArkBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=".", intents=intents)
        self.remove_command("help")

    async def setup_hook(self):
        self.add_view(RulesView())
        self.add_view(TicketView())
        self.add_view(CloseTicketView())
        self.add_view(ReactionRoleView())

        if not hourly_backup_task.is_running():
            hourly_backup_task.start()

bot = ArkBot()

@bot.check
async def check_maintenance_mode(ctx):
    if not MAINTENANCE_MODE:
        return True

    is_admin = getattr(getattr(ctx.author, "guild_permissions", None), "administrator", False)
    staff_roles = {"Supreme Leader", "Highness", "Authority"}
    user_roles = getattr(ctx.author, "roles", [])
    is_high_command = any(role.name in staff_roles for role in user_roles)

    if is_admin or is_high_command:
        return True

    await ctx.send("🛠️ **Maintenance Mode Active:** Arkbot is currently undergoing maintenance. Regular commands are temporarily disabled.", delete_after=6)
    return False

# ==============================================================================
# AUDIT LOGGING & EVENTS
# ==============================================================================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} — Chill-Verse operational.")
    global UPDATE_NOTIFIED
    if not UPDATE_NOTIFIED:
        for guild in bot.guilds:
            team_news_ch = discord.utils.get(guild.text_channels, name="team-news")
            if team_news_ch:
                embed = discord.Embed(
                    title="🚀 Arkbot Updated — Public Announcements System Online!",
                    description="High Command broadcasting active: `.announce` deployed with auto-creating read-only announcements room.",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
                try:
                    await team_news_ch.send(embed=embed)
                except Exception:
                    pass
        UPDATE_NOTIFIED = True

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild:
        return
    log_ch = discord.utils.get(message.guild.text_channels, name="🩸・bot-errors")
    if log_ch:
        content = message.content or "*None (attachment or embed)*"
        if len(content) > 1000:
            content = content[:1000] + "... [truncated]"
        embed = discord.Embed(title="🗑️ Message Deleted", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Author", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Content", value=content, inline=False)
        try:
            await log_ch.send(embed=embed)
        except discord.HTTPException:
            pass

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content:
        return
    log_ch = discord.utils.get(before.guild.text_channels, name="🩸・bot-errors")
    if log_ch:
        b_content = before.content or "*Empty*"
        a_content = after.content or "*Empty*"
        if len(b_content) > 1000:
            b_content = b_content[:1000] + "... [truncated]"
        if len(a_content) > 1000:
            a_content = a_content[:1000] + "... [truncated]"

        embed = discord.Embed(title="✏️ Message Edited", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Author", value=before.author.mention, inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Before", value=b_content, inline=False)
        embed.add_field(name="After", value=a_content, inline=False)
        try:
            await log_ch.send(embed=embed)
        except discord.HTTPException:
            pass

@bot.event
async def on_member_remove(member):
    log_ch = discord.utils.get(member.guild.text_channels, name="🩸・bot-errors")
    if log_ch:
        embed = discord.Embed(title="🚪 Member Left Server", color=discord.Color.dark_grey(), timestamp=discord.utils.utcnow())
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        try:
            await log_ch.send(embed=embed)
        except discord.HTTPException:
            pass

@bot.event
async def on_guild_channel_create(channel):
    await auto_configure_channel(channel)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        return await ctx.send(str(error), delete_after=6)
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"⚠️ **DEBUG ERROR:** {error}")
    print(f"Command Error in {ctx.command}: {error}")

# ==============================================================================
# AUTOMATED HOURLY BACKUP
# ==============================================================================
@tasks.loop(hours=1.0)
async def hourly_backup_task():
    await bot.wait_until_ready()
    for guild in bot.guilds:
        backup_channel = discord.utils.get(guild.text_channels, name="🩸・bot-errors")
        if not backup_channel:
            continue
        backup_data = {
            "server_name": guild.name,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "roles": [{"name": role.name, "permissions": role.permissions.value} for role in guild.roles],
            "text_channels": [{"name": channel.name, "category": str(channel.category)} for channel in guild.text_channels]
        }
        file = discord.File(io.BytesIO(json.dumps(backup_data, indent=4).encode("utf-8")), filename="server_backup.json")
        try:
            await backup_channel.send(content="🔒 **Automated Hourly Backup**", file=file)
            await prune_old_backups(backup_channel, keep_count=3)
        except Exception:
            pass

@bot.event
async def on_member_join(member):
    embed = discord.Embed(
        title="Welcome to Chill-Verse! 🎉",
        description=(
            "**Basic Server Rules:**\n"
            "1. Be respectful, kind, and inclusive to everyone.\n"
            "2. No bullying, hate speech, spam, or toxic behavior.\n"
            "3. Keep conversations teen and family-friendly.\n"
            "4. Follow Discord's Terms of Service at all times.\n\n"
            "To unlock server access, click **Accept** to submit your details via pop-up form, or **Decline** to exit via immediate ban."
        ),
        color=discord.Color.purple()
    )
    sent_dm = False
    try:
        await member.send(embed=embed, view=RulesView(target_guild=member.guild))
        sent_dm = True
    except discord.Forbidden:
        pass

    channel = discord.utils.get(member.guild.text_channels, name="👋・welcome")
    if channel:
        msg = f"{member.mention} Welcome! Please check your DMs to complete verification." if sent_dm else f"{member.mention} (Please enable DMs or click Accept below to verify!)"
        await channel.send(content=msg, embed=embed, view=RulesView(target_guild=member.guild))

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 1. AFK Return Greeting
    if message.author.id in AFK_USERS and not message.content.strip().startswith(f"{bot.command_prefix}afk"):
        del AFK_USERS[message.author.id]
        welcome_template = random.choice(AFK_WELCOME_MESSAGES)
        welcome_embed = discord.Embed(
            description=welcome_template.format(user=message.author.mention),
            color=discord.Color.green()
        )
        await message.channel.send(embed=welcome_embed, delete_after=10)

    # 2. AFK Mention Notice
    if message.mentions:
        for mentioned in message.mentions:
            if mentioned.id in AFK_USERS and mentioned.id != message.author.id:
                afk_info = AFK_USERS[mentioned.id]
                afk_embed = discord.Embed(
                    description=f"💤 **{mentioned.display_name} is currently AFK:**\n*{afk_info['reason']}*",
                    color=discord.Color.dark_purple()
                )
                await message.channel.send(embed=afk_embed, delete_after=10)

    # 3. AutoMod (Only applies to non-staff inside servers)
    if isinstance(message.author, discord.Member) and not is_team_member(message.author):
        if INVITE_REGEX.search(message.content):
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            return await message.channel.send(f"⚠️ {message.author.mention}, posting invite links is prohibited here!", delete_after=4)

        now = discord.utils.utcnow().timestamp()
        timestamps = USER_MESSAGE_TIMESTAMPS[message.author.id]
        timestamps.append(now)
        valid_timestamps = [t for t in timestamps if now - t < 4.0]

        if not valid_timestamps:
            USER_MESSAGE_TIMESTAMPS.pop(message.author.id, None)
        else:
            USER_MESSAGE_TIMESTAMPS[message.author.id] = valid_timestamps

        if len(valid_timestamps) > 5:
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            return await message.channel.send(f"⚠️ {message.author.mention}, please slow down! You are sending messages too quickly.", delete_after=4)

    # 4. Command Execution Filter
    if not is_allowed_channel(message.channel, message.author):
        return

    await bot.process_commands(message)

# ==============================================================================
# HIGH COMMAND ANNOUNCEMENT SYSTEM
# ==============================================================================
@bot.command(name="announce", aliases=["broadcast"])
@is_authority_holder()
async def announce(ctx, *, payload: str = None):
    if not payload:
        return await ctx.send(
            "⚠️ **Please provide content to announce!**\n"
            "**Usage Examples:**\n"
            f"• `{bot.command_prefix}announce Server update completed!`\n"
            f"• `{bot.command_prefix}announce Title | Details of announcement here --everyone`",
            delete_after=7
        )

    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        pass

    guild = ctx.guild
    announcements_ch = await get_or_create_announcements_channel(guild)

    ping_type = None
    if "--everyone" in payload or "--ping" in payload:
        ping_type = "@everyone"
        payload = payload.replace("--everyone", "").replace("--ping", "").strip()
    elif "--here" in payload:
        ping_type = "@here"
        payload = payload.replace("--here", "").strip()

    if "|" in payload:
        parts = payload.split("|", 1)
        title = parts[0].strip()
        description = parts[1].strip()
    else:
        title = "📢 Official Server Announcement"
        description = payload.strip()

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_author(name=f"Announcement by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    embed.set_footer(text="Chill-Verse High Command • Official Broadcast")

    await announcements_ch.send(content=ping_type, embed=embed)
    await ctx.send(f"✅ **Announcement broadcasted successfully to {announcements_ch.mention}!**", delete_after=5)

    log_ch = discord.utils.get(guild.text_channels, name="🩸・bot-errors")
    if log_ch:
        audit_embed = discord.Embed(
            title="📢 Official Announcement Published",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        audit_embed.add_field(name="Announcer", value=ctx.author.mention, inline=True)
        audit_embed.add_field(name="Channel", value=announcements_ch.mention, inline=True)
        audit_embed.add_field(name="Ping", value=str(ping_type or "None"), inline=True)
        audit_embed.add_field(name="Title", value=title, inline=False)
        try:
            await log_ch.send(embed=audit_embed)
        except discord.HTTPException:
            pass

# ==============================================================================
# SPECIFIC BOT ROLE REMOVER & PURGE ENGINE
# ==============================================================================
@bot.command(name="remove_bot_role", aliases=["strip_bot_role", "block_bot_role"])
@is_authority_holder()
async def remove_bot_role(ctx, target: Optional[Union[discord.Role, discord.Member, str]] = None):
    channel = ctx.channel
    guild = ctx.guild

    if not target:
        return await ctx.send(
            "⚠️ **Please specify a target!**\n"
            "**Examples:**\n"
            f"• `{bot.command_prefix}remove_bot_role @BotRole`\n"
            f"• `{bot.command_prefix}remove_bot_role @BotUser`\n"
            f"• `{bot.command_prefix}remove_bot_role all` (removes all bot roles from this room)",
            delete_after=7
        )

    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        pass

    roles_to_block: List[discord.Role] = []

    if isinstance(target, discord.Role):
        roles_to_block.append(target)
    elif isinstance(target, discord.Member):
        if not target.bot:
            return await ctx.send(f"⚠️ {target.mention} is a human user, not a bot.", delete_after=5)
        bot_managed = [r for r in target.roles if r.managed and not r.is_default()]
        if bot_managed:
            roles_to_block.extend(bot_managed)
        else:
            top_r = target.top_role
            if not top_r.is_default() and top_r < guild.me.top_role:
                roles_to_block.append(top_r)
        await channel.set_permissions(target, view_channel=False, send_messages=False, reason=f"Removed by {ctx.author}")
    elif isinstance(target, str) and target.lower() == "all":
        for entity in list(channel.overwrites.keys()):
            if isinstance(entity, discord.Role):
                if (entity.managed and not entity.is_default()) or "bot" in entity.name.lower():
                    if entity != guild.me.top_role and not entity.permissions.administrator:
                        roles_to_block.append(entity)
            elif isinstance(entity, discord.Member) and entity.bot and entity.id != bot.user.id:
                await channel.set_permissions(entity, view_channel=False, send_messages=False)

    if not roles_to_block and not (isinstance(target, discord.Member) and target.bot):
        return await ctx.send("⚠️ No matching bot roles found to remove from this channel.", delete_after=5)

    blocked_names = []
    for r in roles_to_block:
        if r >= guild.me.top_role and r in guild.me.roles:
            continue
        try:
            await channel.set_permissions(
                r,
                view_channel=False,
                send_messages=False,
                reason=f"Bot role stripped from channel by {ctx.author}"
            )
            blocked_names.append(r.name)
            await asyncio.sleep(0.3)
        except discord.Forbidden:
            pass

    summary = ", ".join([f"`{name}`" for name in blocked_names]) or "Target Bot"
    await ctx.send(
        f"🚫 **Channel Bot Role Removal:** Successfully removed/blocked **{summary}** from {channel.mention}!",
        delete_after=6
    )

    log_ch = discord.utils.get(guild.text_channels, name="🩸・bot-errors")
    if log_ch:
        embed = discord.Embed(
            title="🚫 Bot Role Removed From Channel",
            color=discord.Color.dark_grey(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Executor", value=ctx.author.mention, inline=True)
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        embed.add_field(name="Removed Roles", value=summary, inline=False)
        try:
            await log_ch.send(embed=embed)
        except discord.HTTPException:
            pass

@bot.command(name="purge")
@is_authority_holder()
async def purge(ctx, amount: int = 10, target: Optional[Union[discord.Member, str]] = None):
    if amount < 1:
        return await ctx.send("⚠️ You must purge at least 1 message.", delete_after=4)
    if amount > 1000:
        return await ctx.send("⚠️ Safety Cap: Maximum purge limit is 1,000 messages per execution.", delete_after=5)

    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        pass

    def purge_check(m: discord.Message) -> bool:
        if m.pinned:
            return False
        if isinstance(target, discord.Member):
            return m.author.id == target.id
        elif isinstance(target, str):
            t_lower = target.lower()
            if t_lower in ["bot", "bots"]:
                return m.author.bot
            if t_lower in ["link", "links"]:
                return bool(INVITE_REGEX.search(m.content) or "http://" in m.content.lower() or "https://" in m.content.lower())
        return True

    deleted_total = 0
    remaining = amount
    while remaining > 0:
        batch_size = min(remaining, 100)
        try:
            deleted_batch = await ctx.channel.purge(limit=batch_size, check=purge_check)
        except discord.HTTPException as e:
            await ctx.send(f"⚠️ Purge encountered an error (e.g. messages older than 14 days): {e}", delete_after=5)
            break

        deleted_count = len(deleted_batch)
        deleted_total += deleted_count

        if deleted_count < batch_size:
            break

        remaining -= batch_size
        await asyncio.sleep(0.35)

    target_desc = f"from {target.mention}" if isinstance(target, discord.Member) else (f"matching `{target}`" if target else "")
    await ctx.send(f"🧹 **Authority Purge:** Cleared **{deleted_total}** message(s) {target_desc}.", delete_after=4)

    log_ch = discord.utils.get(ctx.guild.text_channels, name="🩸・bot-errors")
    if log_ch:
        embed = discord.Embed(
            title="🧹 Authority Purge Executed",
            color=discord.Color.dark_red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Executor", value=ctx.author.mention, inline=True)
        embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)
        embed.add_field(name="Messages Cleared", value=f"**{deleted_total}** (Scanned: {amount})", inline=True)
        embed.add_field(name="Filter Applied", value=str(target) if target else "None (All Unpinned)", inline=False)
        try:
            await log_ch.send(embed=embed)
        except discord.HTTPException:
            pass

# ==============================================================================
# PERMISSION MEMORY, BACKUPS & BLUEPRINT UPDATER
# ==============================================================================
@bot.command(name="backup")
@commands.has_permissions(administrator=True)
async def backup(ctx):
    guild = ctx.guild
    ch = discord.utils.get(guild.text_channels, name="🩸・bot-errors")
    if not ch:
        return await ctx.send("⚠️ Cannot find `🩸・bot-errors` to store the data.", delete_after=5)

    backup_data = {
        "server_name": guild.name,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "roles": [{"name": role.name, "permissions": role.permissions.value} for role in guild.roles],
        "text_channels": [{"name": channel.name, "category": str(channel.category)} for channel in guild.text_channels]
    }

    file = discord.File(io.BytesIO(json.dumps(backup_data, indent=4).encode("utf-8")), filename="server_backup.json")
    try:
        await ch.send(content=f"🔒 **Manual Backup triggered by {ctx.author.mention}**", file=file)
        await prune_old_backups(ch, keep_count=3)
        await ctx.send("✅ Backup completed successfully! (Only the latest 3 backups are retained)", delete_after=5)
    except Exception as e:
        await ctx.send(f"⚠️ Failed to upload backup: {e}", delete_after=5)

@bot.command(name="backup_perms")
@commands.has_permissions(administrator=True)
async def backup_perms(ctx):
    guild = ctx.guild
    memory_ch = await get_or_create_memory_channel(guild)

    await ctx.send("🔄 **Scanning & serializing channel permissions...**")

    perms_backup = {
        "guild_id": guild.id,
        "guild_name": guild.name,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "categories": {},
        "channels": {}
    }

    for cat in guild.categories:
        cat_overwrites = {}
        for target, overwrite in cat.overwrites.items():
            allow, deny = overwrite.pair()
            target_type = "role" if isinstance(target, discord.Role) else "member"
            cat_overwrites[str(target.id)] = {
                "name": target.name,
                "type": target_type,
                "allow": allow.value,
                "deny": deny.value
            }
        perms_backup["categories"][cat.name] = {
            "id": cat.id,
            "overwrites": cat_overwrites
        }

    for ch in guild.channels:
        if isinstance(ch, discord.CategoryChannel):
            continue
        ch_overwrites = {}
        for target, overwrite in ch.overwrites.items():
            allow, deny = overwrite.pair()
            target_type = "role" if isinstance(target, discord.Role) else "member"
            ch_overwrites[str(target.id)] = {
                "name": target.name,
                "type": target_type,
                "allow": allow.value,
                "deny": deny.value
            }
        perms_backup["channels"][ch.name] = {
            "id": ch.id,
            "category": ch.category.name if ch.category else None,
            "type": str(ch.type),
            "overwrites": ch_overwrites
        }

    data_stream = io.BytesIO(json.dumps(perms_backup, indent=4).encode("utf-8"))
    file = discord.File(data_stream, filename=f"channel_perms_memory_{guild.id}.json")

    embed = discord.Embed(
        title="🔒 Channel Permission Memory Snapshot",
        description=f"Exported permissions for **{len(perms_backup['channels'])}** channels and **{len(perms_backup['categories'])}** categories.",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    await memory_ch.send(embed=embed, file=file)
    await ctx.send(f"✅ Channel permissions memory successfully preserved in {memory_ch.mention}!")

@bot.command(name="backup_channels")
@commands.has_permissions(administrator=True)
async def backup_channels(ctx):
    guild = ctx.guild
    memory_ch = await get_or_create_memory_channel(guild)

    await ctx.send("🔄 **Preserving server channel names and structure...**")

    structure = {
        "guild_id": guild.id,
        "guild_name": guild.name,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "categories": []
    }

    for cat in guild.categories:
        cat_payload = {
            "name": cat.name,
            "position": cat.position,
            "channels": []
        }
        for ch in cat.channels:
            ch_data = {
                "name": ch.name,
                "type": str(ch.type),
                "position": ch.position,
                "user_limit": getattr(ch, "user_limit", None)
            }
            cat_payload["channels"].append(ch_data)
        structure["categories"].append(cat_payload)

    orphans = [
        {"name": ch.name, "type": str(ch.type), "position": ch.position}
        for ch in guild.channels
        if not ch.category and not isinstance(ch, discord.CategoryChannel)
    ]
    structure["uncategorized"] = orphans

    data_stream = io.BytesIO(json.dumps(structure, indent=4).encode("utf-8"))
    file = discord.File(data_stream, filename=f"channel_names_layout_{guild.id}.json")

    embed = discord.Embed(
        title="📁 Server Channel Names & Structure Snapshot",
        description="Saved complete structural layout with channel names and positioning.",
        color=discord.Color.teal(),
        timestamp=discord.utils.utcnow()
    )
    await memory_ch.send(embed=embed, file=file)
    await ctx.send(f"✅ Channel hierarchy names safely archived into {memory_ch.mention}!")

@bot.command(name="update_blueprint")
@commands.has_permissions(administrator=True)
async def update_blueprint(ctx):
    global SERVER_BLUEPRINT
    guild = ctx.guild
    memory_ch = await get_or_create_memory_channel(guild)

    await ctx.send("🔍 **Analyzing live server configuration to generate dynamic blueprint...**")

    new_blueprint = []
    for cat in guild.categories:
        cat_data = {
            "category": cat.name,
            "channels": []
        }
        for ch in cat.channels:
            if ch.name == "bot-memory":
                continue

            ch_type = "text"
            if isinstance(ch, discord.VoiceChannel):
                ch_type = "voice"
            elif isinstance(ch, getattr(discord, "ForumChannel", ())):
                ch_type = "forum"

            default_overwrite = ch.overwrites.get(guild.default_role)
            is_restricted = False
            is_read_only = False
            if default_overwrite:
                if default_overwrite.view_channel is False:
                    is_restricted = True
                if default_overwrite.send_messages is False:
                    is_read_only = True
            elif cat.name in ["Team <3", "Admin Area 🔒"]:
                is_restricted = True

            ch_entry = {
                "name": ch.name,
                "type": ch_type,
                "restricted": is_restricted,
                "read_only": is_read_only
            }
            if ch_type == "voice" and getattr(ch, "user_limit", 0) > 0:
                ch_entry["user_limit"] = ch.user_limit

            cat_data["channels"].append(ch_entry)

        if cat_data["channels"]:
            new_blueprint.append(cat_data)

    SERVER_BLUEPRINT = new_blueprint

    blueprint_stream = io.BytesIO(json.dumps(SERVER_BLUEPRINT, indent=4).encode("utf-8"))
    file = discord.File(blueprint_stream, filename=f"server_blueprint_live_{guild.id}.json")

    embed = discord.Embed(
        title="⚡ Automatic Blueprint Update Complete",
        description=(
            f"Successfully extracted **{len(SERVER_BLUEPRINT)}** categories into the active deployment engine.\n"
            "Any future execution of `.setup_channels` will now recreate this topology!"
        ),
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    await memory_ch.send(embed=embed, file=file)
    await ctx.send(f"✅ **Server Blueprint Updated!** Active memory synced and blueprint schema saved to {memory_ch.mention}.")

# ==============================================================================
# GENERAL & ADMINISTRATIVE COMMANDS
# ==============================================================================
@bot.command(name="afk")
async def afk(ctx, *, reason: str = None):
    selected_status = reason if reason else random.choice(AFK_PRESET_MESSAGES)
    AFK_USERS[ctx.author.id] = {
        "reason": selected_status,
        "time": discord.utils.utcnow()
    }

    embed = discord.Embed(
        description=f"🌙 **{ctx.author.display_name} is now AFK**\n*{selected_status}*",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed, delete_after=10)
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        pass

@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 **Pong!** Bot is online. Latency: `{latency}ms`")

@bot.command(name="maintenance")
@commands.has_permissions(administrator=True)
async def maintenance(ctx):
    global MAINTENANCE_MODE
    MAINTENANCE_MODE = not MAINTENANCE_MODE

    if MAINTENANCE_MODE:
        await bot.change_presence(status=discord.Status.dnd, activity=discord.Game(name="⚠️ Under Maintenance"))
        await ctx.send("🛠️ **Maintenance Mode: 🟢 ENABLED**\nRegular member commands are locked. High Command and Admins retain full access.")
    else:
        await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="Chill-Verse | .setup_help"))
        await ctx.send("🛠️ **Maintenance Mode: 🔴 DISABLED**\nNormal server operations and member commands have been restored.")

@bot.command(name="auto_team")
@commands.has_permissions(administrator=True)
async def auto_team(ctx):
    await ctx.send("🔄 **Auto-Team Sync:** Applying team roles and public/restricted barriers...")
    admin_roles = ["Supreme Leader", "Highness", "Authority", "Head Moderator", "Moderator", "Trial Mod", "Chill-Verse Team"]
    guild = ctx.guild

    for category in guild.categories:
        cat_name = category.name
        is_restricted = cat_name in ["Team <3", "Admin Area 🔒"]
        overwrites = category.overwrites
        overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False if is_restricted else True)
        overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)

        for rname in admin_roles:
            r = discord.utils.get(guild.roles, name=rname)
            if r:
                overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        try:
            await category.edit(overwrites=overwrites, reason="Auto-team category permission sync")
            await asyncio.sleep(0.35)
        except Exception:
            pass

    for channel in guild.channels:
        if isinstance(channel, discord.CategoryChannel):
            continue
        await auto_configure_channel(channel)
        await asyncio.sleep(0.35)

    await ctx.send("✅ **Auto-Team Complete:** Team roles assigned everywhere. Only **Team <3** and **Admin Area 🔒** are restricted from the public!")

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 **Channel Locked:** Standard members can no longer send messages here.")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
    await ctx.send("🔓 **Channel Unlocked:** Standard members can now send messages here.")

@bot.command(name="hide")
@commands.has_permissions(manage_channels=True)
async def hide(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=False)
    await ctx.send("👻 **Channel Hidden:** This channel is now invisible to standard members.")

@bot.command(name="show")
@commands.has_permissions(manage_channels=True)
async def show(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=True)
    await ctx.send("👁️ **Channel Visible:** Standard members can now see this channel.")

@bot.command(name="permit")
@commands.has_permissions(manage_channels=True)
async def permit(ctx, target: Union[discord.Member, discord.Role]):
    await ctx.channel.set_permissions(target, view_channel=True, send_messages=True, read_message_history=True)
    await ctx.send(f"✅ **Access Granted:** {target.mention} can now view and type in this channel.")

@bot.command(name="revoke")
@commands.has_permissions(manage_channels=True)
async def revoke(ctx, target: Union[discord.Member, discord.Role]):
    await ctx.channel.set_permissions(target, view_channel=False, send_messages=False)
    await ctx.send(f"❌ **Access Revoked:** {target.mention} has been removed from this channel.")

@bot.command(name="permit_all")
@commands.has_permissions(administrator=True)
async def permit_all(ctx, target: Union[discord.Member, discord.Role]):
    await ctx.send(f"🔄 **Global Sync:** Granting {target.mention} access to all channels... Please wait.")
    count = 0
    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(target, view_channel=True, send_messages=True, read_message_history=True)
            count += 1
            await asyncio.sleep(0.35)
        except Exception:
            pass
    await ctx.send(f"✅ **Global Access Granted:** {target.mention} can now view and type in **{count}** channels!")

@bot.command(name="revoke_all")
@commands.has_permissions(administrator=True)
async def revoke_all(ctx, target: Union[discord.Member, discord.Role]):
    await ctx.send(f"🔄 **Global Sync:** Revoking {target.mention}'s access from all channels... Please wait.")
    count = 0
    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(target, view_channel=False, send_messages=False)
            count += 1
            await asyncio.sleep(0.35)
        except Exception:
            pass
    await ctx.send(f"❌ **Global Access Revoked:** {target.mention} has been completely locked out of **{count}** channels.")

@bot.command(name="edit_role")
@commands.has_permissions(administrator=True)
async def edit_role(ctx, role: discord.Role, permission_name: str, value: bool):
    if role >= ctx.guild.me.top_role:
        return await ctx.send("⚠️ **Error:** I cannot modify a role higher than or equal to my own bot role!")

    permission_name = permission_name.lower().replace(" ", "_")
    if not hasattr(discord.Permissions, permission_name):
        return await ctx.send(f"⚠️ **Error:** `{permission_name}` is not a valid Discord permission name.")

    perms = role.permissions
    setattr(perms, permission_name, value)
    try:
        await role.edit(permissions=perms, reason=f"Permission changed by {ctx.author}")
        status = "🟢 ENABLED" if value else "🔴 DISABLED"
        await ctx.send(f"✅ Successfully updated **{role.name}**!\n{status}: `{permission_name}`")
    except Exception as e:
        await ctx.send(f"⚠️ **Error updating role:** {e}")

# ==============================================================================
# ROLES & BLUEPRINT DEPLOYMENT
# ==============================================================================
@bot.command(name="nuke_roles")
@commands.has_permissions(administrator=True)
async def nuke_roles(ctx):
    await ctx.send("☢️ **ROLE NUKE INITIATED:** Wiping all custom server roles. Please wait...")
    deleted_count = 0
    skipped_count = 0

    for role in list(ctx.guild.roles):
        if role.is_default() or role.managed or role >= ctx.guild.me.top_role:
            skipped_count += 1
            continue
        try:
            await role.delete(reason=f"Role Nuke initiated by {ctx.author}")
            deleted_count += 1
            await asyncio.sleep(0.4)
        except Exception as e:
            skipped_count += 1
            print(f"Skipped role {role.name}: {e}")

    await ctx.send(f"✅ **ROLE NUKE COMPLETE:** Wiped **{deleted_count}** roles. (Skipped/Protected: **{skipped_count}**)\n➡️ You can now run `.setup_roles` to build the fresh hierarchy!")

@bot.command(name="setup_roles")
@commands.has_permissions(administrator=True)
async def setup_roles(ctx):
    guild = ctx.guild
    await ctx.send("⚙️ Setting up ALL Chill-Verse roles... This will take ~15 seconds to avoid Discord rate limits.")

    base_perms = discord.Permissions(send_messages=True, read_messages=True, connect=True, speak=True)

    roles_to_create = [
        {"name": "Supreme Leader", "perms": discord.Permissions(administrator=True), "color": discord.Color.dark_red(), "hoist": True},
        {"name": "Highness", "perms": discord.Permissions(administrator=True), "color": discord.Color.gold(), "hoist": True},
        {"name": "Authority", "perms": discord.Permissions(ban_members=True, kick_members=True, manage_channels=True, manage_roles=True), "color": discord.Color.orange(), "hoist": True},
        {"name": "Head Moderator", "perms": discord.Permissions(ban_members=True, kick_members=True, moderate_members=True, manage_messages=True), "color": discord.Color.red(), "hoist": True},
        {"name": "Moderator", "perms": discord.Permissions(kick_members=True, moderate_members=True, manage_messages=True), "color": discord.Color.yellow(), "hoist": True},
        {"name": "Trial Mod", "perms": discord.Permissions(moderate_members=True, manage_messages=True), "color": discord.Color.blue(), "hoist": True},
        {"name": "Chill-Verse Team", "perms": discord.Permissions(view_channel=True, send_messages=True, read_message_history=True), "color": getattr(discord.Color, "dark_theme", lambda: discord.Color(0x313338))(), "hoist": True},
        {"name": "Sovereign (Levels 60-70)", "perms": base_perms, "color": discord.Color.purple(), "hoist": True},
        {"name": "Legend (Levels 50-59)", "perms": base_perms, "color": discord.Color.dark_purple(), "hoist": False},
        {"name": "Champion (Levels 40-49)", "perms": base_perms, "color": getattr(discord.Color, "brand_red", lambda: discord.Color(0xED4245))(), "hoist": False},
        {"name": "Elite (Levels 30-39)", "perms": base_perms, "color": discord.Color.dark_green(), "hoist": False},
        {"name": "Vanguard (Levels 20-29)", "perms": base_perms, "color": discord.Color.green(), "hoist": False},
        {"name": "Explorer (Levels 10-19)", "perms": base_perms, "color": discord.Color.teal(), "hoist": False},
        {"name": "Newbie (Levels 1-9)", "perms": base_perms, "color": discord.Color.light_grey(), "hoist": False},
        {"name": "Member", "perms": base_perms, "color": discord.Color.default(), "hoist": False},
        {"name": "OG", "perms": base_perms, "color": discord.Color.dark_gold(), "hoist": False},
        {"name": "Veteran", "perms": base_perms, "color": discord.Color.dark_grey(), "hoist": False},
        {"name": "Vanity", "perms": base_perms, "color": discord.Color.magenta(), "hoist": False},
        {"name": "Bump Pings", "perms": discord.Permissions.none(), "color": discord.Color.default(), "hoist": False},
        {"name": "Poll Pings", "perms": discord.Permissions.none(), "color": discord.Color.default(), "hoist": False},
        {"name": "Roblox Members", "perms": discord.Permissions.none(), "color": discord.Color.default(), "hoist": False},
        {"name": "Male", "perms": discord.Permissions.none(), "color": discord.Color.default(), "hoist": False},
        {"name": "Female", "perms": discord.Permissions.none(), "color": discord.Color.default(), "hoist": False},
        {"name": "Non-Binary", "perms": discord.Permissions.none(), "color": discord.Color.default(), "hoist": False},
        {"name": "Yellow", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(255, 255, 0), "hoist": False},
        {"name": "Red", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(255, 0, 0), "hoist": False},
        {"name": "Pink", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(255, 105, 180), "hoist": False},
        {"name": "Orange", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(255, 165, 0), "hoist": False},
        {"name": "Blue", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(0, 0, 255), "hoist": False},
        {"name": "Green", "perms": discord.Permissions.none(), "color": discord.Color.from_rgb(0, 128, 0), "hoist": False},
    ]

    created_count = 0
    for role_data in roles_to_create:
        if not discord.utils.get(guild.roles, name=role_data["name"]):
            try:
                await guild.create_role(
                    name=role_data["name"],
                    permissions=role_data["perms"],
                    color=role_data["color"],
                    hoist=role_data["hoist"],
                    reason="Chill-Verse bulk role setup"
                )
                created_count += 1
                await asyncio.sleep(0.4)
            except Exception as e:
                print(f"Failed to create role {role_data['name']}: {e}")

    await ctx.send(f"✅ Full server role integration complete! Created **{created_count}** new roles.")

@bot.command(name="nuke_channels")
@commands.has_permissions(administrator=True)
async def nuke_channels(ctx):
    await ctx.send("☢️ **NUKE INITIATED:** Wiping all other channels and categories. Please wait...")
    deleted_count = 0
    skipped_count = 0

    for channel in list(ctx.guild.channels):
        if channel.id == ctx.channel.id or isinstance(channel, discord.CategoryChannel):
            continue
        try:
            await channel.delete(reason=f"Server Nuke initiated by {ctx.author}")
            deleted_count += 1
            await asyncio.sleep(0.35)
        except Exception:
            skipped_count += 1

    for category in list(ctx.guild.categories):
        if category.id == ctx.channel.category_id:
            continue
        try:
            await category.delete(reason=f"Server Nuke initiated by {ctx.author}")
            deleted_count += 1
            await asyncio.sleep(0.35)
        except Exception:
            skipped_count += 1

    await ctx.send(f"✅ **NUKE COMPLETE:** Wiped **{deleted_count}** channels/categories. (Skipped: **{skipped_count}**)\n➡️ Run `.setup_channels` to recreate blueprint.")

@bot.command(name="setup_channels")
@commands.has_permissions(administrator=True)
async def setup_channels(ctx):
    guild = ctx.guild
    admin_roles = ["Supreme Leader", "Highness", "Authority", "Head Moderator", "Moderator", "Trial Mod", "Chill-Verse Team"]

    await ctx.send("🏗️ Deploying current server blueprint... Team has absolute access; only Team & Admin categories are restricted.")

    for cat_data in SERVER_BLUEPRINT:
        cat_name = cat_data["category"]
        category = discord.utils.get(guild.categories, name=cat_name)

        if not category:
            category = await guild.create_category(name=cat_name)

        for ch_info in cat_data["channels"]:
            ch_name = ch_info["name"]
            ch_type = ch_info["type"]
            is_restricted = ch_info.get("restricted", False)
            is_read_only = ch_info.get("read_only", False)
            user_lim = ch_info.get("user_limit", 0)

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    view_channel=False if is_restricted else True,
                    send_messages=False if (is_restricted or is_read_only) else True,
                    add_reactions=True,
                    read_message_history=True
                ),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)
            }
            for rname in admin_roles:
                r = discord.utils.get(guild.roles, name=rname)
                if r:
                    overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

            if ch_type == "text":
                existing = discord.utils.get(category.text_channels, name=ch_name)
                if not existing:
                    await guild.create_text_channel(name=ch_name, category=category, overwrites=overwrites)
            elif ch_type == "voice":
                existing = discord.utils.get(category.voice_channels, name=ch_name)
                if not existing:
                    await guild.create_voice_channel(name=ch_name, category=category, user_limit=user_lim, overwrites=overwrites)
            elif ch_type == "forum":
                existing = discord.utils.get(guild.channels, name=ch_name)
                if not existing:
                    try:
                        await guild.create_forum_channel(name=ch_name, category=category, overwrites=overwrites)
                    except Exception:
                        await guild.create_text_channel(name=ch_name, category=category, overwrites=overwrites)

            await asyncio.sleep(0.35)

    await get_or_create_memory_channel(guild)
    await ctx.send("✅ Server channels deployed successfully based on the active blueprint!")

@bot.command(name="setup_tickets")
@commands.has_permissions(administrator=True)
async def setup_tickets(ctx):
    ch = discord.utils.get(ctx.guild.text_channels, name="🎫・tickets")
    if not ch:
        return await ctx.send("⚠️ Cannot find `🎫・tickets`. Please run `.setup_channels` first.")

    embed = discord.Embed(
        title="🎫 Chill-Verse Support & Staff Applications",
        description="Need help from staff, want to report an issue, or apply to join the Team?\n\nChoose an option using the buttons below:\n*(Note: Private tickets are visible only to Authority, Highness, and Supreme Leader)*",
        color=discord.Color.blue()
    )
    await ch.send(embed=embed, view=TicketView())
    await ctx.send("✅ Support & Application panel successfully deployed to `🎫・tickets`!")

@bot.command(name="setup_roles_panel")
@commands.has_permissions(administrator=True)
async def setup_roles_panel(ctx):
    ch = discord.utils.get(ctx.guild.text_channels, name="🎨・colours")
    if not ch:
        return await ctx.send("⚠️ Cannot find `🎨・colours`. Please run `.setup_channels` first.")

    embed = discord.Embed(
        title="🎨 Chill-Verse Custom Roles & Pings",
        description="Click any button below to instantly toggle your favorite color or community notification pings on or off!",
        color=discord.Color.magenta()
    )
    await ch.send(embed=embed, view=ReactionRoleView())
    await ctx.send("✅ Color & Ping reaction role panel successfully deployed to `🎨・colours`!")

@bot.command(name="setup_help")
@commands.has_permissions(administrator=True)
async def setup_help(ctx):
    ch = discord.utils.get(ctx.guild.text_channels, name="💼・bot-commands")
    if not ch:
        return await ctx.send("⚠️ Cannot find `💼・bot-commands`. Please run `.setup_channels` first.")

    embed = discord.Embed(
        title="🤖 Arkbot Master Command Manual",
        description="Full operational suite for Chill-Verse architecture, permission memory, and automated backups.",
        color=discord.Color.purple()
    )

    embed.add_field(
        name="📢 High Command Broadcast",
        value=(
            "`.announce <text>` — Sends an official broadcast to `📢・announcements`.\n"
            "`.announce <Title> | <Content> [--everyone/--here]` — Posts an embed broadcast with role pings.\n"
            "*(Only High Command can post; regular members can only read and view.)*"
        ),
        inline=False
    )

    embed.add_field(
        name="🧹 Security & Purge Suite",
        value=(
            "`.purge <amount> [user/bots/links]` — Authority surgical cleaner (up to 1,000 unpinned).\n"
            "`.remove_bot_role <@role / @bot / all>` — Locks bot roles out of the current channel."
        ),
        inline=False
    )

    embed.add_field(
        name="💾 Memory & Backup Commands",
        value=(
            "`.backup` — Raw JSON backup to `🩸・bot-errors` (Retains latest 3).\n"
            "`.backup_perms` — Snapshots all channel and category permissions into `bot-memory`.\n"
            "`.backup_channels` — Backs up complete channel names, types, and hierarchy.\n"
            "`.update_blueprint` — ⚡ Auto-syncs live server channels to blueprint in memory."
        ),
        inline=False
    )

    embed.add_field(
        name="🛠️ Architecture & Setup",
        value=(
            "`.setup_channels` — Deploys current blueprint.\n"
            "`.setup_roles` — Generates full 31-role hierarchy.\n"
            "`.setup_tickets` — Drops ticket & application panel.\n"
            "`.setup_roles_panel` — Drops self-assignable role buttons.\n"
            "`.auto_team` — Synchronizes team permissions server-wide.\n"
            "`.maintenance` — Toggles server lockdown mode."
        ),
        inline=False
    )

    embed.set_footer(text="Arkbot Architecture Engine • Prefix: .")
    await ch.send(embed=embed)
    await ctx.send("✅ Command manual posted to `💼・bot-commands`!")

# ==============================================================================
# RUN BOT
# ==============================================================================
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("⚠️ CRITICAL ERROR: 'DISCORD_BOT_TOKEN' environment variable is missing!")
    else:
        bot.run(TOKEN)
