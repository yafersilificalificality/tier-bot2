import discord
from discord.ext import commands
from discord import app_commands
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= CONFIG =================

STAFF_ROLE_IDS = [1470069421379948585]  # REPLACE WITH YOUR STAFF ROLE IDS

TICKET_TIERS = ["HT1", "LT1", "HT2", "LT2", "HT3"]

GAMEMODES = ["nethop", "pot", "sword", "axe", "vanilla", "mace", "uhc", "smp"]

queues = {gm: [] for gm in GAMEMODES}
waitlists = {gm: [] for gm in GAMEMODES}

queue_open = {gm: False for gm in GAMEMODES}
tester_online = {gm: False for gm in GAMEMODES}

# ================= HELPERS =================

def is_staff(member: discord.Member):
    return any(role.id in STAFF_ROLE_IDS for role in member.roles)

# ================= EVENTS =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# ================= UI =================

class CentralPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Start Tier Test", style=discord.ButtonStyle.green, emoji="🧪")
    async def start(self, interaction, button):
        await interaction.response.send_modal(TierTestModal())

    @discord.ui.button(label="Queue Status", style=discord.ButtonStyle.gray, emoji="📊")
    async def status(self, interaction, button):
        desc = ""
        for gm in GAMEMODES:
            q = len(queues[gm])
            wl = len(waitlists[gm])
            status = "🟢 OPEN" if queue_open[gm] else "🔴 CLOSED"
            tester = "👨‍🔬 ONLINE" if tester_online[gm] else "❌ OFFLINE"
            desc += f"**{gm.upper()}** → {status} | {tester} | Queue: {q} | Waitlist: {wl}\n"

        embed = discord.Embed(title="📊 Queue Status", description=desc, color=0x2b2d31)
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ================= MODAL =================

class TierTestModal(discord.ui.Modal, title="Tier Test Application"):
    server = discord.ui.TextInput(label="Server", placeholder="minemen.club")
    tier = discord.ui.TextInput(label="Tier", placeholder="HT3, LT2, etc")
    gamemode = discord.ui.TextInput(label="Gamemode", placeholder="pot, nethop, uhc, etc")

    async def on_submit(self, interaction: discord.Interaction):
        server = self.server.value
        tier = self.tier.value.upper().strip()
        gm = self.gamemode.value.lower().strip()

        if gm not in GAMEMODES:
            return await interaction.response.send_message("❌ Invalid gamemode.", ephemeral=True)

        if tier in TICKET_TIERS:
            await open_private_ticket(interaction, gm, server, tier)
            return

        if not tester_online[gm] or not queue_open[gm]:
            waitlists[gm].append(interaction.user.id)
            pos = len(waitlists[gm])

            return await interaction.response.send_message(
                f"⏳ **Added to {gm.upper()} WAITLIST**\n"
                f"Position: **#{pos}**\n"
                f"You will be moved to queue when tester is online.",
                ephemeral=True
            )

        queues[gm].append(interaction.user.id)
        pos = len(queues[gm])

        await interaction.response.send_message(
            f"✅ **Joined {gm.upper()} queue**\n"
            f"Position: **#{pos}**",
            ephemeral=True
        )

        await try_open_ticket(interaction.guild, gm)

# ================= STAFF PANEL =================

class StaffPanel(discord.ui.View):
    def __init__(self, gamemode):
        super().__init__(timeout=None)
        self.gm = gamemode

    @discord.ui.button(label="Tester Online", style=discord.ButtonStyle.green)
    async def online(self, interaction, button):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        tester_online[self.gm] = True
        await interaction.response.send_message(f"👨‍🔬 {self.gm.upper()} tester ONLINE")

    @discord.ui.button(label="Tester Offline", style=discord.ButtonStyle.red)
    async def offline(self, interaction, button):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        tester_online[self.gm] = False
        await interaction.response.send_message(f"❌ {self.gm.upper()} tester OFFLINE")

    @discord.ui.button(label="Open Queue", style=discord.ButtonStyle.green)
    async def openq(self, interaction, button):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)

        queue_open[self.gm] = True

        while waitlists[self.gm]:
            queues[self.gm].append(waitlists[self.gm].pop(0))

        await interaction.response.send_message(f"🟢 {self.gm.upper()} queue OPEN")

    @discord.ui.button(label="Close Queue", style=discord.ButtonStyle.red)
    async def closeq(self, interaction, button):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        queue_open[self.gm] = False
        await interaction.response.send_message(f"🔴 {self.gm.upper()} queue CLOSED")

# ================= COMMANDS =================

