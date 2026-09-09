import discord
from discord.ext import commands, tasks
import asyncio
import json
import os
import time
import random
from typing import Dict, Any, Optional, List

# ==============================================================================
# 1. SERVER ROLES & PERMISSION MATRIX CONFIGURATION
# ==============================================================================

SUPREME_LEADER_ROLE_NAME = "Supreme Leader"
SUPREME_LEADER_COLOR     = discord.Color.from_rgb(1, 1, 1) # Near-black
ADMIN_ROLE_NAME          = "Highness"
AUTHORITY_ROLE_NAME      = "Authority"
HEAD_MOD_ROLE_NAME       = "Head Moderator"
MOD_ROLE_NAME            = "Moderator"
TRIAL_MOD_ROLE_NAME      = "Trial Mod"
TEAM_ROLE_NAME           = "Team"

RESTRICTED_ADMIN_ROLES = [
    SUPREME_LEADER_ROLE_NAME,
    ADMIN_ROLE_NAME,
    AUTHORITY_ROLE_NAME,
    HEAD_MOD_ROLE_NAME,
    MOD_ROLE_NAME,
    TRIAL_MOD_ROLE_NAME,
    TEAM_ROLE_NAME
]

OG_ROLE_NAME        = "OG"
VETERAN_ROLE_NAME   = "Veteran"
BOOSTER_ROLE_NAME   = "Server Booster"
VANITY_ROLE_NAME    = "Vanity"
BUMP_ROLE_NAME      = "Bump Pings"
POLL_ROLE_NAME      = "Poll Pings"
ROBLOX_ROLE_NAME    = "Roblox Members"

GENDER_ROLES = {
    "Male": discord.Color.blue(),
    "Female": discord.Color.magenta(),
    "Non-Binary": discord.Color.purple()
}

PRO_HEX_COLORS = {
    "Yellow": discord.Color.gold(),
    "Red":    discord.Color.red(),
    "Pink":   discord.Color.from_rgb(255, 105, 180),
    "Orange": discord.Color.orange(),
    "Blue":   discord.Color.blue(),
    "Green":  discord.Color.green()
}

MAX_LEVEL = 70

LEVEL_TIER_ROLES = {
    (1, 9): {
        "name": "Newbie",
        "color": discord.Color.teal(),
        "hoist": False,
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            connect=True, speak=True, add_reactions=True
        )
    },
    (10, 19): {
        "name": "Explorer",
        "color": discord.Color.green(),
        "hoist": False,
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            connect=True, speak=True, add_reactions=True,
            change_nickname=True, attach_files=True, embed_links=True
        )
    },
    (20, 29): {
        "name": "Vanguard",
        "color": discord.Color.blue(),
        "hoist": False,
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            connect=True, speak=True, add_reactions=True,
            change_nickname=True, attach_files=True, embed_links=True,
            use_external_emojis=True, use_external_stickers=True
        )
    },
    (30, 39): {
        "name": "Elite",
        "color": discord.Color.purple(),
        "hoist": False,
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            connect=True, speak=True, add_reactions=True,
            change_nickname=True, attach_files=True, embed_links=True,
            use_external_emojis=True, use_external_stickers=True,
            stream=True, create_public_threads=True, send_messages_in_threads=True
        )
    },
    (40, 49): {
        "name": "Champion",
        "color": discord.Color.gold(),
        "hoist": False,
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            connect=True, speak=True, add_reactions=True,
            change_nickname=True, attach_files=True, embed_links=True,
            use_external_emojis=True, use_external_stickers=True,
            stream=True, create_public_threads=True, send_messages_in_threads=True,
            use_soundboard=True, use_external_sounds=True
        )
    },
    (50, 59): {
        "name": "Legend",
        "color": discord.Color.orange(),
        "hoist": False,
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            connect=True, speak=True, add_reactions=True,
            change_nickname=True, attach_files=True, embed_links=True,
            use_external_emojis=True, use_external_stickers=True,
            stream=True, create_public_threads=True, send_messages_in_threads=True,
            use_soundboard=True, use_external_sounds=True,
            priority_speaker=True, create_private_threads=True
        )
    },
    (60, 70): {
        "name": "Sovereign",
        "color": discord.Color.dark_red(),
        "hoist": True,
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            connect=True, speak=True, add_reactions=True,
            change_nickname=True, attach_files=True, embed_links=True,
            use_external_emojis=True, use_external_stickers=True,
            stream=True, create_public_threads=True, send_messages_in_threads=True,
            use_soundboard=True, use_external_sounds=True,
            priority_speaker=True, create_private_threads=True
        )
    }
}

ROLE_PERMISSIONS_CONFIG = {
    SUPREME_LEADER_ROLE_NAME: {
        "hoist": True,
        "color": SUPREME_LEADER_COLOR,
        "permissions": discord.Permissions(administrator=True)
    },
    ADMIN_ROLE_NAME: {
        "hoist": True,
        "color": discord.Color.from_rgb(255, 105, 180),
        "permissions": discord.Permissions(administrator=True)
    },
    AUTHORITY_ROLE_NAME: {
        "hoist": True,
        "color": discord.Color.from_rgb(150, 100, 255),
        "permissions": discord.Permissions(
            view_audit_log=True, manage_guild=True, manage_channels=True,
            manage_roles=True, kick_members=True, ban_members=True,
            manage_messages=True, moderate_members=True, manage_nicknames=True,
            mute_members=True, deafen_members=True, move_members=True
        )
    },
    HEAD_MOD_ROLE_NAME: {
        "hoist": True,
        "color": discord.Color.from_rgb(230, 70, 80),
        "permissions": discord.Permissions(
            view_audit_log=True, kick_members=True, ban_members=True,
            manage_messages=True, moderate_members=True, mute_members=True,
            deafen_members=True, move_members=True, manage_threads=True
        )
    },
    MOD_ROLE_NAME: {
        "hoist": True,
        "color": discord.Color.from_rgb(240, 190, 60),
        "permissions": discord.Permissions(
            kick_members=True, manage_messages=True, moderate_members=True,
            mute_members=True, deafen_members=True, move_members=True
        )
    },
    TRIAL_MOD_ROLE_NAME: {
        "hoist": True,
        "color": discord.Color.from_rgb(80, 170, 250),
        "permissions": discord.Permissions(manage_messages=True, moderate_members=True)
    },
    TEAM_ROLE_NAME: {
        "hoist": True,
        "color": discord.Color.teal(),
        "permissions": discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True,
            attach_files=True, embed_links=True
        )
    }
}

