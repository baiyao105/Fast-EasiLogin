import uvicorn

from shared.storage import load_appsettings


def main():
    appsettings = load_appsettings()
    port = int(appsettings.get("port", 24300))
    uvicorn.run("api.api:app", host="0.0.0.0", port=port, server_header=False)


if __name__ == "__main__":
    main()
