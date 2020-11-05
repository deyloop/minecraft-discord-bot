import os

import boto3
import asyncio

from discord.ext import commands
from dotenv import load_dotenv
from mcstatus import MinecraftServer

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


class Timer:
    def __init__(self, timeout, callback, job_args):
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.ensure_future(self._job(job_args))

    async def _job(self, job_args):
        await asyncio.sleep(self._timeout)
        await self._callback(*job_args)

    def cancel(self):
        self._task.cancel()


MCSERVERTIMEOUT = 2.5 * 60  # 2.5 mins


async def server_stop_timer(ctx, i):
    # check server status
    instance = get_instance_state()
    if instance.state["Name"] == "running":
        server = MinecraftServer(instance.public_ip_address, 25565)
        status = server.status()
        if status.players.online == 0:
            if i == 0:
                # check to see if it remains inactive after TIMEOUT
                Timer(MCSERVERTIMEOUT, server_stop_timer, (ctx, 1))
            elif i == 1:
                # it has been 2 * TIMEOUT seconds with no activity
                # so stop the server
                await ctx.send(
                    f"No activity in server for {2*MCSERVERTIMEOUT/60} mins. Stopping Server"
                )
                instance.stop()
                instance.wait_until_stopped()
                await ctx.send("Server Stopped")
        else:
            # players are playing... check again after timout
            Timer(
                MCSERVERTIMEOUT,
                server_stop_timer,
                (ctx, 0),
            )
    else:
        # nothing to do, the server was shut down by users
        return


@bot.command(name="status", help="Gets the current status of the server")
async def status(ctx):
    await ctx.send("Checking Server Status")
    instance = get_instance_state()
    response = f"Server Status: {instance.state['Name']}"
    if instance.state["Name"] == "running":
        response = response + (f"\nIP: {instance.public_ip_address}")
        server = MinecraftServer(instance.public_ip_address, 25565)
        status = server.status()
        response = (
            response
            + f"\n{status.players.online} player{' is' if status.players.online == 1 else 's are'} online"
        )
    await ctx.send(response)


@bot.command(name="start", help="Starts the server")
async def start(ctx):
    await ctx.send("Starting server")
    instance = get_instance_state()
    if instance.state["Name"] != "running":
        instance.start()
        instance.wait_until_running()

        Timer(
            MCSERVERTIMEOUT,
            server_stop_timer,
            (ctx, 0),
        )
    await ctx.send(f"Server running at {instance.public_ip_address}")


@bot.command(name="stop", help="Stops the server, only if no players are online")
async def stop(ctx):
    await ctx.send("Stopping server")
    instance = get_instance_state()
    if instance.state["Name"] == "running":
        server = MinecraftServer(instance.public_ip_address, 25565)
        status = server.status()
        if status.players.online != 0:
            await ctx.send(
                f"There is/are {status.players.online} players(s) still playing\n. Can not stop server."
            )
            return
        else:
            instance.stop()
            instance.wait_until_stopped()
    await ctx.send("Server is stopped")


@bot.command(name="playing", help="Displays the names of players currently playing")
async def players(ctx):
    await ctx.send("Checking who is playing")
    instance = get_instance_state()
    if instance.state["Name"] == "running":
        server = MinecraftServer(instance.public_ip_address, 25565)
        query = server.query()
        if query.players.online > 0:
            await ctx.send(
                "Currently playing:\n {0}".format("\n".join(query.players.names))
            )
        else:
            await ctx.send("No one is playing")
    else:
        await ctx.send(f"The server is not running")


@bot.command(name="ip", help="Responds with the IP of the server")
async def get_ip(ctx):
    instance = get_instance_state()
    if instance.state["Name"] == "running":
        await ctx.send(f"Server IP: {instance.public_ip_address}")
    else:
        await ctx.send(f"Server is not running")


bot.run(TOKEN)
