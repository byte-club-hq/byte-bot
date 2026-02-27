# byte-bot

A helpful Discord bot for the Byte Club community.

## Getting Started

To get started with developing Byte Bot locally, follow these steps:

1. [Install UV](https://docs.astral.sh/uv/getting-started/installation/). This is a project dependency manager that will
   keep your dependencies local to this project.
2. Clone the repository by running the following command in your terminal *from the directory where you want to store
   the project*:
   ```bash
   git clone https://github.com/byte-club-hq/byte-bot.git
   ```
3. Navigate to the project directory:
   ```bash
   cd byte-bot
   ```
4. Run the following command to install the project dependencies:
   ```bash
   uv sync
   ```

5. Set your IDE interpreter to the python executable in your project's .venv directory.
   This will ensure that your IDE uses the correct dependencies when running the bot.

6. Create a `.env` file in the root of the project and add your Discord bot token.
    1. You can create a bot and get your token from
       the [Discord Developer Portal](https://discord.com/developers/applications).
    2. The `.env` file should look something like this:
         <!-- Please add new .env vars here as needed -->
         ```bash
         DISCORD_BOT_TOKEN=your_discord_bot_token_here
         ```

    3. **WARNING**: This token is unique to YOU and YOU ONLY. DO NOT commit this token to the repo, or you risk exposing
       your bot
       to malicious actors who could use it to take control of your bot and potentially cause harm to your server or
       users.
       Always keep your token secure and never share it with anyone.
7. In the developer portal `Bot` section enable the `Server Members` and `Message Content` intents and click save
   changes.
8. In the developer portal `Installation` section, only check the `Guild Install`, ensuring to uncheck the `User Install`.
9. In the `Default Install Settings` section, ensure you have the following Scopes and permissions:
   - Scopes: `applications.commands` and `bot`
   - Permissions: `Add Reactions`, `Attach Files`, `Embed Links`, `Manage Messages`, `Manage Threads`, `Read Message History`, `Send Messages`, `Send Messages in Threads`, `Use External Emojis`, `View Channels`
10. In the `Install Link` section ensure `Discord Provided Link` is selected. Copy the URL
    1. Copy and Paste this link into your browser and choose the server you want to add the bot to. You must have the
       `Manage Server` permission in that server to be able to add the bot.
11. Run the bot using the following command:
   ```bash
   uv run python -m byte_bot
   ```
   - At this point the bot should appear online in the server you invited it to!

### Optional/Recommended plugins and extensions

Below are not required plugins, but are helpful for development and improving the overall experience of working on this
project.
If you are using a different IDE, there may be similar plugins/extensions available for your IDE.

#### VS Code

These following plugins are recommended if you are using VS Code as your IDE:

- [Better TOML](https://marketplace.visualstudio.com/items?itemName=bungcip.better-toml) - If you are using VS Code,
  this
  extension will provide better syntax highlighting and error checking for the `pyproject.toml` file, which is used
  to manage the project dependencies and settings.
- [Ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) - If you are using VS Code, this
  extension
  will provide linting and formatting for your Python code, which will help you write cleaner and more consistent
  code.
- [Python Docstring Generator](https://marketplace.visualstudio.com/items?itemName=njpwerner.autodocstring) - If you are
  using VS Code, this extension will help you generate docstrings for your functions and classes, which will make
  your code easier to understand and maintain.
- [GitLens](https://marketplace.visualstudio.com/items?itemName=eamodio.gitlens) - If you are using VS Code, this
  extension will provide enhanced Git integration, which will help you manage your branches, commits, and pull
  requests more effectively.

If you are using PyCharm, all of the above features are built in, so you shouldn't need any additional plugins or
extensions.

## Contributing

This is a project specifically geared toward collaboration and learning, so contributions of all kinds are welcome!

- This project is by learners for learners, so it is appreciated that contributors do the work themselves. This isn't
  to say you can't use AI or other resources to help you, but vibe coding is discouraged.

- To contribute, please find an issue that is geared to your skill level and create a branch relative to that ticket
  name/number.
    - For example, if you are working on issue #1, you would create a branch called `issue-1` or something similar.

- Please be descriptive in your commits and pull requests, so that others can understand the changes you made and why
  you made them.
- Please comment your code as much as possible, so that others can understand what you are doing and why you are doing
  it.
- Please use descriptive variable and function names, so that others can understand what your code is doing without
  having to read through it line by line.

## Discord.py Basics:

### Contexts

[Contexts](https://discordpy.readthedocs.io/en/stable/ext/commands/api.html#discord.ext.commands.Context) are objects
that
represent the context in which a command is being invoked. They contain information about the message that triggered the
command, the user who invoked the command, the channel in which the command was invoked, and other relevant information.

### Cogs

[Cogs](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html) are a way to organize your bot's commands and
events into separate classes. This can help keep your code organized
and the bot's functionality modular. Each cog is a class that inherits from `commands.Cog` and contains methods that are
decorated with @commands.Something to indicate that they are commands or event listeners.
You can then load these cogs into your bot to add their functionality dynamically.

### Listeners

[Listeners](https://discordpy.readthedocs.io/en/stable/ext/commands/api.html#discord.ext.commands.Cog.listener) are
functions that are decorated with @commands.Cog.listener() and are used to listen for specific events that
occur in the Discord server. For example, you can create a listener for the `on_message` event, which will be triggered
every time a message is sent in the server.

### Commands

[HybridCommands](https://discordpy.readthedocs.io/en/stable/ext/commands/api.html#discord.ext.commands.hybrid_command)
are
methods of your cog decorated with @commands.hybrid_command() that can be invoked by users in the Discord server. The
params of the method are expected to be shown to the user when they try to use the command.

- Typehinting/variable naming are crucial to ensuring that the command is displayed correctly and that the user knows
  what a param does.
- The docstring of this method is displayed as the help text for a given command (only applicable to slash commands).
- Hybrid commands can be invoked as either a text command (e.g. `!mycommand`) or as a slash command (e.g. `/mycommand`),
  giving users flexibility in how they interact with your bot.

### Checks

[Checks](https://discordpy.readthedocs.io/en/stable/ext/commands/api.html#checks) are function decorators that are used
to
determine whether a command should be executed or not. They are typically used to check for permissions, roles, or other
conditions.

These decorators expect a predicate function that takes a `Context` object as its only parameter and returns a boolean
value.
If the function returns `True`, the command will be executed. If it returns `False`, the command will not be executed
and an error message
may be sent to the user.