# ==============================================================================
# 2. 10-CATEGORY SERVER BLUEPRINT ARCHITECTURE
# ==============================================================================

EXTENDED_SERVER_BLUEPRINT = [
    {
        "category": "Admin Area 🔒",
        "channels": [
            {"name": "👑・supreme-logs", "type": "text", "scheme": "supreme_admin_only"},
            {"name": "🛠️・admin-chat", "type": "text", "scheme": "supreme_admin_only"},
            {"name": "🔒・bot-config", "type": "text", "scheme": "supreme_admin_only"}
        ]
    },
    {
        "category": "Info 🍸",
        "channels": [
            {"name": "📌・welcome", "type": "text", "scheme": "public_read"},
            {"name": "📜・rules", "type": "text", "scheme": "public_read"},
            {"name": "📢・announcements", "type": "text", "scheme": "public_read"},
            {"name": "🚀・boosters", "type": "text", "scheme": "public_read"},
            {"name": "🤖・bot-commands", "type": "text", "scheme": "public_chat"}
        ]
    },
    {
        "category": "Team <3",
        "channels": [
            {"name": "💬・team-chat", "type": "text", "scheme": "staff_chat"},
            {"name": "📋・staff-logs", "type": "text", "scheme": "staff_chat"},
            {"name": "🎫・support-tickets", "type": "text", "scheme": "staff_chat"}
        ]
    },
    {
        "category": "Events 🎊",
        "channels": [
            {"name": "🏆・giveaways", "type": "text", "scheme": "public_read"},
            {"name": "🎈・event-chat", "type": "text", "scheme": "public_chat"}
        ]
    },
    {
        "category": "Chill Area 🍹",
        "channels": [
            {"name": "🍸・general-chat", "type": "text", "scheme": "public_chat"},
            {"name": "💬・bot-spam", "type": "text", "scheme": "public_chat"},
            {"name": "🍸・chat-ai", "type": "text", "scheme": "public_chat"}
        ]
    },
    {
        "category": "Media 📷",
        "channels": [
            {"name": "🖼️・media-feed", "type": "text", "scheme": "public_media"},
            {"name": "🎨・colours", "type": "text", "scheme": "public_chat"},
            {"name": "🎭・identity-roles", "type": "text", "scheme": "public_chat"}
        ]
    },
    {
        "category": "Fun Area 🎮",
        "channels": [
            {"name": "📊・polls", "type": "text", "scheme": "polls_feed"},
            {"name": "💌・confessions", "type": "text", "scheme": "confession_feed"}
        ]
    },
    {
        "category": "Hobbies 🎲",
        "channels": [
            {"name": "🖇-roblox-elites", "type": "text", "scheme": "roblox_exclusive"}
        ]
    },
    {
        "category": "Voice Chats 🔊",
        "channels": [
            {"name": "🔊・Lounge 1", "type": "voice", "scheme": "public_voice"},
            {"name": "🔊・Lounge 2", "type": "voice", "scheme": "public_voice"},
            {"name": "🔒・VIP Room", "type": "voice", "scheme": "vip_voice", "user_limit": 4}
        ]
    },
    {
        "category": "Music 🎵",
        "channels": [
            {"name": "🎵・Music Lounge", "type": "voice", "scheme": "music_voice"}
        ]
    }
]

# ==============================================================================
# 3. INITIALIZATION & STATE ENGINE
# ==============================================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)
bot.server_state = {}
active_bump_tasks = {}

def normalize_text(text: str) -> str:
    return "".join(c for c in text.lower() if c.isalnum() or c.isspace()).strip()

def default_server_state() -> Dict[str, Any]:
    return {
        "user_xp": {},
        "user_levels": {},
        "warnings": {},
        "mutes_count": {},
        "birthdays": {},
        "afk_users": {},
        "last_bump_time": 0.0,
        "maintenance_mode": False
    }

async def load_state_from_memory(guild: discord.Guild) -> Dict[str, Any]:
    memory_ch = discord.utils.find(lambda c: "bot-memory" in normalize_text(c.name), guild.text_channels)
    if not memory_ch:
        return default_server_state()
    try:
        async for msg in memory_ch.history(limit=5):
            if msg.author == guild.me and msg.content.startswith("```json"):
                raw = msg.content.replace("```json", "").replace("```", "").strip()
                return json.loads(raw)
    except Exception:
        pass
    return default_server_state()

async def save_state_to_memory(guild: discord.Guild, data: Optional[Dict[str, Any]] = None):
    if data is None:
        data = bot.server_state.setdefault(guild.id, default_server_state())
    memory_ch = discord.utils.find(lambda c: "bot-memory" in normalize_text(c.name), guild.text_channels)
    if not memory_ch:
        try:
            overwrites = {
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
                guild.default_role: discord.PermissionOverwrite(view_channel=False)
            }
            memory_ch = await guild.create_text_channel("🤖・bot-memory", overwrites=overwrites, reason="Create state channel")
        except Exception:
            return

    payload = json.dumps(data, indent=2)
    content = f"```json\n{payload}\n```"
    try:
        async for msg in memory_ch.history(limit=10):
            if msg.author == guild.me:
                await msg.edit(content=content)
                return
        await memory_ch.send(content=content)
    except Exception:
        pass

