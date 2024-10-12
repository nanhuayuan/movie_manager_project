import psycopg2

class MovieRepository:
    def __init__(self, db_config):
        self.connection = psycopg2.connect(**db_config)

    def find_by_title_and_year(self, title, year):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM movies WHERE title = %s AND year = %s", (title, year))
            return cursor.fetchone()

    def save_movie(self, movie):
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO movies (title, year, director, genre) VALUES (%s, %s, %s, %s)",
                (movie['title'], movie['year'], movie.get('director'), movie.get('genre'))
            )
        self.connection.commit()
