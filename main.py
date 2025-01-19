import time
import yaml
import smtplib
import logging
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

    def _init_driver(self) -> webdriver.Chrome:
        """初始化Chrome WebDriver"""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("window-size=1080,1920")
        return webdriver.Chrome(options=options)

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

        if len(current_scores) > len(self.base_scores):
            new_courses = [s.name for s in current_scores if s not in self.base_scores]
            title = f"新出了{len(new_courses)}门成绩：{'，'.join(new_courses)}"
            content = EmailHandler.generate_content(current_scores, self.config.email.enabled)

            EmailHandler.send_mail(
                self.config.email,
                title,
                content
            )
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
    config = Config.load_from_file("config.yaml")
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
