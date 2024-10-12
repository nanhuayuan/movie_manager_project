import os

class MovieListProcessor:
    def __init__(self, file_path):
        self.file_path = file_path

    def parse_movie_list(self):
        movies = []
        with open(self.file_path, 'r') as file:
            for line in file:
                title, year = self.extract_movie_data(line)
                if title:
                    movies.append({'title': title, 'year': year})
        return movies

    def extract_movie_data(self, line):
        # 假设每一行是 “电影名称 (年份)” 的格式
        if '(' in line and ')' in line:
            title = line.split('(')[0].strip()
            year = line.split('(')[1].split(')')[0].strip()
            return title, year
        return None, None
