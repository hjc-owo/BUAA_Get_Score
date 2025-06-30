import time
import yaml
import smtplib
import logging
import os
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webelement import WebElement

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    enabled: bool
    smtp_host: str
    smtp_user: str
    smtp_pass: str
    receiver: str


@dataclass
class Credentials:
    username: str
    password: str


@dataclass
class QueryConfig:
    year: str
    term: str


@dataclass
class Config:
    email: EmailConfig
    credentials: Credentials
    query: QueryConfig

    @classmethod
    def load_from_file(cls, filepath: str) -> 'Config':
        """从YAML文件加载配置"""
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
                return cls(
                    email=EmailConfig(**data["email"]),
                    credentials=Credentials(**data["credentials"]),
                    query=QueryConfig(**data["query"])
                )
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise


@dataclass
class CourseScore:
    name: str
    score: str
    credit: str

    @classmethod
    def from_element(cls, box: WebElement) -> Optional['CourseScore']:
        """从网页元素提取课程成绩信息"""
        try:
            score = box.find_element(By.CLASS_NAME, "score").text
            if not score:
                return None

            course = box.find_element(By.CLASS_NAME, "course")
            name = course.find_element(By.TAG_NAME, "p").text
            credit = course.find_element(By.TAG_NAME, "span").find_element(By.TAG_NAME, "span").text

            return cls(
                name=name,
                score=score,
                credit=credit
            )
        except Exception as e:
            logger.error(f"提取课程信息失败: {e}")
            return None


