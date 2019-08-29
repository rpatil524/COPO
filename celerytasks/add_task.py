from web.celery import app


@app.task
def my_add(x, y):
    return x + y