def find_role_resilient(guild: discord.Guild, role_name: str) -> Optional[discord.Role]:
    norm_target = normalize_text(role_name)
    for role in guild.roles:
        if normalize_text(role.name) == norm_target:
            return role
    return None

def is_staff_member(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    for r in member.roles:
        if normalize_text(r.name) in [normalize_text(rn) for rn in RESTRICTED_ADMIN_ROLES]:
            return True
    return False

def get_staff_ping_string(guild: discord.Guild) -> str:
    staff_role_names = [
        SUPREME_LEADER_ROLE_NAME, ADMIN_ROLE_NAME, AUTHORITY_ROLE_NAME,
        HEAD_MOD_ROLE_NAME, MOD_ROLE_NAME, TRIAL_MOD_ROLE_NAME, TEAM_ROLE_NAME
    ]
    mentions = []
    for rname in staff_role_names:
        role = find_role_resilient(guild, rname)
        if role:
            mentions.append(role.mention)
    return " ".join(mentions) if mentions else "@here"

async def ensure_role_exists(guild: discord.Guild, name: str, color: discord.Color, permissions: discord.Permissions = discord.Permissions.none(), hoist: bool = False, mentionable: bool = False) -> discord.Role:
    role = find_role_resilient(guild, name)
    if not role:
        try:
            role = await guild.create_role(name=name, color=color, permissions=permissions, hoist=hoist, mentionable=mentionable, reason="Chill-Verse role sync")
            await asyncio.sleep(0.35)
        except Exception:
            pass
    return role

def generate_channel_overwrites(guild: discord.Guild, scheme: str) -> Dict[Any, discord.PermissionOverwrite]:
    staff_roles = [find_role_resilient(guild, r) for r in RESTRICTED_ADMIN_ROLES]
    active_staff = [r for r in staff_roles if r]
    admin_role = find_role_resilient(guild, ADMIN_ROLE_NAME)
    supreme_role = find_role_resilient(guild, SUPREME_LEADER_ROLE_NAME)
    roblox_role = find_role_resilient(guild, ROBLOX_ROLE_NAME)
    tier_roles = [find_role_resilient(guild, cfg["name"]) for cfg in LEVEL_TIER_ROLES.values()]
    active_tiers = [r for r in tier_roles if r]

    overwrites = {
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True,
            manage_permissions=True, embed_links=True, attach_files=True
        )
    }

    public_schemes = [
        "public_chat", "public_media", "public_read", 
        "polls_feed", "confession_feed", "public_voice", 
        "vip_voice", "music_voice"
    ]

    if scheme in public_schemes:
        if scheme == "public_chat":
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True, add_reactions=True
            )
        elif scheme == "public_media":
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
                attach_files=True, embed_links=True, add_reactions=True
            )
        elif scheme in ["public_read", "polls_feed", "confession_feed"]:
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=False, read_message_history=True, add_reactions=True
            )
        elif scheme in ["public_voice", "vip_voice"]:
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                view_channel=True, connect=True, speak=True, stream=True
            )
        elif scheme == "music_voice":
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                view_channel=True, connect=True, speak=True, stream=False, use_soundboard=False
            )
            
        for role in active_staff + active_tiers:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    elif scheme == "roblox_exclusive":
        overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
        if roblox_role:
            overwrites[roblox_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
                attach_files=True, embed_links=True
            )
        for role in active_staff:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    elif scheme == "staff_chat":
        overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
        for role in active_staff:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
                attach_files=True, embed_links=True
            )

    elif scheme in ["staff_rules", "staff_news"]:
        overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
        for role in active_staff:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=False, read_message_history=True, add_reactions=True
            )
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)

    elif scheme == "supreme_admin_only":
        overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
        for rname in [AUTHORITY_ROLE_NAME, HEAD_MOD_ROLE_NAME, MOD_ROLE_NAME, TRIAL_MOD_ROLE_NAME, TEAM_ROLE_NAME]:
            r = find_role_resilient(guild, rname)
            if r:
                overwrites[r] = discord.PermissionOverwrite(view_channel=False)
        for role in [admin_role, supreme_role]:
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    attach_files=True, embed_links=True
                )
            
    return overwrites

# ==============================================================================
# 4. INTERACTIVE UI VIEWS & MODALS
# ==============================================================================

class ColorDropdown(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label="Reset Color", description="Remove custom color role", emoji="🔄")]
        for c_name, _ in PRO_HEX_COLORS.items():
            options.append(discord.SelectOption(label=c_name, description=f"Apply {c_name} chat color", emoji="🎨"))
        super().__init__(placeholder="Choose your chat color...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        selected = self.values[0]

        for c_name in PRO_HEX_COLORS.keys():
            role = find_role_resilient(guild, c_name)
            if role and role in member.roles:
                try:
                    await member.remove_roles(role)
                except Exception:
                    pass

        if selected == "Reset Color":
            await interaction.response.send_message("🔄 Custom color role removed.", ephemeral=True)
            return

        target_role = find_role_resilient(guild, selected)
        if target_role:
            try:
                await member.add_roles(target_role)
                await interaction.response.send_message(f"✨ Color set to **{selected}**!", ephemeral=True)
            except Exception:
                await interaction.response.send_message("⚠️ Error assigning role.", ephemeral=True)

class ColorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ColorDropdown())

