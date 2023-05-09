import sqlite3 as sq


def create_table():
    with sq.connect("users.db") as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS user_data (username VARCHAR(30), pair VARCHAR(10), timeframe VARCHAR(5), indicators TEXT)"
        )


async def insert_into_table(state):
    with sq.connect("users.db") as conn:
        cur = conn.cursor()

        async with state.proxy() as data:
            if data["username"] in get_usernames():
                cur.execute(
                    "UPDATE user_data SET pair=?, timeframe=?, indicators=? WHERE username=?",
                    (
                        data["pair"],
                        data["timeframe"],
                        data["indicators"],
                        data["username"],
                    ),
                )

            else:
                cur.execute(
                    "INSERT INTO user_data VALUES (?, ?, ?, ?)", tuple(data.values())
                )


def get_usernames():
    with sq.connect("users.db") as conn:
        cur = conn.cursor()

        tuples = cur.execute("SELECT username FROM user_data").fetchall()
        usernames = [str(tpl[0]) for tpl in tuples]
        return usernames


def get_user_data(username):
    with sq.connect("users.db") as conn:
        cur = conn.cursor()

        user_data = cur.execute(
            "SELECT pair, timeframe, indicators FROM user_data WHERE username=?",
            (username,),
        ).fetchone()
        return user_data
