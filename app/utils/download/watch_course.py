import requests
import time
import json
import random
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class CourseWatcher:
    def __init__(self, username, password, watch_time_hours=50, interval_seconds=180):
        self.BASE_URL = "https://gt-java-api.giged.cn:9003/api/v2"
        self.LOGIN_URL = f"{self.BASE_URL}/login/password"
        self.COURSE_LIST_URL = f"{self.BASE_URL}/courses"
        self.COURSE_DETAIL_URL = f"{self.BASE_URL}/course/"
        self.VIDEO_URL = f"{self.BASE_URL}/video/"
        self.VIDEO_RECORD_URL = f"{self.BASE_URL}/video/{{}}/record"
        self.BRANCH_URL = f"{self.BASE_URL}/index/branch"
        self.CATEGORY_URL = f"{self.BASE_URL}/course_categories"
        self.username = username
        self.password = password
        self.watch_time_hours = watch_time_hours
        self.token = None
        self.current_page = 1
        self.total_watch_time = watch_time_hours * 3600
        self.current_watch_time = 0
        self.branches = []
        self.categories = []
        self.completed_courses = set()  # 使用集合存储已观看课程

    def login(self):
        """
        登录并获取token
        """
        data = {"mobile": self.username, "password": self.password}
        response = requests.post(self.LOGIN_URL, json=data)
        if response.status_code == 200:
            response_data = response.json()
            if response_data["status"] == 0:
                self.token = response_data["data"]["token"]
                return True
            else:
                logging.info(f"登录失败: {response_data['message']}")
                return False
        else:
            logging.info(f"登录失败: {response.status_code}")
            return False

    def get_branches(self):
        """
        获取分院列表
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Connection": "keep-alive",
        }
        response = requests.get(self.BRANCH_URL, headers=headers)
        if response.status_code == 200:
            response_data = response.json()
            if response_data["status"] == 0:
                self.branches = [branch["id"] for branch in response_data["data"]]
                return True
            else:
                logging.info(f"获取分院列表失败: {response_data['message']}")
                return False
        else:
            logging.info(f"获取分院列表失败: {response.status_code}")
            return False

    def get_categories(self):
        """
        获取分类列表
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Connection": "keep-alive",
        }
        response = requests.get(self.CATEGORY_URL, headers=headers)
        if response.status_code == 200:
            response_data = response.json()
            if response_data["status"] == 0:
                self.categories = [category["id"] for category in response_data["data"]]
                return True
            else:
                logging.info(f"获取分类列表失败: {response_data['message']}")
                return False
        else:
            logging.info(f"获取分类列表失败: {response.status_code}")
            return False

    def get_course_list(self, category_id=None, branch_id=None, page=1, size=20):
        """
        获取课程列表
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Connection": "keep-alive",
        }
        params = {
            "page": page,
            "size": size,
        }
        if category_id is not None:
            params["category_id"] = category_id
        if branch_id is not None:
            params["branch_id"] = branch_id
        response = requests.get(self.COURSE_LIST_URL, headers=headers, params=params)
        if response.status_code == 200:
            response_data = response.json()
            if response_data["status"] == 0:
                return response_data["data"]["data"]
            else:
                logging.info(f"获取课程列表失败: {response_data['message']}")
                return None
        else:
            logging.info(f"获取课程列表失败: {response.status_code}")
            return None

    def get_course_detail(self, course_id):
        """
        获取课程详情
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Connection": "keep-alive",
        }
        response = requests.get(f"{self.COURSE_DETAIL_URL}{course_id}", headers=headers)
        if response.status_code == 200:
            response_data = response.json()
            if response_data["status"] == 0:
                return response_data["data"]
            else:
                logging.info(f"获取课程详情失败: {response_data['message']}")
                return None
        else:
            logging.info(f"获取课程详情失败: {response.status_code}")
            return None

    def get_video_detail(self, video_id):
        """
        获取视频详情
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Connection": "keep-alive",
        }
        response = requests.get(f"{self.VIDEO_URL}{video_id}", headers=headers)
        if response.status_code == 200:
            response_data = response.json()
            if response_data["status"] == 0:
                return response_data["data"]
            else:
                logging.info(f"获取视频详情失败: {response_data['message']}")
                return None
        else:
            logging.info(f"获取视频详情失败: {response.status_code}")
            return None

    def update_video_record(self, video_id, duration):
        """
        更新视频观看记录
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Connection": "keep-alive",
        }
        data = {"duration": duration}
        record_url = self.VIDEO_RECORD_URL.format(video_id)
        response = requests.post(record_url, headers=headers, json=data)
        if response.status_code == 200:
            response_data = response.json()
            if response_data["status"] == 0:
                return True
            else:
                logging.info(f"更新视频记录失败: {response_data['message']}")
                return False
        else:
            logging.info(f"更新视频记录失败: {response.status_code}")
            return False

    def watch_video(self, video_id, video_duration, interval_seconds=180):
        """模拟观看视频，支持自定义时间间隔"""
        logging.info(f"开始观看视频 {video_id}，预计时长 {video_duration} 秒，间隔 {interval_seconds} 秒")
        try:
            while self.current_watch_time < self.total_watch_time:
                if not self.update_video_record(video_id, self.current_watch_time):
                    logging.error(f"更新视频观看记录失败，跳过当前视频 {video_id}")
                    break
                logging.info(f"已观看 {self.current_watch_time} 秒")
                time.sleep(1)
                self.current_watch_time += interval_seconds
                if self.current_watch_time >= video_duration:
                    logging.info(f"视频 {video_id} 观看完毕")
                    break
        except Exception as e:
            logging.error(f"视频 {video_id} 观看过程中发生错误: {e}")
        finally:
            logging.info(f"视频 {video_id} 观看结束")

    def watch_course(self, course_id, course_title, videos):
        """观看课程，包含所有视频"""
        logging.info(f"开始观看课程 {course_id} - {course_title}")
        try:
            for video_id, video_data_list in videos.items():
                for video_data in video_data_list:
                    video_duration = video_data.get("duration")
                    video_id = video_data.get("id")
                    if video_duration is None or not isinstance(video_duration, (int, float)) or video_id is None:
                        logging.warning(f"视频 {video_id} 数据无效，跳过")
                        continue
                    self.watch_video(video_id, video_duration)
                    self.completed_courses.add(course_id)
        except Exception as e:
            logging.exception(f"课程 {course_id} 观看过程中发生错误: {e}")
    def run(self):
        """
        运行观看课程脚本
        """
        if self.login():
            if self.get_branches() and self.get_categories():
                while self.current_watch_time < self.total_watch_time:
                    # 随机选择分院和分类
                    branch_id = random.choice(self.branches) if self.branches else None
                    category_id = random.choice(self.categories) if self.categories else None
                    #branch_id = 0
                    #category_id = 10274
                    logging.info(f"当前分类：{category_id}，分院：{branch_id}")
                    courses = self.get_course_list(category_id=category_id, branch_id=branch_id, page=self.current_page)
                    if courses:
                        random.shuffle(courses)  # 随机打乱课程顺序
                        for course in courses:
                            course_id = course["id"]
                            if course_id not in self.completed_courses:
                                course_detail = self.get_course_detail(course_id)
                                if course_detail:
                                    course_title = course_detail["course"]["title"]
                                    videos = course_detail["videos"]
                                    if videos:
                                        logging.info(f"当前时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
                                        logging.info(f"课程名称：{course_title}")
                                        logging.info(f"课程ID：{course_id}")
                                        self.watch_course(course_id, course_title, videos)
                                        if self.current_watch_time >= self.total_watch_time:
                                            break
                                    else:
                                        logging.info(f"课程 {course_id} 没有视频")
                                else:
                                    logging.info(f"课程 {course_id} 不存在")
                        self.current_page += 1
                    else:
                        logging.info(f"第 {self.current_page} 页没有课程")
                        #self.current_page += 1
        else:
            logging.info("登录失败")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="观看课程脚本")
    parser.add_argument("username", help="用户名")
    parser.add_argument("password", help="密码")
    parser.add_argument("watch_time_hours", type=int, help="总观看时长（小时）")
    parser.add_argument("--interval", type=int, default=180, help="模拟观看视频的时间间隔（秒），默认为 3 分钟")
    args = parser.parse_args()
    watcher = CourseWatcher(args.username, args.password, args.watch_time_hours, args.interval)
    watcher.run()