import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")

queues = {
    "nethop": [],
    "pot": [],
    "sword": [],
    "axe": [],
    "vanilla": [],
    "mace": [],
    "uhc": [],
    "smp": []
}

async def open_ticket_for_first(interaction: discord.Interaction, gamemode: str):
    guild = interaction.guild

    # Category name for tickets
    category_name = f"{gamemode}-tickets"

    category = discord.utils.get(guild.categories, name=category_name)
    if category is None:
        category = await guild.create_category(category_name)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(view_channel=True)
    }

    channel = await guild.create_text_channel(
        name=f"ticket-{interaction.user.name}",
        overwrites=overwrites,
        category=category
    )

    embed = discord.Embed(
        title="🎫 Tier Test Ticket",
        description=f"{interaction.user.mention}, staff will be with you shortly.\n\n**Gamemode:** {gamemode.upper()}",
        color=discord.Color.green()
    )

    view = CloseTicketView(interaction.user, gamemode)

    await channel.send(embed=embed, view=view)

async def join_queue(interaction, gamemode):
    user = interaction.user
    queue = queues[gamemode]

    if user.id in queue:
        await interaction.response.send_message("You are already in the queue.", ephemeral=True)
        return

    queue.append(user.id)
    pos = len(queue)

    await interaction.response.send_message(
        f"You joined **{gamemode.upper()} queue** at position **#{pos}**",
        ephemeral=True
    )

    if pos == 1:
        await open_ticket_for_first(interaction, gamemode)

async def open_ticket(guild, user, gamemode):
    staff_role = discord.utils.get(guild.roles, name="Staff")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(view_channel=True)
    }

    if staff_role:
        overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    channel = await guild.create_text_channel(
        name=f"ticket-{user.name.lower()}",
        overwrites=overwrites,
        topic=f"{gamemode}|{user.id}"
    )

    await channel.send(
        f"🎫 **Tier Test Ticket**\n\n"
        f"User: {user.mention}\n"
        f"Gamemode: **{gamemode.upper()}**\n\n"
        f"Press **Close Ticket** once testing is finished.",
        view=CloseTicketView()
    )

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel

        try:
            gamemode, user_id = channel.topic.split("|")
            user_id = int(user_id)
        except:
            await interaction.response.send_message("Invalid ticket channel.", ephemeral=True)
            return

        queue = queues[gamemode]

        if user_id in queue:
            queue.remove(user_id)

        await interaction.response.send_message("Closing ticket...", ephemeral=True)

        await channel.delete()

        await open_next(interaction.guild, gamemode)

async def open_next(guild, gamemode):
    queue = queues[gamemode]

    if not queue:
        return

    user = guild.get_member(queue[0])

    if user:
        await open_ticket(guild, user, gamemode)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- CONFIG ----------------

GAMEMODES = ["nethop","pot","sword","axe","vanilla","mace","uhc","smp"]

VALID_TIERS = ["LT5","LT4","LT3","LT2","LT1","HT5","HT4","HT3","HT2","HT1"]

waitlists = {mode: [] for mode in GAMEMODES}

# ----------------------------------------

@bot.event
async def on_ready():
    print("Tier Testing System Online")
    await bot.tree.sync()

# ---------- TIER LOGIC ----------

def should_get_ticket(tier: str) -> bool:
    tier = tier.upper().strip()
    return tier in ["HT1", "LT1", "HT2", "LT2", "HT3"]

# ---------- UTIL ----------

async def get_or_create_waitlist_channel(guild, gamemode):
    name = f"waitlist-{gamemode}"
    channel = discord.utils.get(guild.text_channels, name=name)

    if not channel:
        channel = await guild.create_text_channel(name)

    return channel

# ---------- APPLICATION MODAL ----------

class TierModal(discord.ui.Modal, title="Tier Test Application"):

    server = discord.ui.TextInput(
        label="Server you want to tier test on",
        placeholder="e.g. minemen.club",
        required=True
    )

    tier = discord.ui.TextInput(
        label="Your Current Tier",
        placeholder="Example: HT3",
        required=True,
        max_length=4
    )

    gamemode = discord.ui.TextInput(
        label="Gamemode",
        placeholder="NethOP / Pot / Sword / Axe / Vanilla / Mace / UHC / SMP",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        tier_value = self.tier.value.upper().strip()
        gamemode = self.gamemode.value.lower().strip()

        if tier_value not in VALID_TIERS:
            return await interaction.response.send_message(
                "❌ Invalid tier format. Example: `HT3`, `LT2`",
                ephemeral=True
            )

        if gamemode not in GAMEMODES:
            return await interaction.response.send_message(
                "❌ Invalid gamemode.",
                ephemeral=True
            )

        await process_application(interaction, self.server.value, tier_value, gamemode)

# ---------- APPLICATION HANDLER ----------

async def process_application(interaction, server, tier, gamemode):

    guild = interaction.guild
    user = interaction.user

    # WAITLIST TIERS
    if not should_get_ticket(tier):
        waitlists[gamemode].append(user.id)

        channel = await get_or_create_waitlist_channel(guild, gamemode)
        await channel.send(f"➕ **{user.mention}** joined the **{gamemode.upper()}** waitlist.")

        return await interaction.response.send_message(
            f"✅ You were added to the **{gamemode.upper()}** waitlist.",
            ephemeral=True
        )

    # STAFF TICKET TIERS
    category = discord.utils.get(guild.categories, name="Staff Tickets")
    if not category:
        category = await guild.create_category("Staff Tickets")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    ticket = await guild.create_text_channel(
        f"ticket-{user.name}",
        category=category,
        overwrites=overwrites
    )

    await ticket.send(
        f"🎫 **Tier Test Ticket**\n\n"
        f"User: {user.mention}\n"
        f"Server: `{server}`\n"
        f"Tier: `{tier}`\n"
        f"Gamemode: `{gamemode.upper()}`\n\n"
        f"Staff will assist shortly."
    )

    await interaction.response.send_message(
        "🎟 Your private staff ticket has been created.",
        ephemeral=True
    )

# ---------- PANEL ----------

class Panel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Apply For Tier Test", style=discord.ButtonStyle.green)
    async def apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TierModal())

# ---------- COMMANDS ----------

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    embed = discord.Embed(
        title="Tier Testing System",
        description="Click below to apply for a tier test.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=Panel())

@bot.command()
async def queue(ctx, gamemode: str):
    gamemode = gamemode.lower()

    if gamemode not in GAMEMODES:
        return await ctx.send("❌ Invalid gamemode.")

    queue_list = waitlists[gamemode]

    if not queue_list:
        return await ctx.send("Queue is empty.")

    msg = "\n".join([f"{i+1}. <@{uid}>" for i, uid in enumerate(queue_list)])
    await ctx.send(f"**{gamemode.upper()} Queue:**\n{msg}")

@bot.command()
async def next(ctx, gamemode: str):
    gamemode = gamemode.lower()

    if gamemode not in GAMEMODES:
        return await ctx.send("❌ Invalid gamemode.")

    if not waitlists[gamemode]:
        return await ctx.send("Queue is empty.")

    user_id = waitlists[gamemode].pop(0)
    await ctx.send(f"🎯 Next player: <@{user_id}>")

# ---------- RUN ----------

bot.run(TOKEN)