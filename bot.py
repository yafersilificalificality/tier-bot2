import discord
from discord.ext import commands
from discord import app_commands
import os

TOKEN = os.getenv("TOKEN")

GAMEMODES = ["NethOP", "Pot", "Sword", "Axe", "Vanilla", "Mace", "UHC", "SMP"]
STAFF_ROLE_NAME = "Staff"
TESTER_ROLE_NAME = "Tester"

TIERS_FOR_TICKET = ["HT1", "LT1", "HT2", "LT2", "HT3"]

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

queues = {gm: [] for gm in GAMEMODES}
waitlists = {gm: [] for gm in GAMEMODES}
open_queues = {gm: False for gm in GAMEMODES}


def is_staff(member: discord.Member):
    return any(r.name == STAFF_ROLE_NAME for r in member.roles)


def is_tester(member: discord.Member):
    return any(r.name == TESTER_ROLE_NAME for r in member.roles)


async def get_or_create_waitlist_channel(guild, gamemode):
    channel_name = f"waitlist-{gamemode.lower()}"
    channel = discord.utils.get(guild.text_channels, name=channel_name)

    if channel is None:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False)
        }
        channel = await guild.create_text_channel(channel_name, overwrites=overwrites)

    return channel


async def open_ticket(guild, user, gamemode):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    }

    for role in guild.roles:
        if role.name == STAFF_ROLE_NAME:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    category = discord.utils.get(guild.categories, name="Tickets")
    if category is None:
        category = await guild.create_category("Tickets")

    channel = await guild.create_text_channel(
        name=f"ticket-{user.name}-{gamemode.lower()}",
        overwrites=overwrites,
        category=category
    )

    await channel.send(
        f"🎫 **Ticket Opened for {user.mention}**\nGamemode: **{gamemode}**",
        view=CloseTicketView(user, gamemode)
    )


async def check_queue(guild, gamemode):
    if open_queues[gamemode] and queues[gamemode]:
        user = queues[gamemode][0]
        await open_ticket(guild, user, gamemode)


class CloseTicketView(discord.ui.View):
    def __init__(self, user, gamemode):
        super().__init__(timeout=None)
        self.user = user
        self.gamemode = gamemode

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Staff only.", ephemeral=True)

        if queues[self.gamemode] and queues[self.gamemode][0] == self.user:
            queues[self.gamemode].pop(0)

        await interaction.channel.delete()


class TestingModal(discord.ui.Modal, title="Tier Test Form"):
    server = discord.ui.TextInput(label="Server", placeholder="Server name")
    tier = discord.ui.TextInput(label="Your Tier (HT1, LT1, etc)")
    gamemode = discord.ui.TextInput(label="Gamemode")

    async def on_submit(self, interaction: discord.Interaction):
        gm = self.gamemode.value.capitalize()

        if gm not in GAMEMODES:
            return await interaction.response.send_message("Invalid gamemode.", ephemeral=True)

        tier = self.tier.value.upper()

        if tier in TIERS_FOR_TICKET:
            if interaction.user not in queues[gm]:
                queues[gm].append(interaction.user)

            await interaction.response.send_message(
                f"✅ Added to **{gm} queue**. Position: **{len(queues[gm])}**",
                ephemeral=True
            )

            await check_queue(interaction.guild, gm)

        else:
            if interaction.user not in waitlists[gm]:
                waitlists[gm].append(interaction.user)

                channel = await get_or_create_waitlist_channel(interaction.guild, gm)
                await channel.send(f"➕ {interaction.user.mention} joined **{gm} waitlist**")

            await interaction.response.send_message(
                f"🕒 Added to **{gm} waitlist**.",
                ephemeral=True
            )


class TestingPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Testing Form", style=discord.ButtonStyle.green)
    async def open_form(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TestingModal())


class QueueControl(discord.ui.View):
    def __init__(self, gamemode):
        super().__init__(timeout=None)
        self.gm = gamemode

    @discord.ui.button(label="Open Queue", style=discord.ButtonStyle.success)
    async def openq(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_tester(interaction.user):
            return await interaction.response.send_message("Tester only.", ephemeral=True)

        open_queues[self.gm] = True
        await interaction.response.send_message(f"✅ **{self.gm} queue opened!**")
        await check_queue(interaction.guild, self.gm)

    @discord.ui.button(label="Close Queue", style=discord.ButtonStyle.danger)
    async def closeq(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_tester(interaction.user):
            return await interaction.response.send_message("Tester only.", ephemeral=True)

        open_queues[self.gm] = False
        await interaction.response.send_message(f"⛔ **{self.gm} queue closed.**")


@bot.tree.command(name="panel")
async def panel(interaction: discord.Interaction):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("Staff Only.", ephemeral=True)

    embed = discord.Embed(
        title="🎯 Central Testing Panel",
        description="Click below to open the tier testing form."
    )

    await interaction.channel.send(embed=embed, view=TestingPanel())
    await interaction.response.send_message("Panel sent.", ephemeral=True)


@bot.tree.command(name="queue")
@app_commands.describe(gamemode="Gamemode")
async def queue(interaction: discord.Interaction, gamemode: str):
    gm = gamemode.capitalize()

    if gm not in GAMEMODES:
        return await interaction.response.send_message("Invalid gamemode.", ephemeral=True)

    embed = discord.Embed(
        title=f"{gm} Queue Control",
        description="Testers can open or close the queue."
    )

    await interaction.channel.send(embed=embed, view=QueueControl(gm))
    await interaction.response.send_message("Queue panel sent.", ephemeral=True)


@bot.tree.command(name="checkqueue")
async def checkqueue(interaction: discord.Interaction):
    msg = ""
    for gm in GAMEMODES:
        msg += f"**{gm}** → Queue: {len(queues[gm])} | Waitlist: {len(waitlists[gm])}\n"

    await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name="remove")
@app_commands.describe(user="User", gamemode="Gamemode")
async def remove(interaction: discord.Interaction, user: discord.Member, gamemode: str):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("Staff Only.", ephemeral=True)

    gm = gamemode.capitalize()

    if user in queues[gm]:
        queues[gm].remove(user)
        return await interaction.response.send_message("Removed from queue.")

    if user in waitlists[gm]:
        waitlists[gm].remove(user)
        return await interaction.response.send_message("Removed from waitlist.")

    await interaction.response.send_message("User not found.")


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot online as {bot.user}")


bot.run(TOKEN)
