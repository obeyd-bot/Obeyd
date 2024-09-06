# Obeyd Bot

## Overview

Welcome to the `Obeyd` Bot! This bot delivers a fresh, random joke straight to your chat, guaranteed to brighten your day. Whether you're looking for a quick laugh or want to liven up a conversation, this bot has you covered with a wide variety of jokes.

## Setup Instructions

### 1. Create a Testing Bot

To test the changes you made to the bot, you need a testing bot. Follow these steps:

1. Open Telegram and start a chat with [BotFather](https://t.me/BotFather).
2. Create a new bot using the `/newbot` command.
3. Follow the prompts to name your bot and obtain a bot token.

### 2. Configure Environment Variables

1. Copy the `app.env.sample` file to a new file named `app.env`:

```bash
cp app.env.sample app.env
```

2. Open `app.env` and fill in the necessary variables, including the bot token obtained from BotFather.

### 3. Start the Server

To start the server, run the following command:
```bash
docker compose up --build
```

## Contributions

We welcome contributions to expand the bot's joke database, add new features, or improve existing functionality. Here's how you can help:

- Submit Jokes: Add your favorite jokes to our collection by submitting a pull request.
- Improve the Bot: Help us enhance the bot's performance or add new features (like joke categories or user interaction commands).
- Report Issues: If you encounter any bugs or have suggestions, feel free to open an issue!

Whether you're a seasoned developer or just getting started, we'd love to have you contribute to making this bot more fun for everyone!
