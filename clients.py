
import discord
from discord.ext import commands
from discord.ext.commands.view import StringView
from discord.ext.commands.context import Context
from discord.ext.commands.errors import CommandNotFound, CommandError
import aiohttp
import cleverbot
import datetime
import inflect
import json
import random
import os
from utilities.help_formatter import CustomHelpFormatter
from modules import utilities

version = "0.31.0"
changelog = "https://discord.gg/a2rbZPu"
wait_time = 15.0
code_block = "```\n{}\n```"
py_code_block = "```py\n{}\n```"
online_time = datetime.datetime.utcnow()
aiohttp_session = aiohttp.ClientSession()
cleverbot_instance = cleverbot.Cleverbot()
inflect_engine = inflect.engine()
application_info = None

class Bot(commands.Bot):
	
	def reply(self, content, *args, **kwargs):
		author = commands.bot._get_variable('_internal_author')
		destination = commands.bot._get_variable('_internal_channel')
		fmt = '{0.display_name}: {1}'.format(author, str(content)) # , -> :
		extensions = ('delete_after',)
		params = {k: kwargs.pop(k, None) for k in extensions}
		coro = self.send_message(destination, fmt, *args, **kwargs)
		return self._augmented_msg(coro, **params)
	
	async def process_commands(self, message):
		_internal_channel = message.channel
		_internal_author = message.author
		view = StringView(message.content)
		if self._skip_check(message.author, self.user):
			return
		prefix = self._get_prefix(message)
		invoked_prefix = prefix
		if not isinstance(prefix, (tuple, list)):
			if not view.skip_string(prefix):
				return
		else:
			invoked_prefix = discord.utils.find(view.skip_string, prefix)
			if invoked_prefix is None:
				return
		invoker = view.get_word().lower() # case insensitive commands
		tmp = {'bot': self, 'invoked_with': invoker, 'message': message, 'view': view, 'prefix': invoked_prefix}
		ctx = Context(**tmp)
		del tmp
		if invoker in self.commands:
			command = self.commands[invoker]
			self.dispatch('command', command, ctx)
			try:
				await command.invoke(ctx)
			except CommandError as e:
				ctx.command.dispatch_error(e, ctx)
			else:
				self.dispatch('command_completion', command, ctx)
		elif invoker:
			exc = CommandNotFound('Command "{}" is not found'.format(invoker))
			self.dispatch('command_error', exc, ctx)

utilities.create_file("prefixes")

def get_prefix(bot, message):
	with open("data/prefixes.json", "r") as prefixes_file:
		all_prefixes = json.load(prefixes_file)
	if message.channel.is_private:
		prefixes = all_prefixes.get(message.channel.id, None)
	else:
		prefixes = all_prefixes.get(message.server.id, None)
	return prefixes if prefixes else '!'

_CustomHelpFormatter = CustomHelpFormatter()

client = Bot(command_prefix = get_prefix, formatter = _CustomHelpFormatter, pm_help = None)
client.remove_command("help")

@client.listen()
async def on_ready():
	global application_info
	application_info = await client.application_info()

for file in os.listdir("cogs"):
	if file.endswith(".py"):
		client.load_extension("cogs." + file[:-3])

# Utilities

async def random_game_status():
	statuses = ["with i7-2670QM", "with mainframes", "with Cleverbot",
	"tic-tac-toe with Joshua", "tic-tac-toe with WOPR", "the Turing test",
	"with my memory", "with R2-D2", "with C-3PO", "with BB-8",
	"with machine learning", "gigs", "with Siri", "with TARS", "with KIPP",
	"with humans", "with Skynet", "Goldbach's conjecture",
	"Goldbach's conjecture solution", "with quantum foam",
	"with quantum entanglement", "with P vs NP", "the Reimann hypothesis",
	"the Reimann proof", "with the infinity gauntlet", "for the other team",
	"hard to get", "to win", "world domination", "with Opportunity",
	"with Spirit in the sand pit", "with Curiousity", "with Voyager 1",
	"music", "Google Ultron", "not enough space here to",
	"the meaning of life is", "with the NSA", "with RSS Bot", " "]
	updated_game = discord.utils.get(client.servers).me.game
	if not updated_game:
		updated_game = discord.Game(name = random.choice(statuses))
	else:
		updated_game.name = random.choice(statuses)
	await client.change_status(game = updated_game)

async def set_streaming_status(client):
	updated_game = discord.utils.get(client.servers).me.game
	if not updated_game:
		updated_game = discord.Game(url = "https://www.twitch.tv/harmonbot", type = 1)
	else:
		updated_game.url = "https://www.twitch.tv/harmonbot"
		updated_game.type = 1
	await client.change_status(game = updated_game)

async def reply(message, response):
	return await client.send_message(message.channel, "{}: {}".format(message.author.mention, response))

async def reply_newline(message, response):
	return await client.send_message(message.channel, "{}:\n{}".format(message.author.mention, response))

async def reply_code(message, response):
	return await client.send_message(message.channel, "{}:\n```{}```".format(message.author.mention, response))

# Restart/Shutdown Tasks

def add_uptime():
	with open("data/stats.json", "r") as stats_file:
			stats = json.load(stats_file)
	now = datetime.datetime.utcnow()
	uptime = now - online_time
	stats["uptime"] += uptime.total_seconds()
	with open("data/stats.json", "w") as stats_file:
		json.dump(stats, stats_file, indent = 4)

def add_restart():
	with open("data/stats.json", "r") as stats_file:
		stats = json.load(stats_file)
	stats["restarts"] += 1
	with open("data/stats.json", "w") as stats_file:
		json.dump(stats, stats_file, indent = 4)

async def leave_all_voice():
	# necessary?
	for voice_client in client.voice_clients:
		await voice_client.disconnect()

async def shutdown_tasks():
	await client.cogs["Audio"].stop_all_streams() # budio - remove
	# await leave_all_voice()
	aiohttp_session.close()
	add_uptime()

async def restart_tasks():
	await shutdown_tasks()
	add_restart()