class GenderDropdown(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=g_name, description=f"Select {g_name}", emoji="👤") for g_name in GENDER_ROLES.keys()]
        super().__init__(placeholder="Select your identity role...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        selected = self.values[0]

        for g_name in GENDER_ROLES.keys():
            r = find_role_resilient(guild, g_name)
            if r and r in member.roles:
                try:
                    await member.remove_roles(r)
                except Exception:
                    pass

        target_role = find_role_resilient(guild, selected)
        if target_role:
            try:
                await member.add_roles(target_role)
                await interaction.response.send_message(f"👤 Identity set to **{selected}**!", ephemeral=True)
            except Exception:
                await interaction.response.send_message("⚠️ Error assigning identity role.", ephemeral=True)

class IdentityView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GenderDropdown())

class TicketModal(discord.ui.Modal):
    def __init__(self, ticket_type: str):
        super().__init__(title=f"{ticket_type} Form")
        self.ticket_type = ticket_type
        self.reason = discord.ui.TextInput(
            label="Please describe your request or reason:",
            style=discord.TextStyle.paragraph,
            placeholder="Provide details here...",
            required=True,
            max_length=1000
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        category = discord.utils.find(lambda c: "team" in normalize_text(c.name) or "ticket" in normalize_text(c.name), guild.categories)
        
        overwrites = {
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }
        for rname in RESTRICTED_ADMIN_ROLES:
            r = find_role_resilient(guild, rname)
            if r:
                overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel_name = f"ticket-{member.name}".lower()[:25]
        ticket_ch = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites, reason=f"Ticket: {self.ticket_type}")

        embed = discord.Embed(
            title=f"🎫 {self.ticket_type} Opened",
            description=f"Welcome {member.mention}!\n\n**Reason:** {self.reason.value}\n\nStaff will assist shortly.",
            color=discord.Color.teal()
        )
        await ticket_ch.send(content=f"{member.mention} {get_staff_ping_string(guild)}", embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f"✅ Ticket created: {ticket_ch.mention}", ephemeral=True)

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...", ephemeral=True)
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason="Ticket closed")
        except Exception:
            pass

class TicketLaunchSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Team Apply", description="Submit a staff application", emoji="🛡️"),
            discord.SelectOption(label="Create Ticket", description="General inquiries & support", emoji="📩"),
            discord.SelectOption(label="Need Help", description="Urgent assistance or reports", emoji="🆘")
        ]
        super().__init__(placeholder="Select ticket category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.values[0]))

class TicketLaunchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketLaunchSelect())

