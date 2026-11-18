# Public demo: deploy and screenshots

## 1. Deploy the read-only demo on Render

1. Push the latest code to GitHub.
2. Render dashboard: New > Blueprint > pick this repository.
3. When Render asks for the blueprint file, use `render-demo.yaml` (not `render.yaml`).
4. Set `GEMINI_API_KEY` (only needed for chat and research). `DEMO_MODE=true` is already in the file.
5. Wait for the build. The demo seeds itself on every start (`scripts/seed_demo`).
6. Open `https://<your-demo>.onrender.com/docs` and check that reading works.

## 2. Check it from your PC

The free tier sleeps. The first call can take about a minute, so run it twice if it times out.

## 3. Screenshots for the README

Save PNG files in `docs/screenshots/` with these names:

| File | What to capture |
|------|-----------------|
| `dashboard-stories.png` | Dashboard, Stories tab |
| `dashboard-chat.png` | Chat tab with a cited answer |
| `dashboard-research.png` | Research tab with a report |
| `email-digest.png` | The daily digest email |
| `telegram-alert.png` | A breaking alert in Telegram |

Hide any email address, token or key before saving.