class ScoreChecker:
    def __init__(self, config: Config):
        self.config = config
        self.driver = None
        self.base_scores: List[CourseScore] = []
        self.is_logged_in = False
        
        # 启动时从markdown文件加载已有成绩
        self.load_existing_scores()

    def load_existing_scores(self) -> None:
        """从markdown文件加载已存在的成绩作为基准成绩"""
        self.base_scores = EmailHandler.load_scores_from_markdown()
        if self.base_scores:
            logger.info(f"已加载 {len(self.base_scores)} 门课程的基准成绩")
        else:
            logger.info("未找到已有成绩记录，将从空开始检测")

    def _init_driver(self) -> webdriver.Chrome:
        """初始化Chrome WebDriver"""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("window-size=1080,1920")
        return webdriver.Chrome(options=options)

    def _navigate_to_semester_by_buttons(self, current_semester: str, target_semester: str) -> None:
        """通过prev/next按钮导航到目标学期"""
        max_attempts = 20  # 防止无限循环
        attempts = 0
        
        while current_semester != target_semester and attempts < max_attempts:
            attempts += 1
            logger.info(f"尝试第{attempts}次，当前: {current_semester}, 目标: {target_semester}")
            
            # 比较学期字符串来决定点击哪个按钮
            # 格式: "2024-2025年第3学期"
            try:
                current_parts = current_semester.replace("年第", "-").replace("学期", "").split("-")
                target_parts = target_semester.replace("年第", "-").replace("学期", "").split("-")
                
                current_year_start = int(current_parts[0])
                current_year_end = int(current_parts[1])
                current_term = int(current_parts[2])
                
                target_year_start = int(target_parts[0])
                target_year_end = int(target_parts[1])
                target_term = int(target_parts[2])
                
                # 比较学年和学期
                if (current_year_start, current_year_end, current_term) < (target_year_start, target_year_end, target_term):
                    # 需要往后（next）
                    self.driver.find_element(By.CLASS_NAME, "next-icon").click()
                else:
                    # 需要往前（prev）
                    self.driver.find_element(By.CLASS_NAME, "prev-icon").click()
                
                time.sleep(1)
                current_semester = self.driver.find_element(By.CSS_SELECTOR, ".demo-select-opt label").text
                
            except Exception as e:
                logger.error(f"解析学期字符串失败: {e}")
                break
        
        if attempts >= max_attempts:
            logger.warning("达到最大尝试次数，停止学期导航")

    def check_login_status(self) -> bool:
        """检查是否处于登录状态"""
        try:
            self.driver.get("https://app.buaa.edu.cn/buaascore/wap/default/index")
            # 尝试找到成绩列表元素，如果能找到说明处于登录状态
            self.driver.find_element(By.CLASS_NAME, "score-list")
            return True
        except WebDriverException:
            return False

    def login(self) -> bool:
        """登录到教务系统"""
        try:
            if not self.driver:
                self.driver = self._init_driver()

            # 如果已经登录，直接返回
            if self.is_logged_in and self.check_login_status():
                return True

            self.driver.get("https://sso.buaa.edu.cn")
            time.sleep(2)

            iframe = self.driver.find_element(By.TAG_NAME, "iframe")
            self.driver.switch_to.frame(iframe)

            self.driver.find_element(By.NAME, "username").send_keys(self.config.credentials.username)
            self.driver.find_element(By.NAME, "password").send_keys(self.config.credentials.password)
            self.driver.find_element(By.CLASS_NAME, "submit-btn").click()

            # 登录成功后设置状态
            self.is_logged_in = True
            logger.info("登录成功")
            return True
        except WebDriverException as e:
            logger.error(f"登录失败: {e}")
            self.is_logged_in = False
            return False

    def get_scores(self) -> List[CourseScore]:
        """获取成绩列表"""
        try:
            # 如果未登录，先尝试登录
            if not self.is_logged_in:
                if not self.login():
                    return []

            self.driver.get("https://app.buaa.edu.cn/buaascore/wap/default/index")
            
            # 选择指定的学年学期
            target_semester = f"{self.config.query.year}年第{self.config.query.term}学期"
            
            try:
                # 先检查当前选中的学期
                current_label = self.driver.find_element(By.CSS_SELECTOR, ".demo-select-opt label").text
                logger.info(f"当前学期: {current_label}")
                
                if current_label != target_semester:
                    logger.info(f"需要切换到: {target_semester}")
                    # 使用按钮方式切换学期
                    self._navigate_to_semester_by_buttons(current_label, target_semester)
                else:
                    logger.info("当前已是目标学期")
                    
            except Exception as e:
                logger.error(f"学期选择失败: {e}")

            score_boxes = self.driver.find_elements(By.CLASS_NAME, "score-list")
            scores = []

            for box in score_boxes:
                score = CourseScore.from_element(box)
                if score:
                    scores.append(score)

            return scores
        except WebDriverException as e:
            logger.error(f"获取成绩失败: {e}")
            self.is_logged_in = False  # 出错时重置登录状态
            return []

    def check_new_scores(self) -> None:
        """检查新成绩并发送通知"""
        current_scores = self.get_scores()

        # 如果获取成绩失败（返回空列表）且之前有基准成绩，保持原有基准成绩不变
        if not current_scores and self.base_scores:
            logger.warning("获取成绩失败，保持原有基准成绩")
            return

        # 如果有成绩数据，保存到markdown文件
        if current_scores:
            EmailHandler.save_scores_to_markdown(current_scores)

        # 检查是否有新课程（基于课程名称）
        base_course_names = {score.name for score in self.base_scores}
        current_course_names = {score.name for score in current_scores}
        new_course_names = current_course_names - base_course_names
        
        if new_course_names:
            title = f"新出了{len(new_course_names)}门成绩：{'，'.join(new_course_names)}"
            content = EmailHandler.generate_content(current_scores, self.config.email.enabled)

            EmailHandler.send_mail(
                self.config.email,
                title,
                content
            )
            
        # 更新基准成绩（无论是否有新课程，都要更新以反映成绩变化）
        if current_scores:
            self.base_scores = current_scores

    def close(self) -> None:
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.is_logged_in = False