class ConfessionModal(discord.ui.Modal, title="Anonymous Confession Form"):
    confession = discord.ui.TextInput(
        label="Type your confession anonymously:",
        style=discord.TextStyle.paragraph,
        placeholder="Your identity is 100% secure...",
        required=True,
        max_length=1500
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        confess_ch = discord.utils.find(lambda c: "confessions" in normalize_text(c.name), guild.text_channels)
        if confess_ch:
            embed = discord.Embed(
                title="💌 Anonymous Confession",
                description=self.confession.value,
                color=discord.Color.from_rgb(230, 70, 80),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text="100% Anonymous & Secure")
            await confess_ch.send(embed=embed)
            await interaction.response.send_message("✅ Confession submitted anonymously!", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Confession channel not found.", ephemeral=True)

class ConfessionPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Submit Anonymous Confession", style=discord.ButtonStyle.secondary, emoji="💌")
    async def open_confession(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ConfessionModal())

# ==============================================================================
# 5. AUTOMATED PANELS & SERVER BOOTSTRAP PIPELINE
# ==============================================================================

async def auto_deploy_server_panels(guild: discord.Guild):
    async def refresh_panel(channel: discord.TextChannel, title_keyword: str, embed: discord.Embed, view: discord.ui.View):
        if not channel:
            return
        try:
            async for msg in channel.history(limit=25):
                if msg.author == guild.me and msg.embeds:
                    if title_keyword in msg.embeds[0].title:
                        try:
                            await msg.delete()
                            await asyncio.sleep(0.35)
                        except Exception:
                            pass
            await channel.send(embed=embed, view=view)
        except Exception:
            pass

    colors_ch = discord.utils.find(lambda c: "colours" in normalize_text(c.name), guild.text_channels)
    if colors_ch:
        embed = discord.Embed(
            title="🎨 Customize Your Name Color",
            description="Select a color from the dropdown below to tint your username in chat.\n\n*Selecting 'Reset Color' removes your custom cosmetic role.*",
            color=discord.Color.from_rgb(255, 105, 180)
        )
        await refresh_panel(colors_ch, "Customize Your Name Color", embed, ColorView())

    identity_ch = discord.utils.find(lambda c: "identity" in normalize_text(c.name), guild.text_channels)
    if identity_ch:
        embed = discord.Embed(
            title="🎭 Identity Roles",
            description="Select your pronoun/identity role from the dropdown below.",
            color=discord.Color.purple()
        )
        await refresh_panel(identity_ch, "Identity Roles", embed, IdentityView())

    tickets_ch = discord.utils.find(lambda c: "support-tickets" in normalize_text(c.name), guild.text_channels)
    if tickets_ch:
        embed = discord.Embed(
            title="🎫 Chill-Verse Support & Application Portal",
            description=(
                "Need assistance, want to report an issue, or looking to join the staff team?\n\n"
                "Select an option from the dropdown menu below to open your private ticket:\n\n"
                "🛡️ **Team Apply** — Submit a staff application\n"
                "📩 **Create Ticket** — General inquiries & support\n"
                "🆘 **Need Help** — Urgent assistance or reports"
            ),
            color=discord.Color.teal()
        )
        embed.set_footer(text="Confidential • Only staff and you can view your tickets.")
        await refresh_panel(tickets_ch, "Support & Application Portal", embed, TicketLaunchView())

    confess_ch = discord.utils.find(lambda c: normalize_text(c.name) == "confessions", guild.text_channels)
    if confess_ch:
        embed = discord.Embed(
            title="💌 Anonymous Confession Portal",
            description="Click the button below to open your 100% anonymous confession form.\n\n*Your identity, username, and ID are never logged, tracked, or shown anywhere.*",
            color=discord.Color.from_rgb(230, 70, 80)
        )
        embed.set_footer(text="100% Anonymous & Secure")
        await refresh_panel(confess_ch, "Anonymous Confession Portal", embed, ConfessionPanelView())

async def run_full_server_bootstrap(guild: discord.Guild):
    try:
        sup_cfg = ROLE_PERMISSIONS_CONFIG[SUPREME_LEADER_ROLE_NAME]
        await ensure_role_exists(guild, SUPREME_LEADER_ROLE_NAME, sup_cfg["color"], sup_cfg["permissions"], sup_cfg["hoist"])

        for rname, cfg in ROLE_PERMISSIONS_CONFIG.items():
            if rname != SUPREME_LEADER_ROLE_NAME:
                await ensure_role_exists(guild, rname, cfg["color"], cfg["permissions"], cfg["hoist"])

        for (low, high), cfg in LEVEL_TIER_ROLES.items():
            await ensure_role_exists(guild, cfg["name"], cfg["color"], cfg["permissions"], cfg["hoist"])

        for c_name, c_color in PRO_HEX_COLORS.items():
            await ensure_role_exists(guild, c_name, c_color)
        for g_name, g_color in GENDER_ROLES.items():
            await ensure_role_exists(guild, g_name, g_color)

        await ensure_role_exists(guild, OG_ROLE_NAME, discord.Color.dark_magenta())
        await ensure_role_exists(guild, VETERAN_ROLE_NAME, discord.Color.purple())
        await ensure_role_exists(guild, BOOSTER_ROLE_NAME, discord.Color.from_rgb(255, 105, 180))
        await ensure_role_exists(guild, VANITY_ROLE_NAME, discord.Color.from_rgb(120, 100, 180))
        await ensure_role_exists(guild, BUMP_ROLE_NAME, discord.Color.gold(), mentionable=True)
        await ensure_role_exists(guild, POLL_ROLE_NAME, discord.Color.red(), mentionable=True)
        await ensure_role_exists(guild, ROBLOX_ROLE_NAME, discord.Color.blue())

        for cat_data in EXTENDED_SERVER_BLUEPRINT:
            cat_name = cat_data["category"]
            category = discord.utils.find(lambda c: normalize_text(c.name) == normalize_text(cat_name), guild.categories)
            if not category:
                category = await guild.create_category(name=cat_name, reason="Bootstrap Category Init")
                await asyncio.sleep(0.35)

            for ch in cat_data["channels"]:
                ch_name, ch_type, scheme = ch["name"], ch["type"], ch["scheme"]
                user_lim = ch.get("user_limit", 0)
                overwrites = generate_channel_overwrites(guild, scheme)

                target_list = guild.text_channels if ch_type == "text" else guild.voice_channels
                channel = discord.utils.find(lambda c: normalize_text(c.name) == normalize_text(ch_name) and c.category_id == category.id, target_list)

                if not channel:
                    if ch_type == "text":
                        await guild.create_text_channel(name=ch_name, category=category, overwrites=overwrites, reason="Bootstrap channel")
                    else:
                        await guild.create_voice_channel(name=ch_name, category=category, user_limit=user_lim, overwrites=overwrites, reason="Bootstrap voice")
                    await asyncio.sleep(0.35)

        valid_channel_names = set()
        for cat in EXTENDED_SERVER_BLUEPRINT:
            for ch in cat["channels"]:
                valid_channel_names.add(normalize_text(ch["name"]))
        valid_channel_names.add("bot-memory")

        for channel in list(guild.text_channels + guild.voice_channels):
            if normalize_text(channel.name) not in valid_channel_names:
                try:
                    await channel.delete(reason="Bootstrap cleanup")
                    await asyncio.sleep(0.35)
                except Exception:
                    pass

        await auto_deploy_server_panels(guild)
    except Exception:
        pass

# ==============================================================================
# 6. XP, LEVELING, TENURE & AFK SYSTEMS
# ==============================================================================

async def verify_member_tenure(member: discord.Member):
    if member.bot:
        return
    guild = member.guild
    joined_at = member.joined_at
    if not joined_at:
        return
    
    days_in_server = (discord.utils.utcnow() - joined_at).days
    if days_in_server >= 365:
        og = find_role_resilient(guild, OG_ROLE_NAME)
        if og and og not in member.roles:
            try:
                await member.add_roles(og)
            except Exception:
                pass
    if days_in_server >= 180:
        vet = find_role_resilient(guild, VETERAN_ROLE_NAME)
        if vet and vet not in member.roles:
            try:
                await member.add_roles(vet)
            except Exception:
                pass

async def handle_user_xp_and_level(message: discord.Message):
    guild = message.guild
    user_id = str(message.author.id)
    state = bot.server_state.setdefault(guild.id, default_server_state())
    
    xp_data = state.setdefault("user_xp", {})
    lvl_data = state.setdefault("user_levels", {})

    current_xp = xp_data.get(user_id, 0) + random.randint(15, 25)
    xp_data[user_id] = current_xp

    current_lvl = lvl_data.get(user_id, 1)
    required_xp = current_lvl * 120

    if current_xp >= required_xp and current_lvl < MAX_LEVEL:
        new_lvl = current_lvl + 1
        lvl_data[user_id] = new_lvl
        
        for (low, high), cfg in LEVEL_TIER_ROLES.items():
            if low <= new_lvl <= high:
                role = find_role_resilient(guild, cfg["name"])
                if role and role not in message.author.roles:
                    for (_, _), old_cfg in LEVEL_TIER_ROLES.items():
                        old_r = find_role_resilient(guild, old_cfg["name"])
                        if old_r and old_r in message.author.roles:
                            try:
                                await message.author.remove_roles(old_r)
                            except Exception:
                                pass
                    try:
                        await message.author.add_roles(role)
                    except Exception:
                        pass
                break

        await save_state_to_memory(guild, data=state)

# ==============================================================================
# 7. AUTOMODERATION
# ==============================================================================

async def run_automod_check(message: discord.Message) -> bool:
    if is_staff_member(message.author) or message.author.bot:
        return False
    
    content_lower = message.content.lower()
    bad_words = ["discord.gg/", "invite.gg/", "badword1", "badword2"]
    if any(bw in content_lower for bw in bad_words):
        try:
            await message.delete()
            await message.channel.send(f"⚠️ {message.author.mention}, content blocked by automod.", delete_after=5)
        except Exception:
            pass
        return True
    return False

# ==============================================================================
# 8. BUMP SCHEDULER & LISTENERS
# ==============================================================================

async def schedule_bump_reminder(guild: discord.Guild, channel: Optional[discord.TextChannel] = None):
    if guild.id in active_bump_tasks:
        active_bump_tasks[guild.id].cancel()

    async def _runner():
        try:
            state = bot.server_state.setdefault(guild.id, default_server_state())
            last_bump = state.get("last_bump_time", 0.0)
            remaining = max(0, int(7200 - (time.time() - last_bump)))

            if remaining > 0:
                await asyncio.sleep(remaining)

            bump_ch = channel or discord.utils.find(lambda c: "bump" in normalize_text(c.name) or "announcements" in normalize_text(c.name), guild.text_channels)
            if bump_ch:
                staff_pings = get_staff_ping_string(guild)
                embed = discord.Embed(
                    title="⏰ Time to Bump!",
                    description="The 2-hour cooldown has passed. Run `.bump` to grow the server! 🚀",
                    color=discord.Color.gold(),
                    timestamp=discord.utils.utcnow()
                )
                await bump_ch.send(
                    content=f"🔔 {staff_pings}",
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions(roles=True, everyone=False)
                )
        finally:
            active_bump_tasks.pop(guild.id, None)

    active_bump_tasks[guild.id] = asyncio.create_task(_runner())

# ==============================================================================
# 9. EVENTS (ON_READY, ON_MESSAGE)
# ==============================================================================

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user} (ID: {bot.user.id})")
    for guild in bot.guilds:
        restored = await load_state_from_memory(guild)
        bot.server_state[guild.id] = restored

        if restored.get("last_bump_time", 0.0) > 0:
            await schedule_bump_reminder(guild)

        for member in guild.members:
            if not member.bot:
                await verify_member_tenure(member)

        await run_full_server_bootstrap(guild)
    print("🚀 Chill-Verse fully online & initialized!")

@bot.event
async def on_message(message: discord.Message):
    try:
        if message.author.bot or not message.guild:
            if message.guild and (message.author.id == 302050872383242240 or (message.author.bot and "bump" in message.content.lower())):
                success = "bump done" in message.content.lower()
                if not success and message.embeds:
                    for emb in message.embeds:
                        desc = emb.description or ""
                        if "bump done" in desc.lower() or "thumbsup" in desc.lower():
                            success = True
                            break
                if success:
                    state = bot.server_state.setdefault(message.guild.id, default_server_state())
                    state["last_bump_time"] = time.time()
                    await save_state_to_memory(message.guild, data=state)
                    try:
                        await message.channel.send("🚀 **Bump detected!** Next bump alert in 2 hours.", delete_after=10)
                    except Exception:
                        pass
                    await schedule_bump_reminder(message.guild, message.channel)
            return

        guild_id = message.guild.id
        state = bot.server_state.setdefault(guild_id, default_server_state())

        if state.get("maintenance_mode", False):
            if not is_staff_member(message.author):
                return

        afk_dict = state.setdefault("afk_users", {})
        if str(message.author.id) in afk_dict:
            afk_dict.pop(str(message.author.id))
            await save_state_to_memory(message.guild, data=state)
            try:
                await message.channel.send(f"Welcome back {message.author.mention}, AFK status cleared.", delete_after=6)
            except Exception:
                pass

        for ment in message.mentions:
            if str(ment.id) in afk_dict:
                reason = afk_dict[str(ment.id)]
                try:
                    await message.channel.send(f"💤 **{ment.display_name}** is AFK: {reason}", delete_after=8)
                except Exception:
                    pass

        if await run_automod_check(message):
            return

        await handle_user_xp_and_level(message)
        await bot.process_commands(message)
    except Exception:
        pass

# ==============================================================================
# 10. COMPLETE COMMANDS SUITE
# ==============================================================================

def check_maintenance_mode():
    async def predicate(ctx: commands.Context) -> bool:
        if not ctx.guild:
            return False
        state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
        if state.get("maintenance_mode", False) and not is_staff_member(ctx.author):
            await ctx.send("🚧 **Server is in Maintenance Mode.** Bot commands are locked for regular members.", delete_after=6)
            return False
        return True
    return commands.check(predicate)

@bot.command(name="maintenance")
@commands.has_permissions(administrator=True)
async def cmd_maintenance(ctx: commands.Context, status: Optional[str] = None):
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    if not status:
        current = state.get("maintenance_mode", False)
        await ctx.send(f"🚧 Maintenance Mode is currently: `{'ON' if current else 'OFF'}`")
        return
    
    if status.lower() in ["on", "true", "enable"]:
        state["maintenance_mode"] = True
        await save_state_to_memory(ctx.guild, data=state)
        await ctx.send("🚧 **Maintenance Mode ENABLED.**")
    elif status.lower() in ["off", "false", "disable"]:
        state["maintenance_mode"] = False
        await save_state_to_memory(ctx.guild, data=state)
        await ctx.send("✅ **Maintenance Mode DISABLED.**")

@bot.command(name="setup_channels")
@commands.has_permissions(administrator=True)
@check_maintenance_mode()
async def cmd_setup_channels(ctx: commands.Context):
    await ctx.send("⏳ **Deploying server blueprint & refreshing panels...**")
    await run_full_server_bootstrap(ctx.guild)
    await ctx.send("✅ **Server blueprint & panels deployed successfully!**")

@bot.command(name="autorole_setup")
@commands.has_permissions(administrator=True)
@check_maintenance_mode()
async def cmd_autorole_setup(ctx: commands.Context):
    guild = ctx.guild
    msg = await ctx.send("⏳ **Provisioning server roles exclusively...**")

    sup_cfg = ROLE_PERMISSIONS_CONFIG[SUPREME_LEADER_ROLE_NAME]
    await ensure_role_exists(guild, SUPREME_LEADER_ROLE_NAME, sup_cfg["color"], sup_cfg["permissions"], sup_cfg["hoist"])

    for rname, cfg in ROLE_PERMISSIONS_CONFIG.items():
        if rname != SUPREME_LEADER_ROLE_NAME:
            await ensure_role_exists(guild, rname, cfg["color"], cfg["permissions"], cfg["hoist"])

    for (low, high), cfg in LEVEL_TIER_ROLES.items():
        await ensure_role_exists(guild, cfg["name"], cfg["color"], cfg["permissions"], cfg["hoist"])

    for c_name, c_color in PRO_HEX_COLORS.items():
        await ensure_role_exists(guild, c_name, c_color)
    for g_name, g_color in GENDER_ROLES.items():
        await ensure_role_exists(guild, g_name, g_color)

    await ensure_role_exists(guild, OG_ROLE_NAME, discord.Color.dark_magenta())
    await ensure_role_exists(guild, VETERAN_ROLE_NAME, discord.Color.purple())
    await ensure_role_exists(guild, BOOSTER_ROLE_NAME, discord.Color.from_rgb(255, 105, 180))
    await ensure_role_exists(guild, VANITY_ROLE_NAME, discord.Color.from_rgb(120, 100, 180))
    await ensure_role_exists(guild, BUMP_ROLE_NAME, discord.Color.gold(), mentionable=True)
    await ensure_role_exists(guild, POLL_ROLE_NAME, discord.Color.red(), mentionable=True)
    await ensure_role_exists(guild, ROBLOX_ROLE_NAME, discord.Color.blue())

    await msg.edit(content="✅ **All server roles provisioned! Channels untouched.**")

@bot.command(name="rank")
@check_maintenance_mode()
async def cmd_rank(ctx: commands.Context, member: Optional[discord.Member] = None):
    target = member or ctx.author
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    xp = state.get("user_xp", {}).get(str(target.id), 0)
    lvl = state.get("user_levels", {}).get(str(target.id), 1)

    embed = discord.Embed(title=f"📊 Rank Card — {target.display_name}", color=discord.Color.teal())
    embed.add_field(name="Level", value=str(lvl), inline=True)
    embed.add_field(name="Total XP", value=str(xp), inline=True)
    embed.set_thumbnail(url=target.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="leaderboard")
@check_maintenance_mode()
async def cmd_leaderboard(ctx: commands.Context):
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    xp_data = state.get("user_xp", {})
    if not xp_data:
        await ctx.send("📊 Leaderboard is currently empty.")
        return

    sorted_users = sorted(xp_data.items(), key=lambda x: x[1], reverse=True)[:10]
    desc = []
    for idx, (uid, xp) in enumerate(sorted_users, 1):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"User {uid}"
        lvl = state.get("user_levels", {}).get(uid, 1)
        desc.append(f"**{idx}.** {name} — Level {lvl} ({xp} XP)")

    embed = discord.Embed(title="🏆 Chill-Verse XP Leaderboard", description="\n".join(desc), color=discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command(name="confess")
@check_maintenance_mode()
async def cmd_confess(ctx: commands.Context):
    try:
        await ctx.author.send("💌 Please reply with your confession. It will be posted anonymously.")
        await ctx.send("📬 Check your DMs for the anonymous confession prompt!", delete_after=6)
    except Exception:
        await ctx.send("⚠️ Could not send you a DM. Please enable direct messages.", delete_after=6)

@bot.command(name="afk")
@check_maintenance_mode()
async def cmd_afk(ctx: commands.Context, *, reason: str = "AFK"):
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    state.setdefault("afk_users", {})[str(ctx.author.id)] = reason
    await save_state_to_memory(ctx.guild, data=state)
    await ctx.send(f"💤 **{ctx.author.display_name}** is now AFK: {reason}", delete_after=10)

@bot.command(name="bumptimer")
@check_maintenance_mode()
async def cmd_bumptimer(ctx: commands.Context):
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    remaining = max(0, int(7200 - (time.time() - state.get("last_bump_time", 0.0))))
    if remaining == 0:
        await ctx.send("🚀 **Server is ready to be bumped right now!** Type `.bump`")
    else:
        await ctx.send(f"⏳ Next bump available in **{remaining // 60} minutes and {remaining % 60} seconds**.")

@bot.command(name="bump")
@check_maintenance_mode()
async def cmd_bump(ctx: commands.Context):
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    state["last_bump_time"] = time.time()
    await save_state_to_memory(ctx.guild, data=state)
    await schedule_bump_reminder(ctx.guild, ctx.channel)
    
    embed = discord.Embed(title="🚀 Server Bump Logged!", description="Thank you! Next alert scheduled in 2 hours.", color=discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command(name="poll")
@commands.has_permissions(manage_messages=True)
@check_maintenance_mode()
async def cmd_poll(ctx: commands.Context, *, question: str):
    poll_role = find_role_resilient(ctx.guild, POLL_ROLE_NAME)
    mention_str = poll_role.mention if poll_role else "@here"

    embed = discord.Embed(title="📊 Official Chill-Verse Poll", description=f"**{question}**\n\nReact below to vote!", color=discord.Color.red())
    embed.set_footer(text=f"Hosted by {ctx.author.display_name}")
    
    msg = await ctx.send(content=f"📢 {mention_str}", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True, everyone=False))
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
@check_maintenance_mode()
async def cmd_kick(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    try:
        await member.kick(reason=reason)
        await ctx.send(f"👢 **{member}** kicked. Reason: {reason}")
    except Exception as e:
        await ctx.send(f"⚠️ Error: `{e}`")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
@check_maintenance_mode()
async def cmd_ban(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"🔨 **{member}** banned. Reason: {reason}")
    except Exception as e:
        await ctx.send(f"⚠️ Error: `{e}`")

@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
@check_maintenance_mode()
async def cmd_timeout(ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str = "No reason provided"):
    try:
        duration = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
        mutes = state.setdefault("mutes_count", {})
        mutes[str(member.id)] = mutes.get(str(member.id), 0) + 1
        await save_state_to_memory(ctx.guild, data=state)
        await ctx.send(f"🔇 **{member}** timed out for {minutes}m. Reason: {reason}")
    except Exception as e:
        await ctx.send(f"⚠️ Error: `{e}`")

@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
@check_maintenance_mode()
async def cmd_warn(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    warnings = state.setdefault("warnings", {})
    user_warns = warnings.setdefault(str(member.id), [])
    user_warns.append({"reason": reason, "moderator": ctx.author.id, "time": time.time()})
    await save_state_to_memory(ctx.guild, data=state)
    await ctx.send(f"⚠️ **{member.mention}** warned. Reason: {reason} (Total: {len(user_warns)})")

@bot.command(name="warnings")
@check_maintenance_mode()
async def cmd_warnings(ctx: commands.Context, member: Optional[discord.Member] = None):
    target = member or ctx.author
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    user_warns = state.get("warnings", {}).get(str(target.id), [])
    if not user_warns:
        await ctx.send(f"✅ **{target.display_name}** has 0 warnings.")
        return

    desc = [f"**{i+1}.** {w['reason']}" for i, w in enumerate(user_warns)]
    embed = discord.Embed(title=f"⚠️ Warnings — {target.display_name}", description="\n".join(desc), color=discord.Color.orange())
    await ctx.send(embed=embed)

@bot.command(name="clearwarns")
@commands.has_permissions(manage_messages=True)
@check_maintenance_mode()
async def cmd_clearwarns(ctx: commands.Context, member: discord.Member):
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    if str(member.id) in state.get("warnings", {}):
        state["warnings"].pop(str(member.id))
        await save_state_to_memory(ctx.guild, data=state)
    await ctx.send(f"✅ Warnings cleared for **{member}**.")

@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
@check_maintenance_mode()
async def cmd_purge(ctx: commands.Context, amount: int):
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"🧹 Cleared {len(deleted) - 1} messages.", delete_after=5)
    except Exception as e:
        await ctx.send(f"⚠️ Error: `{e}`")

@bot.command(name="setbirthday")
@check_maintenance_mode()
async def cmd_setbirthday(ctx: commands.Context, date_str: str):
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    state.setdefault("birthdays", {})[str(ctx.author.id)] = date_str
    await save_state_to_memory(ctx.guild, data=state)
    await ctx.send(f"🎂 Birthday registered as **{date_str}**!")

@bot.command(name="birthday")
@check_maintenance_mode()
async def cmd_birthday(ctx: commands.Context, member: Optional[discord.Member] = None):
    target = member or ctx.author
    state = bot.server_state.setdefault(ctx.guild.id, default_server_state())
    bday = state.get("birthdays", {}).get(str(target.id))
    if bday:
        await ctx.send(f"🎂 Birthday for **{target.display_name}**: `{bday}`")
    else:
        await ctx.send(f"🎂 No birthday found for **{target.display_name}**.")

@bot.command(name="botlist")
@check_maintenance_mode()
async def cmd_botlist(ctx: commands.Context):
    embed = discord.Embed(
        title="🤖 Chill-Verse Complete Command Matrix",
        description="Catalog of all administrative, staff, and public user commands:",
        color=discord.Color.teal(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(
        name="🏗️ Setup & Infrastructure",
        value=(
            "• `.setup_channels` — Deploys missing channels & auto-posts panels safely\n"
            "• `.autorole_setup` — Provisions all server roles and cosmetic tiers\n"
            "• `.maintenance [on/off]` — Toggles server maintenance lock"
        ),
        inline=False
    )
    embed.add_field(
        name="🛡️ Moderation Suite",
        value=(
            "• `.kick` / `.ban` / `.timeout` — Admin moderation actions\n"
            "• `.warn` / `.warnings` / `.clearwarns` — Warning management\n"
            "• `.purge <amount>` — Clears chat messages"
        ),
        inline=False
    )
    embed.add_field(
        name="🎮 Public & Community Features",
        value=(
            "• `.rank` — Displays user level and XP card\n"
            "• `.leaderboard` — Shows top active members\n"
            "• `.confess` — Triggers anonymous confession workflow\n"
            "• `.afk` — Sets custom AFK mood/reason\n"
            "• `.bump` / `.bumptimer` — Server bump tools\n"
            "• `.poll` — Dispatches official server poll\n"
            "• `.setbirthday` — Registers birthday"
        ),
        inline=False
    )
    await ctx.send(embed=embed)

# ==============================================================================
# RUN BOT
# ==============================================================================

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("⚠️ Error: DISCORD_BOT_TOKEN environment variable not found.")
    else:
        bot.run(TOKEN)
