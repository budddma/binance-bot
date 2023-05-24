import sqlite3 as sq


def create_table():
    global conn, cur
    conn = sq.connect("users.db")
    cur = conn.cursor()

    conn.execute(
        "CREATE TABLE IF NOT EXISTS user_data (username VARCHAR(30), pair VARCHAR(10), timeframe VARCHAR(5), indicators TEXT)"
    )
    conn.commit()


def get_usernames():
    tuples = cur.execute("SELECT username FROM user_data").fetchall()
    usernames = [str(tpl[0]) for tpl in tuples]
    conn.commit()
    return usernames


async def insert_into_table(state):
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
    conn.commit()


def get_user_data(username):
    user_data = cur.execute(
        "SELECT pair, timeframe, indicators FROM user_data WHERE username=?",
        (username,),
    ).fetchone()
    conn.commit()
    return user_data