@bot.tree.command(name="panel", description="Open central testing panel")
async def panel(interaction):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff only.", ephemeral=True)

    embed = discord.Embed(
        title="🧪 Goofy Tiers – Testing Panel",
        description="Click below to start your tier test.",
        color=0x2b2d31
    )

    await interaction.response.send_message(embed=embed, view=CentralPanel())

@bot.tree.command(name="staffpanel", description="Open staff queue panel")
@app_commands.describe(gamemode="Gamemode")
async def staffpanel(interaction, gamemode: str):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff only.", ephemeral=True)

    gamemode = gamemode.lower()
    if gamemode not in GAMEMODES:
        return await interaction.response.send_message("❌ Invalid gamemode.", ephemeral=True)

    await interaction.response.send_message(
        f"🎛 {gamemode.upper()} Staff Panel",
        view=StaffPanel(gamemode)
    )

@bot.tree.command(name="queue", description="View queue")
@app_commands.describe(gamemode="Gamemode")
async def queue(interaction, gamemode: str):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff only.", ephemeral=True)

    gamemode = gamemode.lower()
    if gamemode not in GAMEMODES:
        return await interaction.response.send_message("❌ Invalid gamemode.", ephemeral=True)

    q = queues[gamemode]
    if not q:
        return await interaction.response.send_message("Queue is empty.", ephemeral=True)

    desc = ""
    for i, uid in enumerate(q, 1):
        user = interaction.guild.get_member(uid)
        if user:
            desc += f"{i}. {user.mention}\n"

    await interaction.response.send_message(desc, ephemeral=True)

@bot.tree.command(name="waitlist", description="View waitlist")
@app_commands.describe(gamemode="Gamemode")
async def waitlist(interaction, gamemode: str):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff only.", ephemeral=True)

    gamemode = gamemode.lower()
    if gamemode not in GAMEMODES:
        return await interaction.response.send_message("❌ Invalid gamemode.", ephemeral=True)

    wl = waitlists[gamemode]
    if not wl:
        return await interaction.response.send_message("Waitlist is empty.", ephemeral=True)

    desc = ""
    for i, uid in enumerate(wl, 1):
        user = interaction.guild.get_member(uid)
        if user:
            desc += f"{i}. {user.mention}\n"

    await interaction.response.send_message(desc, ephemeral=True)

@bot.tree.command(name="removefromqueue", description="Remove from queue")
@app_commands.describe(user="User", gamemode="Gamemode")
async def removefromqueue(interaction, user: discord.Member, gamemode: str):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff only.", ephemeral=True)

    gamemode = gamemode.lower()
    if user.id in queues[gamemode]:
        queues[gamemode].remove(user.id)
        await interaction.response.send_message("✅ Removed.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Not in queue.", ephemeral=True)

@bot.tree.command(name="removefromwaitlist", description="Remove from waitlist")
@app_commands.describe(user="User", gamemode="Gamemode")
async def removefromwaitlist(interaction, user: discord.Member, gamemode: str):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Staff only.", ephemeral=True)

    gamemode = gamemode.lower()
    if user.id in waitlists[gamemode]:
        waitlists[gamemode].remove(user.id)
        await interaction.response.send_message("✅ Removed.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Not in waitlist.", ephemeral=True)

# ================= TICKET SYSTEM =================

class CloseTicketView(discord.ui.View):
    def __init__(self, gamemode, user_id):
        super().__init__(timeout=None)
        self.gm = gamemode
        self.uid = user_id

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, emoji="🔒")
    async def close(self, interaction, button):
        if self.uid in queues[self.gm]:
            queues[self.gm].remove(self.uid)
        await interaction.channel.delete()

async def try_open_ticket(guild, gamemode):
    if not queues[gamemode]:
        return

    user_id = queues[gamemode][0]
    member = guild.get_member(user_id)
    if member:
        await open_private_ticket(member, gamemode, "Queue", "N/A")

async def open_private_ticket(interaction_or_member, gamemode, server, tier):
    user = interaction_or_member.user if isinstance(interaction_or_member, discord.Interaction) else interaction_or_member
    guild = user.guild

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }

    for rid in STAFF_ROLE_IDS:
        role = guild.get_role(rid)
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    channel = await guild.create_text_channel(
        name=f"ticket-{user.name.lower()}",
        overwrites=overwrites
    )

    embed = discord.Embed(
        title="🎫 Tier Test Ticket",
        description=(
            f"**User:** {user.mention}\n"
            f"**Gamemode:** {gamemode.upper()}\n"
            f"**Server:** {server}\n"
            f"**Tier:** {tier}"
        ),
        color=0x2b2d31
    )

    await channel.send(embed=embed, view=CloseTicketView(gamemode, user.id))

# ================= RUN =================

bot.run(TOKEN)

