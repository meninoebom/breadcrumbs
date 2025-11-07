from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


//GET crumbs get crumbs

//GET crumbs/{id} get crumb

//DELETE crumbs/{id} delete crumb

//GET tags get all tags

//GET tags/{id} get a tag

//DELETE tags/{id} delete a tag


