import os

import boto3

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_REGION = os.getenv("AWS_REGION")

aws = boto3.resource(
    "ec2",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION,
)
bot = commands.Bot(command_prefix="!")


def get_instance_state():
    instance_iter = aws.instances.filter(
        Filters=[{"Name": "tag:Name", "Values": ["GeeksInc Minecraft Server"]}]
    )
    instance = [i for i in instance_iter.all()][0]

    return instance


@bot.command(name="status", help="Gets the current status of the server")
async def status(ctx):
    await ctx.send("Checking Server Status")
    instance = get_instance_state()
    await ctx.send(f"Server Status: {instance.state['Name']}")


@bot.command(name="start", help="Starts the server")
async def start(ctx):
    await ctx.send("Starting server")
    instance = get_instance_state()
    if instance.state["Name"] != "running":
        instance.start()
        instance.wait_until_running()
    await ctx.send(f"Server running at {instance.public_ip_address}")


@bot.command(name="stop", help="Stops the server")
async def stop(ctx):
    await ctx.send("Stopping server")
    instance = get_instance_state()
    if instance.state["Name"] == "running":
        instance.stop()
        instance.wait_until_stopped()
    await ctx.send("Server is stopped")


@bot.command(name="ip", help="Responds with the IP of the server")
async def get_ip(ctx):
    instance = get_instance_state()
    if instance.state["Name"] == "running":
        await ctx.send(f"Server IP: {instance.public_ip_address}")
    else:
        await ctx.send(f"Server is not running")


bot.run(TOKEN)
