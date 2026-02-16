def dev():
    import uvicorn
    uvicorn.run("app.api:app", host="0.0.0.0", port=8100, reload=True)