class EmailHandler:
    @staticmethod
    def generate_content(scores: List[CourseScore], html_format: bool = True) -> str:
        """生成邮件内容"""
        if html_format:
            msg = """
            <html>
            <head></head>
            <body>
            <p>本学期的课程成绩如下:</p>
            <table border="1">
            <tr><th>课程</th><th>成绩</th><th>学分</th></tr>
            """
            for score in scores:
                msg += f"<tr><td>{score.name}</td><td>{score.score}</td><td>{score.credit}</td></tr>"
            msg += "</table></body></html>"
        else:
            msg = ""
            for score in scores:
                msg += f"科目：{score.name}，成绩{score.score}，学分{score.credit}\n"
        return msg

    @staticmethod
    def generate_markdown_content(scores: List[CourseScore]) -> str:
        """生成markdown格式的成绩内容"""
        if not scores:
            return "# 成绩记录\n\n暂无成绩记录。\n"
        
        content = "# 成绩记录\n\n"
        content += f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "| 课程名称 | 成绩 | 学分 |\n"
        content += "|---------|------|------|\n"
        
        for score in scores:
            content += f"| {score.name} | {score.score} | {score.credit} |\n"
        
        content += f"\n总计：{len(scores)} 门课程\n"
        return content

    @staticmethod
    def save_scores_to_markdown(scores: List[CourseScore], filename: str = "score.md") -> None:
        """将成绩保存到markdown文件"""
        try:
            content = EmailHandler.generate_markdown_content(scores)
            with open(filename, "w", encoding="utf-8") as file:
                file.write(content)
            logger.info(f"成绩已保存到 {filename}")
        except Exception as e:
            logger.error(f"保存成绩到文件失败: {e}")

    @staticmethod
    def load_scores_from_markdown(filename: str = "score.md") -> List[CourseScore]:
        """从markdown文件中读取成绩数据"""
        scores = []
        try:
            if not os.path.exists(filename):
                logger.info(f"文件 {filename} 不存在，跳过加载")
                return scores
            
            with open(filename, "r", encoding="utf-8") as file:
                lines = file.readlines()
            
            # 寻找表格内容，跳过表头
            in_table = False
            for line in lines:
                line = line.strip()
                # 跳过表头和分隔线
                if line.startswith("| 课程名称") or line.startswith("|------"):
                    in_table = True
                    continue
                
                # 如果遇到空行或总计行，表格结束
                if in_table and (not line or line.startswith("总计")):
                    break
                
                # 解析表格行
                if in_table and line.startswith("|") and line.endswith("|"):
                    parts = [part.strip() for part in line.split("|")[1:-1]]  # 去掉首尾的空字符串
                    if len(parts) == 3:
                        name, score, credit = parts
                        scores.append(CourseScore(name=name, score=score, credit=credit))
            
            logger.info(f"从 {filename} 加载了 {len(scores)} 门课程成绩")
            return scores
            
        except Exception as e:
            logger.error(f"从文件加载成绩失败: {e}")
            return []

    @staticmethod
    def send_mail(config: EmailConfig, title: str, content: str, max_retries: int = 3) -> None:
        """发送邮件，支持重试机制"""
        if not config.enabled:
            logger.info("邮件服务未启用，跳过发送邮件")
            logger.info(content)
            return

        for attempt in range(max_retries):
            smtp = None
            try:
                message = MIMEMultipart("related")
                message["From"] = Header(config.smtp_user)
                message["To"] = Header(config.receiver, "utf-8")
                message["Subject"] = Header(title, "utf-8")
                message.attach(MIMEText(content, "html", "utf-8"))

                smtp = smtplib.SMTP_SSL(config.smtp_host, 465)
                smtp.login(config.smtp_user, config.smtp_pass)
                smtp.sendmail(config.smtp_user, config.receiver, message.as_string())
                logger.info("邮件发送成功")
                return

            except smtplib.SMTPServerDisconnected as e:
                logger.error(f"服务器连接断开 (尝试 {attempt + 1}/{max_retries}): {e}")
                time.sleep(2)
            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"邮箱认证失败: {e}")
                return
            except Exception as e:
                # 检查是否是退出时的错误
                if "queued as" in str(e).lower():
                    logger.info("邮件发送成功")
                    return
                logger.error(f"发送邮件失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                time.sleep(2)
            finally:
                # 安全关闭SMTP连接
                if smtp:
                    try:
                        smtp.close()
                    except:
                        pass

        logger.error("邮件发送失败，已达到最大重试次数")


def main():
    config = Config.load_from_file("config_hy.yaml")
    checker = ScoreChecker(config)

    try:
        # 首次运行，尝试登录
        if not checker.login():
            logger.error("首次登录失败，程序退出")
            return

        while True:
            try:
                logger.info("检查成绩中...")
                checker.check_new_scores()

            except Exception as e:
                logger.error(f"检查成绩出错: {e}")
                checker.is_logged_in = False  # 重置登录状态

            time.sleep(60)

    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
    finally:
        checker.close()


if __name__ == "__main__":
    main()
