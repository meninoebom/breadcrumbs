import os

import uvicorn


def main():
    port = int(os.environ.get("PORT", "8100"))
    uvicorn.run("app.api:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    main()
