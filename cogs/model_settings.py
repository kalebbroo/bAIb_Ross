import discord
from discord.ext import commands

class ModelSettings(commands.Cog):
    """The logic and methods for changing the model settings"""
    def __init__(self, bot: commands.Bot):
        """Initialize the cog."""
        self.bot = bot
        self.cmd_cog = self.bot.get_cog("Commands")

    """The model settings logic for when the user is selecting settings.
    
    This part of the code manages the flow of selecting various settings for the model generation.
    It handles the steps, CFG scale, LORA, embeddings, and image size, guiding the user through these
    settings via interactive menus.
    """

    async def model_setting(self, bot, interaction, settings_data, start=0):
        model_list = await self.get_model_list()

        # Prepare options for the SettingsSelect
        # Only take 24 models starting from the index 'start'
        options = [discord.SelectOption(label=model['title'], value=model['name']) for model in model_list[start:start + 24]]

        # Add "Show more models..." if there are more models to show
        if len(model_list) > start + 24:
            options.append(discord.SelectOption(label='Show more models...', value='Show more models...'))

        # Initialize the next_setting function
        next_setting = self.steps_setting

        # Create an instance of SettingsSelect
        return ModelSettings.SettingsSelect(bot=bot, placeholder='Choose a Model', 
                                       options=options, next_setting=next_setting,
                                       settings_data=settings_data, model_list=model_list, start=start)
    
    
    def steps_setting(self, bot, settings_data, model_list):
        step_values = {
                        1: "1 (Unusable)", 
                        5: "5 (Very Low)", 
                        8: "8 (Low)",
                        10: "10 (*Recommended* for speed)", 
                        15: "15 (Above Avg.)", 
                        16: "16 (Good)",
                        17: "17 (Good+)", 
                        18: "18 (Good++)",
                        19: "19 (Very Good)", 
                        20: "20 (Recommended balance)", 
                        25: "25 (High, Slower)", 
                        30: "30 (High, Slower++)", 
                        35: "35 (Very High, Long Wait)", 
                        40: "40 (Not Worth It, Very Long Wait)",
                        60: "60 (This is too much, don't do it)",
                        80: "80 (This could break the bot)",
                        100: "100 (What is wrong with you?)",
                        120: "120 (Way to kill the invironment)",
                    }
        steps = [discord.SelectOption(label=label, value=key) for key, label in step_values.items()]
        return ModelSettings.SettingsSelect(bot, "Choose Steps", steps, self.cfgscale_setting, settings_data, model_list)

    def cfgscale_setting(self, bot, settings_data, model_list):
        cfgscale_descriptions = {
                                1: "1 (AI Imagination is weird)",
                                2: "2 (Creative, will ignore prompt)",
                                3: "3 (Creative)",
                                4: "4 (Creative+)",
                                5: "5 (Balanced)",
                                6: "6 (Balanced+)",
                                7: "7 (Balanced++)",
                                8: "8 (Guided)",
                                9: "9 (Requires Detailed Prompt)",
                                10: "10 (Max, Not Recommended)"
                            }
        cfgscale = [discord.SelectOption(label=cfgscale_descriptions[i], value=str(i)) for i in range(1, 11)]
        return ModelSettings.SettingsSelect(bot, "Choose CFG Scale", cfgscale, self.lora_setting, settings_data, model_list)


    def lora_setting(self, bot, settings_data, model_list):
        lora = [discord.SelectOption(label="Placeholder", value="Placeholder")]
        return ModelSettings.SettingsSelect(bot, "Choose LORA", lora, self.embedding_setting, settings_data, model_list)

    def embedding_setting(self, bot, settings_data, model_list):
        embedding = [discord.SelectOption(label="Placeholder", value="Placeholder")]
        return ModelSettings.SettingsSelect(bot, "Choose Embeddings", embedding, self.size_setting, settings_data, model_list)

    def scale_to_aspect_ratio(self, base_width, base_height, aspect_ratio):
        w, h = map(int, aspect_ratio.split(":"))
        new_width = base_width
        new_height = int((new_width * h) / w)
        if new_height > base_height:
            new_height = base_height
            new_width = int((new_height * w) / h)
        return new_width, new_height

    def size_setting(self, bot, settings_data, model_list):
        model_name = settings_data.get("Choose a Model")
        chosen_model = next((model for model in model_list if model["name"] == model_name), None)

        if chosen_model:
            standard_width = chosen_model.get("standard_width")
            standard_height = chosen_model.get("standard_height")
        else:
            standard_width = 1024  # Default values
            standard_height = 1024

        aspect_ratios = {
            "1:1": "1:1 Square", 
            "4:3": "4:3 Standard Landscape", 
            "3:2": "3:2 Classic Landscape", 
            "8:5": "8:5 Landscape", 
            "16:9": "16:9 Widescreen Landscape",
            "21:9": "21:9 Ultra-Widescreen Landscape",
            "3:4": "3:4 Standard Portrait",
            "2:3": "2:3 Classic Portrait",
            "5:8": "5:8 Portrait",
            "9:16": "9:16 Widescreen Portrait",
            "9:21": "9:21 Ultra-Widescreen Portrait"
        }
        size_values = {}
        for aspect_ratio, label in aspect_ratios.items():
            width, height = self.scale_to_aspect_ratio(standard_width, standard_height, aspect_ratio)
            size_values[label] = (width, height)

        size_options = [discord.SelectOption(label=f"{label} ({width}x{height})", value=f"{width}-{height}") for label, (width, height) in size_values.items()]
        return ModelSettings.SettingsSelect(bot, "Choose Size", size_options, None, settings_data)
                    
    class SettingsSelect(discord.ui.Select):
        def __init__(self, bot, placeholder, options, next_setting=None, settings_data=None, model_list=None, start=0):
            super().__init__(placeholder=placeholder, options=options, row=0)
            self.bot = bot
            self.next_setting = next_setting
            self.settings_data = settings_data or {}
            self.model_list = model_list
            self.start = start

        async def callback(self, interaction: discord.Interaction):
            selected_value = self.values[0]

            # Initialize the embed with a default title and description
            embed = discord.Embed(
                title=f"Change Settings",
                description="Choose an option.",
                color=discord.Color.purple()
            )

            # Handle the "Show more models..." option
            if selected_value == 'Show more models...':
                next_select_menu = await self.bot.get_cog("Commands").model_setting(self.bot, interaction, self.settings_data, start=self.start + 24)
                view = discord.ui.View()
                view.add_item(next_select_menu)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                return
            else:
                # Save the selected setting in setting_data
                self.settings_data[self.placeholder] = selected_value

            # Prepare for the next setting
            if self.next_setting:
                await interaction.response.defer(ephemeral=True)
                next_select_menu = self.next_setting(self.bot, self.settings_data, self.model_list)
                view = discord.ui.View()
                view.add_item(next_select_menu)
            else:
                cmd_cog = self.bot.get_cog("Commands")
                user_id = str(interaction.user.id)
                cmd_cog.user_settings[user_id]["settings_data"].update(self.settings_data)
                modal = cmd_cog.Txt2imgModal(self.bot, interaction, self.bot.ran_prompt, self.bot.ran_negative)
                await interaction.response.send_modal(modal)
                ai = self.bot.get_cog("AIPromptGenerator")
                self.bot.ran_prompt, self.bot.ran_negative = await ai.gen_random_prompt()
                return
                
            # Initialize the embed for the current setting
            match self.placeholder:
                case "Choose Steps":
                    embed = discord.Embed(
                        title="CFG Scale Setting",
                        description="""This parameter can be seen as the “Creativity vs. Prompt” scale. Lower numbers give the AI more freedom to be creative, 
                                        while higher numbers force it to stick more to the prompt.
                        
                                    CFG 2 - 4: Creative, but might be too distorted and not follow the prompt. Can be fun and useful for short prompts
                                    CFG 5 - 8: Recommended for most prompts. Good balance between creativity and guided generation
                                    CFG 9 - 10: When you're sure that your prompt is detailed and very clear on what you want the image to look like
                                    CFG 11 - 20: Not generally recommended almost never usable""",
                        color=discord.Color.purple()
                    )
                    embed.set_image(url="https://i0.wp.com/blog.openart.ai/wp-content/uploads/2023/02/Screen-Shot-2023-02-13-at-5.25.57-PM.png?resize=768%2C213&ssl=1")
                    embed.add_field(name="Tip for Beginners", 
                                    value="Try different scales to explore various artistic effects.")

                case "Choose CFG Scale":
                    embed = discord.Embed(
                        title="LoRA Configuration",
                        description="""LoRA stands for Low-Rank Adaptation. It allows you to use low-rank adaptation technology to quickly fine-tune diffusion models. 
                        To put it in simple terms, the LoRA training model makes it easier to train Stable Diffusion on different concepts, 
                        such as characters or a specific style. These trained models then can be exported and used by others in their own generations.
                        You want a specific celeberity? Use a LoRA model trained on that celeberity. You want a specific style? Use a LoRA model trained on that style.
                        
                        SD 1.5 (512x512) LoRA can only be used with 1.5 models. SD XL (1024x1024) LoRA can only be used with XL models. Ask for more to be added!!""",
                        color=discord.Color.purple()
                    )
                    embed.set_image(url="https://techpp.com/wp-content/uploads/2022/10/how-to-train-stable-diffusion.jpg")
                    embed.add_field(name="Tip for Beginners", 
                                    value="If you're unsure, just skip this setting.")

                case "Choose LORA":
                    embed = discord.Embed(
                        title="Embedding Options",
                        description="""What is an Embedding?
                        The embedding layer encodes inputs such as text prompts into low-dimensional vectors that map features of an object. 
                        These vectors guide the Stable Diffusion model to produce images to match the user's input.
                        Do you want specific poses or angles? Use a pose embedding. Do you want specific colors? Use a color embedding.
                        Ask for more to be added!!""",
                        color=discord.Color.purple()
                    )
                    embed.set_image(url="https://149868225.v2.pressablecdn.com/wp-content/uploads/2023/06/212048-1024x859.jpg")
                    embed.add_field(name="Tip for Beginners", 
                                    value="If you're unsure, just skip this setting.")

                case "Choose Embeddings":
                    embed = discord.Embed(
                        title="Image Size Selection",
                        description="""This setting allows you to choose the dimensions of 
                        the output image. Different sizes will have an impact on the processing 
                        time and quality. Please not depending on the model, you will not get good image results with all sizes.
                        It is better to use the default size (1:1) and upscale an image you like.""",
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="Tip for Beginners", 
                                    value="Start with 1:1 so it will use the default size of the chosen model.")
                    
                case "Choose a Model":
                    embed = discord.Embed(
                            title="Step Selection",
                            description="""The 'Steps' setting controls the number of iterations 
                            the algorithm will perform. A higher number generally means better 
                            quality but will require more time to process.""",
                            color=discord.Color.purple()
                        )
                    embed.set_image(url="https://i0.wp.com/blog.openart.ai/wp-content/uploads/2023/02/Screen-Shot-2023-02-13-at-5.11.28-PM.png?resize=1024%2C602&ssl=1")
                    embed.add_field(name="Tip for Beginners", 
                                    value="Start with a lower number of steps `10` to get quicker results, then increase for better quality.")
                    embed.add_field(name="Note", value="Remember, these settings will affect both the processing time and the output quality.")
                    embed.set_footer(text="Use the menu below to make your selection, or press the 'skip' option.")

            # Common fields that appear in all embeds
            embed.add_field(name="Note", value="Remember, these settings will affect both the processing time and the output quality.")
            embed.set_footer(text="Use the menu below to make your selection, or press the 'skip' option.")
            
            # Send the embed
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

# The setup function to add the cog to the bot
async def setup(bot: commands.Bot):
    """Setup function to add the Cog to the bot.
    Args:
        bot: The Discord bot.
    """
    await bot.add_cog(ModelSettings(bot))