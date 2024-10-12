class DownloadStatusUpdater:
    def __init__(self, db_session: Session):
        self.db = db_session

    def update_status(self, chart_entry_id: int, status: int):
        # 更新 chart_entry 表中的下载状态
        self.db.execute(
            "UPDATE chart_entry SET status = :status WHERE id = :chart_entry_id",
            {'status': status, 'chart_entry_id': chart_entry_id}
        )
        self.db.commit()
        print(f"电影 ID {chart_entry_id} 的状态已更新为 {status}")
