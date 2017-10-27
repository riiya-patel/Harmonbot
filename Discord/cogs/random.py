
import discord
from discord.ext import commands

import asyncio
from bs4 import BeautifulSoup
import calendar
import concurrent.futures
import csv
import datetime
import dice
import inspect
import json
import multiprocessing
import pydealer
import pyparsing
import random
import string
import xml.etree.ElementTree

import clients
import credentials
from modules import utilities
from utilities import checks

def setup(bot):
	bot.add_cog(Random(bot))

class Random:
	
	def __init__(self, bot):
		self.bot = bot
		# Add commands as random subcommands
		for name, command in inspect.getmembers(self):
			if isinstance(command, commands.Command) and command.parent is None and name != "random":
				self.bot.add_command(command)
				self.random.add_command(command)
		# Add fact subcommands as subcommands of corresponding commands
		for command, parent in ((self.fact_cat, self.cat), (self.fact_date, self.date), (self.fact_number, self.number)):
			utilities.add_as_subcommand(self, command, parent, "fact")
		# Add random subcommands as subcommands of corresponding commands
		self.random_subcommands = ((self.color, "Resources.color"), (self.giphy, "Resources.giphy"), (self.map, "Resources.map"), (self.streetview, "Resources.streetview"), (self.uesp, "Search.uesp"), (self.wikipedia, "Search.wikipedia"), (self.xkcd, "Resources.xkcd"))
		for command, parent_name in self.random_subcommands:
			utilities.add_as_subcommand(self, command, parent_name, "random")
		# Import jokes
		self.jokes = []
		try:
			with open(clients.data_path + "/jokes.csv", newline = "") as jokes_file:
				jokes_reader = csv.reader(jokes_file)
				for row in jokes_reader:
					self.jokes.append(row[0])
		except FileNotFoundError:
			pass
	
	def __unload(self):
		for command, parent_name in self.random_subcommands:
			utilities.remove_as_subcommand(self, parent_name, "random")
	
	@commands.group(invoke_without_command = True)
	@checks.not_forbidden()
	async def random(self, ctx):
		'''
		Random things
		All random subcommands are also commands
		'''
		await ctx.embed_reply(":grey_question: Random what?")
	
	@random.command()
	@checks.not_forbidden()
	async def color(self, ctx):
		'''Information on a random color'''
		url = "http://www.colourlovers.com/api/colors/random?numResults=1&format=json"
		cog = self.bot.get_cog("Resources")
		if cog: await cog.process_color(ctx, url)
	
	@random.command()
	@checks.not_forbidden()
	async def giphy(self, ctx):
		'''Random gif from giphy'''
		url = "http://api.giphy.com/v1/gifs/random?api_key={}".format(credentials.giphy_public_beta_api_key)
		async with clients.aiohttp_session.get(url) as resp:
			data = await resp.json()
		await ctx.embed_reply(image_url = data["data"]["image_url"])
	
	@random.command()
	@checks.not_forbidden()
	async def map(self, ctx):
		'''See map of random location'''
		latitude = random.uniform(-90, 90)
		longitude = random.uniform(-180, 180)
		map_url = "https://maps.googleapis.com/maps/api/staticmap?center={},{}&zoom=13&size=640x640".format(latitude, longitude)
		await ctx.embed_reply("[:map:]({})".format(map_url), image_url = map_url)
	
	@random.command()
	@checks.not_forbidden()
	async def streetview(self, ctx):
		'''Generate street view of a random location'''
		latitude = random.uniform(-90, 90)
		longitude = random.uniform(-180, 180)
		image_url = "https://maps.googleapis.com/maps/api/streetview?size=400x400&location={},{}".format(latitude, longitude)
		await ctx.embed_reply(image_url = image_url)
	
	@random.command()
	@checks.not_forbidden()
	async def uesp(self, ctx):
		'''
		Random UESP page
		[UESP](http://uesp.net/wiki/Main_Page)
		'''
		cog = self.bot.get_cog("Search")
		if cog: await cog.process_uesp(None, random = True)
		else: await ctx.embed_reply(title = "Random UESP page", title_url = "http://uesp.net/wiki/Special:Random") # necessary?
	
	@random.command(aliases = ["wiki"])
	@checks.not_forbidden()
	async def wikipedia(self, ctx):
		'''Random Wikipedia article'''
		cog = self.bot.get_cog("Search")
		if cog: await cog.process_wikipedia(None, random = True)
		else: await ctx.embed_reply(title = "Random Wikipedia article", title_url = "https://wikipedia.org/wiki/Special:Random") # necessary?
	
	@random.command()
	@checks.not_forbidden()
	async def xkcd(self, ctx):
		'''Random xkcd'''
		async with clients.aiohttp_session.get("http://xkcd.com/info.0.json") as resp:
			data = await resp.text()
		total = json.loads(data)["num"]
		url = "http://xkcd.com/{}/info.0.json".format(random.randint(1, total))
		cog = self.bot.get_cog("Resources")
		if cog: await cog.process_xkcd(ctx, url)
	
	@commands.command()
	@checks.not_forbidden()
	async def card(self, ctx):
		'''Random playing card'''
		await ctx.embed_reply(":{}: {}".format(random.choice(pydealer.const.SUITS).lower(), random.choice(pydealer.const.VALUES)))
	
	@commands.group(invoke_without_command = True)
	@checks.not_forbidden()
	async def cat(self, ctx, *, category : str = ""):
		'''
		Random image of a cat
		cat categories (cats) for different categories you can choose from
		cat <category> for a random image of a cat from that category
		'''
		if category and category in ("categories", "cats"):
			async with clients.aiohttp_session.get("http://thecatapi.com/api/categories/list") as resp:
				data = await resp.text()
			try:
				categories = xml.etree.ElementTree.fromstring(data).findall(".//name")
			except xml.etree.ElementTree.ParseError:
				await ctx.embed_reply(":no_entry: Error")
			else:
				await ctx.embed_reply('\n'.join(sorted(category.text for category in categories)))
		elif category:
			async with clients.aiohttp_session.get("http://thecatapi.com/api/images/get?format=xml&results_per_page=1&category={}".format(category)) as resp:
				data = await resp.text()
			try:
				url = xml.etree.ElementTree.fromstring(data).find(".//url")
			except xml.etree.ElementTree.ParseError:
				await ctx.embed_reply(":no_entry: Error")
				return
			if url is not None:
				await ctx.embed_reply("[:cat:]({})".format(url.text), image_url = url.text)
			else:
				await ctx.embed_reply(":no_entry: Error: Category not found")
		else:
			async with clients.aiohttp_session.get("http://thecatapi.com/api/images/get?format=xml&results_per_page=1") as resp:
				data = await resp.text()
			try:
				url = xml.etree.ElementTree.fromstring(data).find(".//url").text
			except xml.etree.ElementTree.ParseError:
				await ctx.embed_reply(":no_entry: Error")
			else:
				await ctx.embed_reply("[:cat:]({})".format(url), image_url = url)
	
	@commands.command()
	@checks.not_forbidden()
	async def command(self, ctx):
		'''Random command'''
		await ctx.embed_reply("{}{}".format(ctx.prefix, random.choice(tuple(set(command.name for command in self.bot.commands)))))
	
	@commands.command(aliases = ["die", "roll"])
	@checks.not_forbidden()
	async def dice(self, ctx, *, input : str = '6'):
		'''
		Roll dice
		Inputs:                                      Examples:
		S     |  S - number of sides (default is 6)  [6      | 12]
		AdS   |  A - amount (default is 1)           [5d6    | 2d10]
		AdSt  |  t - return total                    [2d6t   | 20d5t]
		AdSs  |  s - return sorted                   [4d6s   | 5d8s]
		AdS^H | ^H - return highest H rolls          [10d6^4 | 2d7^1]
		AdSvL | vL - return lowest L rolls           [15d7v2 | 8d9v2]
		'''
		# TODO: Add documentation on arithmetic/basic integer operations
		if 'd' not in input:
			input = 'd' + input
		with multiprocessing.Pool(1) as pool:
			async_result = pool.apply_async(dice.roll, (input,))
			future = self.bot.loop.run_in_executor(None, async_result.get, 10.0)
			try:
				result = await asyncio.wait_for(future, 10.0, loop = self.bot.loop)
				if type(result) is int:
					await ctx.embed_reply(result)
				else:
					await ctx.embed_reply(", ".join(str(roll) for roll in result))
			except discord.errors.HTTPException:
				await ctx.embed_reply(":no_entry: Output too long")
			except pyparsing.ParseException:
				await ctx.embed_reply(":no_entry: Invalid input")
			except (concurrent.futures.TimeoutError, multiprocessing.context.TimeoutError):
				await ctx.embed_reply(":no_entry: Execution exceeded time limit")
	
	@commands.group(invoke_without_command = True)
	@checks.not_forbidden()
	async def date(self, ctx):
		'''Random date'''
		await ctx.embed_reply(datetime.date.fromordinal(random.randint(1, 365)).strftime("%B %d"))
	
	@commands.command()
	@checks.not_forbidden()
	async def day(self, ctx):
		'''Random day of week'''
		await ctx.embed_reply(random.choice(calendar.day_name))
	
	@commands.group(invoke_without_command = True)
	@checks.not_forbidden()
	async def dog(self, ctx, *, breed : str = ""):
		'''
		Random image of a dog
		[breed] [sub-breed] to specify a specific sub-breed
		'''
		if breed:
			async with clients.aiohttp_session.get("https://dog.ceo/api/breed/{}/images/random".format(breed.lower().replace(' ', '/'))) as resp:
				data = await resp.json()
			if data["status"] == "error":
				await ctx.embed_reply(":no_entry: Error: {}".format(data["message"]))
			else:
				await ctx.embed_reply("[:dog2:]({})".format(data["message"]), image_url = data["message"])
		else:
			async with clients.aiohttp_session.get("https://dog.ceo/api/breeds/image/random") as resp:
				data = await resp.json()
			await ctx.embed_reply("[:dog2:]({})".format(data["message"]), image_url = data["message"])
	
	@dog.command(name = "breeds", aliases = ["breed", "subbreeds", "subbreed", "sub-breeds", "sub-breed"])
	@checks.not_forbidden()
	async def dog_breeds(self, ctx):
		'''Breeds and sub-breeds of dogs for which images are categorized under'''
		async with clients.aiohttp_session.get("https://dog.ceo/api/breeds/list/all") as resp:
			data = await resp.json()
		breeds = data["message"]
		for breed in breeds:
			breeds[breed] = " ({})".format(", ".join(sub.capitalize() for sub in breeds[breed])) if breeds[breed] else ""
		await ctx.embed_reply(", ".join("**{}**{}".format(breed.capitalize(), breeds[breed]) for breed in breeds), footer_text = "Sub-breeds are in parentheses after the corresponding breed")
	
	@commands.group(invoke_without_command = True)
	@checks.not_forbidden()
	async def fact(self, ctx):
		'''Random fact'''
		url = "http://mentalfloss.com/api/1.0/views/amazing_facts.json?limit=1&bypass={}".format(random.random())
		async with clients.aiohttp_session.get(url) as resp:
			data = await resp.json()
		await ctx.embed_reply(BeautifulSoup(data[0]["nid"]).text)
	
	@fact.command(name = "cat", aliases = ["cats"])
	@checks.not_forbidden()
	async def fact_cat(self, ctx):
		'''Random fact about cats'''
		async with clients.aiohttp_session.get("http://catfacts-api.appspot.com/api/facts") as resp:
			data = await resp.json()
		if data["success"]:
			await ctx.embed_reply(data["facts"][0])
		else:
			await ctx.embed_reply(":no_entry: Error")
	
	@fact.command(name = "date")
	@checks.not_forbidden()
	async def fact_date(self, ctx, date : str):
		'''
		Random fact about a date
		Format: month/date
		Example: 1/1
		'''
		async with clients.aiohttp_session.get("http://numbersapi.com/{}/date".format(date)) as resp:
			if resp.status == 404:
				await ctx.embed_reply(":no_entry: Error")
				return
			data = await resp.text()
		await ctx.embed_reply(data)
	
	@fact.command(name = "math")
	@checks.not_forbidden()
	async def fact_math(self, ctx, number : int):
		'''Random math fact about a number'''
		async with clients.aiohttp_session.get("http://numbersapi.com/{}/math".format(number)) as resp:
			data = await resp.text()
		await ctx.embed_reply(data)
	
	@fact.command(name = "number")
	@checks.not_forbidden()
	async def fact_number(self, ctx, number : int):
		'''Random fact about a number'''
		async with clients.aiohttp_session.get("http://numbersapi.com/{}".format(number)) as resp:
			data = await resp.text()
		await ctx.embed_reply(data)
	
	@fact.command(name = "year")
	@checks.not_forbidden()
	async def fact_year(self, ctx, year : int):
		'''Random fact about a year'''
		async with clients.aiohttp_session.get("http://numbersapi.com/{}/year".format(year)) as resp:
			data = await resp.text()
		await ctx.embed_reply(data)
	
	@commands.command()
	@checks.not_forbidden()
	async def idea(self, ctx):
		'''Random idea'''
		async with clients.aiohttp_session.get("http://itsthisforthat.com/api.php?json") as resp:
			data = await resp.json(content_type = "text/javascript")
		await ctx.embed_reply("{0[this]} for {0[that]}".format(data))
	
	@commands.command()
	@checks.not_forbidden()
	async def insult(self, ctx):
		'''Random insult'''
		async with clients.aiohttp_session.get("http://quandyfactory.com/insult/json") as resp:
			data = await resp.json()
		await ctx.embed_say(data["insult"])
	
	@commands.command()
	@checks.not_forbidden()
	async def joke(self, ctx):
		'''Random joke'''
		# Sources:
		# https://github.com/KiaFathi/tambalAPI
		# https://www.kaggle.com/abhinavmoudgil95/short-jokes (https://github.com/amoudgl/short-jokes-dataset)
		await ctx.embed_reply(random.choice(self.jokes))
	
	@commands.command()
	@checks.not_forbidden()
	async def letter(self, ctx):
		'''Random letter'''
		await ctx.embed_reply(random.choice(string.ascii_uppercase))
	
	@commands.command()
	@checks.not_forbidden()
	async def location(self, ctx):
		'''Random location'''
		await ctx.embed_reply("{}, {}".format(random.uniform(-90, 90), random.uniform(-180, 180)))
	
	@commands.group(aliases = ["rng"], invoke_without_command = True)
	@checks.not_forbidden()
	async def number(self, ctx, number : int = 10):
		'''
		Random number
		Default range is 1 to 10
		'''
		await ctx.embed_reply(random.randint(1, number))
	
	@commands.command(aliases = ["why"])
	@checks.not_forbidden()
	async def question(self, ctx):
		'''Random question'''
		async with clients.aiohttp_session.get("http://xkcd.com/why.txt") as resp:
			data = await resp.text()
		questions = data.split('\n')
		await ctx.embed_reply("{}?".format(random.choice(questions).capitalize()))
	
	@commands.command()
	@checks.not_forbidden()
	async def quote(self, ctx):
		'''Random quote'''
		async with clients.aiohttp_session.get("http://api.forismatic.com/api/1.0/?method=getQuote&format=json&lang=en") as resp:
			try:
				data = await resp.json()
			except:
				await ctx.embed_reply(":no_entry: Error")
				return
		await ctx.embed_reply(data["quoteText"], footer_text = data["quoteAuthor"]) # quoteLink?
	
	@commands.command()
	@checks.not_forbidden()
	async def time(self, ctx):
		'''Random time'''
		await ctx.embed_reply("{:02d}:{:02d}".format(random.randint(0, 23), random.randint(0, 59)))
	
	@commands.command()
	@checks.not_forbidden()
	async def word(self, ctx):
		'''Random word'''
		await ctx.embed_reply(self.bot.wordnik_words_api.getRandomWord().word.capitalize())

