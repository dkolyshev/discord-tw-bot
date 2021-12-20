import os
from dotenv import load_dotenv
import discord
import discord.utils
import discord.guild
import helper_db
import helper_data_processing

from keep_alive import keep_alive
from discord.ext import commands
from discord.ext.tasks import loop

global channel, channel_id, enable_bg_task, bg_task_interval, enable_keep_alive_feature


load_dotenv()
token = os.getenv('DISCORD_BOT_TOKEN')
channel_id = int(os.getenv('DISCORD_CHANNEL_ID'))
channel = None
enable_bg_task = False
bg_task_interval = 5
enable_keep_alive_feature = True

intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.guilds = True

bot = commands.Bot('!', intents=intents)

@bot.event
async def on_ready():
    global channel
    global channel_id
    channel = bot.get_channel(channel_id)
    print("Bot is ready")
    print("Default channel ID for BG task is " + str(channel))

# define !dtw_help command
@bot.command()
async def dtw_help(ctx):
    embed_msg = discord.Embed(title="Help",
                              description="List of Twitter Updates bot commands",
                              color=0xf6b26b)
    embed_msg.add_field(
        name="!dtw_help",
        value=
        "Output information about the bot and commands.",
        inline=True)
    embed_msg.add_field(
        name="!dtw_check",
        value=
        "Check updates for a single account in DB or for all accs in DB. Usage for single account: !dtw_check username. Usage for all accounts: !dtw_check",
        inline=True)
    embed_msg.add_field(
        name="!dtw_add",
        value=
        "Add new account for monitoring. Usage: !dtw_add username",
        inline=True)
    embed_msg.add_field(
        name="!dtw_remove",
        value=
        "Remove account from monitoring. Usage: !dtw_remove username",
        inline=True)
    embed_msg.add_field(
        name="!dtw_stat",
        value=
        "Show statistic for account in DB. Usage: !dtw_stat username",
        inline=True)
    await ctx.send(embed=embed_msg)

# define dtw_check command
@bot.command()
async def dtw_check(ctx, account_name=None):
    if account_name != None:
        accs = [account_name]
    else:
        accs = helper_db.extract_all_accs(helper_db.conn)
    await helper_data_processing.dtw_check_processing(ctx, accs)
    print("!dtw_check finished")

# define dtw_check command
@bot.command()
async def dtw_add(ctx, account_name=None):
    if account_name == None:
        await ctx.send("Please specify the username. Example: !dtw_add nasa")
    if helper_db.add_acc(helper_db.conn, account_name):
        msg = "Account with the name **" + account_name + "** was added to monitoring"
    else:
        msg = "Account with the name **" + account_name + "** already added"
    await ctx.send(msg)

# define dtw_list command
@bot.command()
async def dtw_list(ctx):
    accs = helper_db.extract_all_accs(helper_db.conn)
    total_accs = len(accs)
    if total_accs == 0:
        desc = "The list of monitored accounts is empty. Please use command '!dtw_add username' to add new accounts for monitoring"
    else:
        desc = "The list of monitored accounts. Total count is " + str(total_accs)
    embedVar = discord.Embed(title="The result of the !list command", description=desc, color=0x00ff00)
    for i in range(total_accs):
        embedVar.add_field(name=accs[i], value="https://twitter.com/" + accs[i], inline=True)
    await ctx.send(embed=embedVar)

# define dtw_remove command
@bot.command()
async def dtw_remove(ctx, account_name=None):
    if account_name == None:
        await ctx.send("Please specify the username. Example: !dtw_remove nasa")
    helper_db.remove_acc(helper_db.conn, account_name)
    await ctx.send("Account with the name **" + account_name + "** was removed from monitoring")

# define dtw_stat command
@bot.command()
async def dtw_stat(ctx, account_name=None):
    if account_name == None:
        await ctx.send("Please specify the username. Example: !dtw_stat nasa")
    count = helper_db.check_acc_follows_count(helper_db.conn, account_name)
    if isinstance(count, int):
        await ctx.send("Account " + account_name + " has " + str(count) + " follows.")

@loop(seconds=60 * bg_task_interval)
async def background_dtw_check():
    global channel, enable_bg_task
    if channel != None and enable_bg_task:
        print(channel)
        accs = helper_db.extract_all_accs(helper_db.conn)
        await helper_data_processing.dtw_check_processing(channel, accs, False)
        print("background_dtw_check finished")

# tweak REPL instance: ping local Flask server with uptimerobot - this will allow to keep repl instance in live mode 24/7 
if enable_keep_alive_feature:
    keep_alive()

# run background task
background_dtw_check.start()

# run bot
bot.run(token)