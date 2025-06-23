import random

import requests
import json
import os
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class PixivCrawler:
    def __init__(self, username, password, use_selenium=True):
        self.session = requests.Session()
        self.base_url = "https://www.pixiv.net"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.pixiv.net/"
        }
        self.username = username
        self.password = password

        # 使用Selenium登录或Cookie登录
        if use_selenium:
            self.login_with_selenium()
        else:
            # 如果有保存的cookies，可以直接加载
            if os.path.exists("pixiv_cookies.json"):
                self.load_cookies()
            else:
                print("未找到已保存的cookies，请先使用Selenium登录")

    def login_with_selenium(self):
        """使用Selenium进行登录"""
        print("正在使用Selenium登录Pixiv...")

        # 设置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 无头模式，可注释此行以显示浏览器窗口
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        # 初始化WebDriver
        driver = webdriver.Chrome(options=chrome_options)

        try:
            # 打开登录页
            driver.get("https://accounts.pixiv.net/login")

            # 输入用户名和密码
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username']"))
            )

            # 输入用户名
            username_input = driver.find_element(By.CSS_SELECTOR, "input[autocomplete='username']")
            username_input.send_keys(self.username)

            # 点击登录按钮进入密码输入界面
            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()

            # 等待密码输入框出现
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='current-password']"))
            )

            # 输入密码
            password_input = driver.find_element(By.CSS_SELECTOR, "input[autocomplete='current-password']")
            password_input.send_keys(self.password)

            # 点击登录按钮
            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()

            # 等待登录完成
            WebDriverWait(driver, 15).until(
                EC.url_contains("https://www.pixiv.net")
            )

            print("登录成功！")

            # 获取cookies并保存到会话
            cookies = driver.get_cookies()
            for cookie in cookies:
                self.session.cookies.set(cookie['name'], cookie['value'])

            # 保存cookies以便后续使用
            self.save_cookies()

        except Exception as e:
            print(f"登录过程中出错: {e}")
        finally:
            driver.quit()

    def save_cookies(self):
        """保存cookies到文件"""
        with open("pixiv_cookies.json", "w") as f:
            json.dump(requests.utils.dict_from_cookiejar(self.session.cookies), f)

    def load_cookies(self):
        """从文件加载cookies"""
        with open("pixiv_cookies.json", "r") as f:
            cookies = json.load(f)
        self.session.cookies = requests.utils.cookiejar_from_dict(cookies)

    def search_images(self, keyword, page_limit=3):
        """通过关键词搜索图片"""
        all_image_ids = []
        for page in range(1, page_limit + 1):
            search_url = f"https://www.pixiv.net/ajax/search/artworks/{keyword}?word={keyword}&order=date_d&mode=all&p={page}&s_mode=s_tag&type=all"
            response = self.session.get(search_url, headers=self.headers)

            try:
                data = json.loads(response.text)
                if data.get("error", False):
                    print(f"搜索出错: {data.get('message', '未知错误')}")
                    break

                image_data = data["body"]["illustManga"]["data"]
                for item in image_data:
                    all_image_ids.append(item["id"])

                print(f"已获取第{page}页，共{len(image_data)}张图片")
            except Exception as e:
                print(f"处理第{page}页时出错: {e}")
                break

            time.sleep(1)  # 防止请求过快

        return all_image_ids

    def download_image(self, keyword,image_id, save_dir="pixiv_images"):
        """下载指定ID的图片"""
        # 创建保存目录
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # 获取图片详情
        detail_url = f"https://www.pixiv.net/ajax/illust/{image_id}"
        print(detail_url)
        response = self.session.get(detail_url, headers=self.headers)
        data = json.loads(response.text)

        if data.get("error", False):
            print(f"获取图片{image_id}详情出错: {data.get('message', '未知错误')}")
            return

        # 获取原图URL
        illust = data["body"]
        title = illust["title"]
        original_url = illust["urls"]["original"]

        # 确保文件名有效

        filename = f"{image_id}_{re.sub(r'[/:*?<>|]', '_', title)}{os.path.splitext(original_url)[1]}"

        #if keyword in filename:
        # 下载图片
        try:
            headers = self.headers.copy()
            headers["Referer"] = f"https://www.pixiv.net/artworks/{image_id}"
            response = self.session.get(original_url, headers=headers, stream=True)

            if response.status_code == 200:
                with open(os.path.join(save_dir, filename), "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                print(f"已下载: {filename}")
                return filename
            else:
                print(f"下载失败 {image_id}: HTTP状态码 {response.status_code}")
        except Exception as e:
            print(f"下载图片{image_id}时出错: {e}")


def get_pixiv(keyword):
    # 请替换为你的账号和密码
    username = ""
    password = ""

    crawler = PixivCrawler(username, password, use_selenium=True)
    page_limit = 1

    print(f"开始搜索关键词: {keyword}")
    image_ids = crawler.search_images(keyword, page_limit)

    if not image_ids:
        print("未找到符合条件的图片或登录状态失效")
        return

    print(f"找到{len(image_ids)}张图片，开始下载...")
    n = 0
    for image_id in image_ids:
        #while n < random.randrange(1,10):
        file_name = crawler.download_image(keyword,image_id)
        time.sleep(1)  # 防止请求过快
        n += 1
        if n >= random.randrange(1,10):
            break
    print("已完成下载")
    return file_name
