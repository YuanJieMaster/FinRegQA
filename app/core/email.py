"""
FinRegQA 邮箱模块
Email utilities for QQ email
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import Optional
from .config import settings


class EmailSender:
    """QQ邮箱发送器"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.use_tls = settings.SMTP_USE_TLS
        self.from_name = settings.EMAIL_FROM_NAME
    
    def _get_connection(self) -> smtplib.SMTP:
        """获取SMTP连接"""
        server = smtplib.SMTP(self.smtp_host, self.smtp_port)
        if self.use_tls:
            server.starttls()
        server.login(self.smtp_user, self.smtp_password)
        return server
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """发送邮件"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = Header(f"{self.from_name} <{self.smtp_user}>")
            msg['To'] = Header(to_email)
            msg['Subject'] = Header(subject, 'utf-8')
            
            if text_content:
                msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            with self._get_connection() as server:
                server.sendmail(self.smtp_user, [to_email], msg.as_string())
            return True
        except Exception as e:
            print(f"发送邮件失败: {str(e)}")
            return False
    
    def send_verification_email(self, to_email: str, username: str, token: str) -> bool:
        """发送邮箱验证邮件"""
        verification_url = f"{settings.API_V1_PREFIX}/auth/verify-email?token={token}"
        subject = "【FinRegQA】验证您的邮箱地址"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1>FinRegQA 金融制度知识问答系统</h1>
                </div>
                <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                    <h2>您好，{username}！</h2>
                    <p>感谢您注册 FinRegQA 系统，请点击下面的按钮验证您的邮箱地址：</p>
                    <p style="text-align: center;">
                        <a href="{verification_url}" style="display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px;">验证邮箱</a>
                    </p>
                    <p>此链接将在 <strong>24小时</strong> 后过期。</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self.send_email(to_email, subject, html_content)
    
    def send_password_reset_email(self, to_email: str, username: str, token: str) -> bool:
        """发送密码重置邮件"""
        reset_url = f"{settings.API_V1_PREFIX}/auth/reset-password/confirm?token={token}"
        subject = "【FinRegQA】重置您的账户密码"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1>FinRegQA 金融制度知识问答系统</h1>
                </div>
                <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                    <h2>您好，{username}！</h2>
                    <p>我们收到了您的密码重置请求，请点击下面的按钮重置密码：</p>
                    <p style="text-align: center;">
                        <a href="{reset_url}" style="display: inline-block; background: #f5576c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px;">重置密码</a>
                    </p>
                    <p>此链接将在 <strong>30分钟</strong> 后过期。</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self.send_email(to_email, subject, html_content)


email_sender = EmailSender()
