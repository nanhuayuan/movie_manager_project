class MagnetManager:
    def __init__(self, db_session: Session):
        self.db = db_session

    def add_magnet_link(self, movie_id: int, magnet_link: str, magnet_name: str):
        # 插入磁力链接到数据库
        self.db.execute(
            "INSERT INTO magnet (movie_id, link, name) VALUES (:movie_id, :link, :name)",
            {'movie_id': movie_id, 'link': magnet_link, 'name': magnet_name}
        )
        self.db.commit()
        print(f"磁力链接 {magnet_name} 已插入数据库")
