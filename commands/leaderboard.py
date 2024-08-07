import discord
from discord import app_commands, Color
import discord.ext
from discord.ui import View
from discord.ext import commands
import sqlite3

import discord.ext.tasks

class leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.connection = sqlite3.connect(f"{self.bot.path}{self.bot.pathtype}content{self.bot.pathtype}sql{self.bot.pathtype}lb.db")
        self.cursor = self.connection.cursor()

        #self.optOutList = self.cursor.execute(f"SELECT userID FROM optOutList;").fetchall()
        self.optOutList = []

    # # Refresh opt out list function
    # async def refreshOptOutList(self):
    #     try:
    #         self.cursor.execute(f"DELETE FROM optOut;")
    #         self.connection.commit()

    #         for id in self.optOutList:
    #             self.cursor.execute(f"INSERT INTO optOut (userID) VALUES (?)", (id,))
            
    #         return True, ""
    #     except Exception as e:
    #         return False, e
                
    # Listen for Messages
    @commands.Cog.listener()
    async def on_message(self, message):
        # Catch possible errors
        try:
            # Check if user is Bot
            if message.author.bot != True:
                if not(message.author.id in self.optOutList):
                    # Check if server is in DB
                    if self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{str(message.guild.id)}';").fetchone() != None:
                        # Check if user is already on leaderboard
                        if self.cursor.execute(f"SELECT userMention FROM '{message.guild.id}' WHERE userMention = '{message.author.mention}';").fetchone() != None:
                            # User is on the leaderboard, update their values
                            self.cursor.execute(f"UPDATE '{message.guild.id}' SET messageCount = messageCount + 1, wordCount = wordCount + {len((message.content).split())}, attachmentCount = attachmentCount + {len(message.attachments)} WHERE userMention = ?", (message.author.mention,))
                        else:
                            # User is not on leaderboard, add them to the leaderboard
                            self.cursor.execute(f"INSERT INTO '{message.guild.id}' (userMention, messageCount, wordCount, attachmentCount) VALUES (?, 1, {len((message.content).split())}, {len(message.attachments)})", (message.author.mention,))
                        
                        # Commit to DB
                        self.connection.commit()
                    else:
                        pass
            else:
                pass
        # This should never happen, but if there is an error, log it
        except Exception as error:
            print("Error occurred while logging message for leaderboard!")
            print(error)
    
    # Leaderboard Command
    @app_commands.command(name = "leaderboard", description = "View the server message leaderboard.")
    @app_commands.choices(sort_type=[
        app_commands.Choice(name="Messages Sent", value="messageCount"),
        app_commands.Choice(name="Words Sent", value="wordCount"),
        app_commands.Choice(name="Attachments Sent", value="attachmentCount"),
        ])
    @app_commands.checks.cooldown(1, 10)
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    async def leaderboard(self, interaction: discord.Interaction, sort_type: app_commands.Choice[str]):
        await interaction.response.defer()
        
        pages = []
        
        # Send initial embed
        embed = discord.Embed(title = "Loading...")
        embed.set_footer(text = f"Requested by {interaction.user.name}", icon_url = interaction.user.avatar.url)
        await interaction.followup.send(embed = embed)

        try:
            i = 0
            pageStr = ""
            
            if self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{str(interaction.guild.id)}';").fetchone() != None:
                vals = self.cursor.execute(f"SELECT userMention, {sort_type.value} FROM '{interaction.guild.id}' ORDER BY {sort_type.value} DESC").fetchall()
                if vals != []:
                    for val in vals:
                        i += 1
                        
                        if pageStr == "":
                            pageStr += f"{i}. {val[0]}: {val[1]}"
                        else:
                            pageStr += f"\n{i}. {val[0]}: {val[1]}"

                        # If there's 10 items in the current page, we split it into a new page
                        if i % 10 == 0:
                            pages.append(pageStr)
                            pageStr = ""

                    if pageStr != "":
                        pages.append(pageStr)
                else:
                    pages.append("No Data")
                
                class Leaderboard(View):
                    def __init__(self, pages):
                        super().__init__()
                        self.page = 0
                        self.pages = pages
                
                    @discord.ui.button(label="<", style=discord.ButtonStyle.green, custom_id="prev")
                    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                        if self.page > 0:
                            self.page -= 1
                        else:
                            self.page = len(self.pages) - 1
                        embed = discord.Embed(title = f"Server Leaderboard - {sort_type.name}", description = self.pages[self.page], color = Color.random())
                        embed.set_footer(text = f"Currently controlling: {interaction.user.name} - Page {self.page + 1}/{len(self.pages)}", icon_url = interaction.user.avatar.url)
                        await interaction.response.edit_message(embed = embed)

                    @discord.ui.button(label=">", style=discord.ButtonStyle.green, custom_id="next")
                    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                        if self.page < len(self.pages) - 1:
                            self.page += 1
                        else:
                            self.page = 0
                        embed = discord.Embed(title = f"Server Leaderboard - {sort_type.name}", description = self.pages[self.page], color = Color.red())
                        embed.set_footer(text = f"Currently controlling: {interaction.user.name} - Page {self.page + 1}/{len(self.pages)}", icon_url = interaction.user.avatar.url)
                        await interaction.response.edit_message(embed = embed)

                embed = discord.Embed(title = f"Server Leaderboard - {sort_type.name}", description=pages[0], color = Color.random())
                embed.set_footer(text = f"Currently controlling: {interaction.user.name} - Page 1/{len(pages)}", icon_url = interaction.user.avatar.url)
                
                if len(pages) == 1:
                    await interaction.edit_original_response(embed = embed)
                else:
                    await interaction.edit_original_response(embed = embed, view = Leaderboard(pages))
            else:
                embed = discord.Embed(title = "Not Enabled", description = "The message leaderboard is not enabled in this server.", color = Color.red())
                await interaction.edit_original_response(embed = embed)
        except Exception:
            embed = discord.Embed(title = "Unexpected Error", description = "Please try again later or message <@563372552643149825> for assistance.", color = Color.red())
            await interaction.edit_original_response(embed = embed, view = None)
    
    context = discord.app_commands.AppCommandContext(guild=True, dm_channel=False, private_channel=False)
    lbGroup = app_commands.Group(name="lb-control", description="Control the leaderboard.", allowed_contexts=context)

    # Enable LB command
    @lbGroup.command(name = "enable", description = "Enable the message leaderboard.")
    @app_commands.checks.has_permissions(administrator=True)
    async def enable_lb(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral = True)
        
        embed = discord.Embed(title = "Enabling...", color = Color.orange())
        await interaction.edit_original_response(embed = embed)

        try:
            if self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{str(interaction.guild.id)}';").fetchone() != None:
                embed = discord.Embed(title = "Success", description = "Already enabled for this server.", color = Color.green())
                await interaction.edit_original_response(embed = embed)
            else:
                self.cursor.execute(f"CREATE TABLE '{interaction.guild.id}' (userMention text, messageCount integer, wordCount integer, attachmentCount integer)")
                self.connection.commit()
                
                embed = discord.Embed(title = "Success", description = "Enabled message leaderboard for this server.", color = Color.green())
                await interaction.edit_original_response(embed = embed)
        except Exception:
            embed = discord.Embed(title = "Unexpected Error", description = "Please try again later or message <@563372552643149825> for assistance.", color = Color.red())
            await interaction.edit_original_response(embed = embed, view = None)
    
    # Disable LB command
    @lbGroup.command(name = "disable", description = "Disable the message leaderboard.")
    @app_commands.checks.has_permissions(administrator=True)
    async def disable_lb(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral = True)
        
        async def delete_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral = True)

            embed = discord.Embed(title = "Disabling...", color = Color.orange())
            await interaction.edit_original_response(embed = embed, view = None)

            try:
                if self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{interaction.guild.id}';").fetchone() == None:
                    embed = discord.Embed(title = "Failed", description = "Leaderboard is already disabled in this server.", color = Color.red())
                    await interaction.edit_original_response(embed = embed)
                else:
                    self.cursor.execute(f"DROP TABLE '{interaction.guild.id}'")
                    self.connection.commit()

                    embed = discord.Embed(title = "Disabled.", color = Color.green())
                    await interaction.edit_original_response(embed = embed)
            except Exception:
                embed = discord.Embed(title = "Unexpected Error", description = "Please try again later or message <@563372552643149825> for assistance.", color = Color.red())
                await interaction.edit_original_response(embed = embed, view = None)
                
        view = View()
        delete_button = discord.ui.Button(label='Delete', style=discord.ButtonStyle.red)
        delete_button.callback = delete_callback
        view.add_item(delete_button)

        embed = discord.Embed(title = "Are you sure?", description = "The leaderboard will be disabled, and data for this server will be deleted!", color = Color.orange())
        await interaction.followup.send(embed = embed, view = view, ephemeral = True)
    
    # # Opt out command
    # @lbGroup.command(name = "opt-out", description = "Opt out of the leaderboard globally as a user.")
    # async def optOut_lb(self, interaction: discord.Interaction):
    #     await interaction.response.defer(ephemeral = True)
        
    #     async def delete_callback(interaction: discord.Interaction):
    #         await interaction.response.defer(ephemeral = True)

    #         embed = discord.Embed(title = "Opting out...", color = Color.orange())
    #         await interaction.edit_original_response(embed = embed, view = None)

    #         try:
    #             if interaction.user.id in self.optOutList:
    #                 embed = discord.Embed(title = "Failed", description = "You have already opted out.", color = Color.red())
    #                 await interaction.edit_original_response(embed = embed)
    #             else:
    #                 self.optOutList.remove(interaction.user.id)
    #                 status, error = await self.refreshOptOutList(self)

    #                 for server in self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{interaction.guild.id}';").fetchall():
    #                     self.cursor.execute(f"DELETE FROM '{server}' WHERE userMention = '<@{interaction.user.id}>';")
                    
    #                 self.connection.commit()

    #                 if status == False:
    #                     embed = discord.Embed(title = "Unexpected Error", description = "Please try again later or message <@563372552643149825> for assistance.", color = Color.red())
    #                     await interaction.edit_original_response(embed = embed, view = None)

    #                 embed = discord.Embed(title = "You have opted out.", color = Color.green())
    #                 await interaction.edit_original_response(embed = embed)
    #         except Exception:
    #             embed = discord.Embed(title = "Unexpected Error", description = "Please try again later or message <@563372552643149825> for assistance.", color = Color.red())
    #             await interaction.edit_original_response(embed = embed, view = None)
                
    #     view = View()
    #     delete_button = discord.ui.Button(label='Opt Out', style=discord.ButtonStyle.red)
    #     delete_button.callback = delete_callback
    #     view.add_item(delete_button)

    #     embed = discord.Embed(title = "Are you sure?", description = "By opting out of the leaderboard, you will be unable to contribute to the Titanium leaderboard in any server.", color = Color.orange())
    #     await interaction.followup.send(embed = embed, view = view, ephemeral = True)
    
    # # Opt out command
    # @lbGroup.command(name = "opt-in", description = "Opt back in to the leaderboard globally as a user.")
    # async def optIn_lb(self, interaction: discord.Interaction):
    #     await interaction.response.defer(ephemeral = True)
        
    #     async def delete_callback(interaction: discord.Interaction):
    #         await interaction.response.defer(ephemeral = True)

    #         embed = discord.Embed(title = "Opting in...", color = Color.orange())
    #         await interaction.edit_original_response(embed = embed, view = None)

    #         try:
    #             if not(interaction.user.id in self.optOutList):
    #                 embed = discord.Embed(title = "Failed", description = "You are already opted in.", color = Color.red())
    #                 await interaction.edit_original_response(embed = embed)
    #             else:
    #                 self.optOutList.remove(interaction.user.id)
    #                 status, error = await self.refreshOptOutList(self)

    #                 if status == False:
    #                     embed = discord.Embed(title = "Unexpected Error", description = "Please try again later or message <@563372552643149825> for assistance.", color = Color.red())
    #                     await interaction.edit_original_response(embed = embed, view = None)

    #                 embed = discord.Embed(title = "You have opted in.", color = Color.green())
    #                 await interaction.edit_original_response(embed = embed)
    #         except Exception:
    #             embed = discord.Embed(title = "Unexpected Error", description = "Please try again later or message <@563372552643149825> for assistance.", color = Color.red())
    #             await interaction.edit_original_response(embed = embed, view = None)
                
    #     view = View()
    #     delete_button = discord.ui.Button(label='Opt In', style=discord.ButtonStyle.green)
    #     delete_button.callback = delete_callback
    #     view.add_item(delete_button)

    #     embed = discord.Embed(title = "Are you sure?", description = "By opting in to the leaderboard, you will be able to contribute to the Titanium leaderboard in any server again.", color = Color.orange())
    #     await interaction.followup.send(embed = embed, view = view, ephemeral = True)
    
    # Reset LB command
    @lbGroup.command(name = "reset", description = "Resets the message leaderboard.")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_lb(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral = True)
        
        embed = discord.Embed(title = "Loading...", color = Color.orange())
        await interaction.followup.send(embed = embed, ephemeral = True)
        
        if self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{interaction.guild.id}';").fetchone() == None:
            embed = discord.Embed(title = "Disabled", description = "Leaderboard is disabled in this server.", color = Color.red())
            await interaction.edit_original_response(embed = embed)
        else:
            async def delete_callback(interaction: discord.Interaction):
                await interaction.response.defer(ephemeral = True)

                embed = discord.Embed(title = "Resetting...", color = Color.orange())
                await interaction.edit_original_response(embed = embed, view = None)

                try:
                    self.cursor.execute(f"DELETE FROM '{interaction.guild.id}';")
                    self.connection.commit()

                    embed = discord.Embed(title = "Reset.", color = Color.green())
                    await interaction.edit_original_response(embed = embed)
                except Exception:
                    embed = discord.Embed(title = "Unexpected Error", description = "Please try again later or message <@563372552643149825> for assistance.", color = Color.red())
                    await interaction.edit_original_response(embed = embed, view = None)
                    
            view = View()
            delete_button = discord.ui.Button(label='Reset', style=discord.ButtonStyle.red)
            delete_button.callback = delete_callback
            view.add_item(delete_button)

            embed = discord.Embed(title = "Are you sure?", description = "The leaderboard will be reset and all data will be removed!", color = Color.orange())
            await interaction.edit_original_response(embed = embed, view = view)

    # Reset LB command
    @lbGroup.command(name = "reset-user", description = "Resets a user on the leaderboard.")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_userlb(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer(ephemeral = True)
        
        embed = discord.Embed(title = "Loading...", color = Color.orange())
        await interaction.followup.send(embed = embed, ephemeral = True)
        
        if self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{interaction.guild.id}';").fetchone() == None:
            embed = discord.Embed(title = "Disabled", description = "Leaderboard is disabled in this server.", color = Color.red())
            await interaction.edit_original_response(embed = embed)
        else:
            async def delete_callback(interaction: discord.Interaction):
                await interaction.response.defer(ephemeral = True)

                embed = discord.Embed(title = "Removing...", color = Color.orange())
                await interaction.edit_original_response(embed = embed, view = None)

                try:
                    self.cursor.execute(f"DELETE FROM '{interaction.guild.id}' WHERE userMention = '{user.mention}';")
                    self.connection.commit()

                    embed = discord.Embed(title = "Removed.", color = Color.green())
                    await interaction.edit_original_response(embed = embed)
                except Exception:
                    embed = discord.Embed(title = "Unexpected Error", description = "Please try again later or message <@563372552643149825> for assistance.", color = Color.red())
                    await interaction.edit_original_response(embed = embed, view = None)
                    
            view = View()
            delete_button = discord.ui.Button(label='Remove', style=discord.ButtonStyle.red)
            delete_button.callback = delete_callback
            view.add_item(delete_button)

            embed = discord.Embed(title = "Are you sure?", description = f"Are you sure you want to remove {user.mention} from the leaderboard?", color = Color.orange())
            await interaction.edit_original_response(embed = embed, view = view)

    # Privacy command
    @lbGroup.command(name = "privacy", description = "View the leaderboard privacy disclaimer.")
    async def privacy(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral = True)

        title = "Leaderboard Privacy Disclaimer"
        description = "The leaderboard system tracks the following information:"
        description += "\n\n-User Mention\n-Message Count\n-Word Count\n-Attachment Count\n-Server ID"
        description += "Message content is temporarily stored while word count is processed. "
        description += "A list of attachments in the target message is also temporarily stored, so we can work out how many attachments are in your message. "
        description += "Message content and attachment data can not be viewed at any point during the tracking process, and is not saved after it has been processed."
        description += "The leaderboard does not contain any sensitive information, such as:"
        description += "\n\n-User PFP\n-Message Content\n-Attachment Data"
        
        embed = discord.Embed(title = title, description = description)
        await interaction.followup.send(embed = embed, ephemeral = True)
        
async def setup(bot):
    await bot.add_cog(leaderboard(bot))