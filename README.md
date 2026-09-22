# Facebook Page Reels Bot

Docker bot that watches `videos/` and publishes queued videos as Facebook Page Reels through Meta's Graph API.

IMPORTANT: Meta's documented Facebook Reels API is for Facebook Pages. This bot does not automate a Professional Mode personal profile.

## Quick start

1. Create a Meta developer app: https://developers.facebook.com/
2. Use Graph API Explorer: https://developers.facebook.com/tools/explorer/
3. Generate a User Access Token with the Page permissions Meta currently makes available.
4. Get your Page ID and Page Access Token using `/me/accounts?fields=name,access_token,tasks`.
5. Copy `.env.example` to `.env` and fill in the values.
6. Put Reel videos in `videos/`.
7. Run `docker compose up -d --build`.

Meta's official API collection documents the Reel flow as initialize -> upload -> publish. Current documented media requirements include 9:16, minimum 540x960, and 4-60 seconds.

## GitHub

Create a PRIVATE GitHub repository. Never commit `.env`, tokens, passwords, or `data/reels.db`.

```bash
git init
git add .
git commit -m "Initial Facebook Reels bot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/facebook-reels-bot.git
git push -u origin main
```

GitHub stores the source code. For a 24/7 bot, run the Docker container on a VPS/cloud server.

On the server:

```bash
git clone https://github.com/YOUR_USERNAME/facebook-reels-bot.git
cd facebook-reels-bot
nano .env
docker compose up -d --build
docker compose logs -f
```

Add new videos by copying them into `videos/`; no restart is required.

Set `POST_INTERVAL_MINUTES=360` for 6 hours. Set `REPEAT=true` to loop through the collection indefinitely.
