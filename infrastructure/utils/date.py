import datetime


def get_current_colombian_time() -> datetime.datetime:
    date = datetime.datetime.now(datetime.UTC)
    return date - datetime.timedelta(hours=5)
