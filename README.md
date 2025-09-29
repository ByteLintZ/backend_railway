# AI Chatbot Platform - Railway Backend

This folder contains a production-ready backend for deployment on Railway.

## How to use
1. Copy all backend files (except data, logs, and local-only configs) into this folder.
2. Add your `.env.railway` file and set all secrets in Railway dashboard.
3. Push this folder to a new GitHub repo and connect it to Railway.
4. Deploy and monitor from Railway dashboard.

## Included
- All backend app code
- requirements.txt
- Dockerfile
- Procfile
- .env.railway (example, do not commit secrets)

## Not included
- /data (user conversations)
- /logs (runtime logs)
- Any local dev/test scripts

---

For help, see the main project README or ask GitHub Copilot!
