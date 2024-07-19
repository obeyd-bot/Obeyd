# Obeyd Bot

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

Feel free to reach out if you have any questions or need further assistance.
