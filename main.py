import os

import uvicorn


def main():
    port = int(os.environ.get("PORT", "8100"))
    is_dev = os.environ.get("ENVIRONMENT", "development") == "development"
    uvicorn.run("app.api:app", host="0.0.0.0", port=port, reload=is_dev)


if __name__ == "__main__":
    main()
