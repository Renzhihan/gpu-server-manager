import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from config.settings import Config
import json
import os


class EmailService:
    """邮件通知服务"""

    SMTP_CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../../data/smtp_config.json')

    # 常见邮箱服务商配置模板
    SMTP_TEMPLATES = {
        'gmail': {
            'name': 'Gmail',
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'smtp_use_tls': True,
            'smtp_use_ssl': False,
            'note': '需要开启"两步验证"并使用"应用专用密码"'
        },
        'qq': {
            'name': 'QQ邮箱',
            'smtp_server': 'smtp.qq.com',
            'smtp_port': 587,
            'smtp_use_tls': True,
            'smtp_use_ssl': False,
            'note': '密码处需填写授权码，不是QQ密码'
        },
        '163': {
            'name': '163邮箱',
            'smtp_server': 'smtp.163.com',
            'smtp_port': 465,
            'smtp_use_tls': False,
            'smtp_use_ssl': True,
            'note': '密码处需填写授权码，不是登录密码'
        },
        'outlook': {
            'name': 'Outlook/Hotmail',
            'smtp_server': 'smtp.office365.com',
            'smtp_port': 587,
            'smtp_use_tls': True,
            'smtp_use_ssl': False,
            'note': '使用账号密码即可'
        },
        '126': {
            'name': '126邮箱',
            'smtp_server': 'smtp.126.com',
            'smtp_port': 465,
            'smtp_use_tls': False,
            'smtp_use_ssl': True,
            'note': '密码处需填写授权码'
        },
        'sina': {
            'name': '新浪邮箱',
            'smtp_server': 'smtp.sina.com',
            'smtp_port': 465,
            'smtp_use_tls': False,
            'smtp_use_ssl': True,
            'note': '使用账号密码'
        }
    }

    @staticmethod
    def load_smtp_config() -> Optional[Dict]:
        """加载 SMTP 配置"""
        try:
            if os.path.exists(EmailService.SMTP_CONFIG_FILE):
                with open(EmailService.SMTP_CONFIG_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return None

    @staticmethod
    def save_smtp_config(config: Dict) -> bool:
        """保存 SMTP 配置"""
        try:
            os.makedirs(os.path.dirname(EmailService.SMTP_CONFIG_FILE), exist_ok=True)
            with open(EmailService.SMTP_CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"保存 SMTP 配置失败: {e}")
            return False

    @staticmethod
    def get_smtp_config() -> Dict:
        """获取 SMTP 配置（优先使用用户配置，否则使用环境变量）"""
        user_config = EmailService.load_smtp_config()

        if user_config and user_config.get('smtp_username'):
            return user_config

        # 回退到环境变量配置
        if Config.SMTP_USERNAME and Config.SMTP_PASSWORD:
            return {
                'smtp_server': Config.SMTP_SERVER,
                'smtp_port': Config.SMTP_PORT,
                'smtp_username': Config.SMTP_USERNAME,
                'smtp_password': Config.SMTP_PASSWORD,
                'smtp_from': Config.SMTP_FROM or Config.SMTP_USERNAME,
                'smtp_use_tls': Config.SMTP_USE_TLS,
                'smtp_use_ssl': False
            }

        return {}

    @staticmethod
    def send_email(to_emails: List[str], subject: str, body: str, html: bool = False) -> Dict:
        """
        发送邮件

        参数:
            to_emails: 收件人邮箱列表
            subject: 邮件主题
            body: 邮件正文
            html: 是否为 HTML 格式

        返回格式: {
            'success': bool,
            'message': str,
            'error': str
        }
        """
        smtp_config = EmailService.get_smtp_config()

        if not smtp_config.get('smtp_username') or not smtp_config.get('smtp_password'):
            return {
                'success': False,
                'message': '',
                'error': '邮件配置未完成，请先配置 SMTP 设置'
            }

        # 验证和清理收件人邮箱列表
        if not to_emails or not isinstance(to_emails, list):
            return {
                'success': False,
                'message': '',
                'error': '收件人邮箱列表格式错误'
            }

        # 过滤空字符串并清理邮箱地址
        to_emails = [email.strip() for email in to_emails if email and email.strip()]

        if not to_emails:
            return {
                'success': False,
                'message': '',
                'error': '收件人邮箱列表为空'
            }

        try:
            # 创建邮件对象
            msg = MIMEMultipart('alternative')
            msg['From'] = smtp_config.get('smtp_from', smtp_config['smtp_username'])
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject

            # 添加邮件正文
            if html:
                part = MIMEText(body, 'html', 'utf-8')
            else:
                part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(part)

            # 连接 SMTP 服务器并发送
            smtp_server = smtp_config.get('smtp_server', 'smtp.gmail.com')
            smtp_port = smtp_config.get('smtp_port', 587)
            use_tls = smtp_config.get('smtp_use_tls', True)
            use_ssl = smtp_config.get('smtp_use_ssl', False)

            print(f"[邮件调试] 尝试发送邮件:")
            print(f"  服务器: {smtp_server}:{smtp_port}")
            print(f"  加密: {'SSL' if use_ssl or smtp_port == 465 else 'TLS' if use_tls else '无'}")
            print(f"  发件人: {smtp_config['smtp_username']}")
            print(f"  收件人: {to_emails}")

            # 根据配置选择连接方式
            if use_ssl or smtp_port == 465:
                # 使用 SSL 连接（端口 465）
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30, context=context) as server:
                    print(f"[邮件调试] SSL 连接成功")
                    server.login(smtp_config['smtp_username'], smtp_config['smtp_password'])
                    print(f"[邮件调试] 登录成功")
                    server.send_message(msg)
                    print(f"[邮件调试] 邮件发送成功")
            else:
                # 使用 STARTTLS（端口 587）
                with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                    print(f"[邮件调试] SMTP 连接成功")
                    server.ehlo()  # 标识客户端
                    print(f"[邮件调试] EHLO 完成")
                    if use_tls:
                        server.starttls()
                        print(f"[邮件调试] STARTTLS 完成")
                        server.ehlo()  # TLS 后重新标识
                    server.login(smtp_config['smtp_username'], smtp_config['smtp_password'])
                    print(f"[邮件调试] 登录成功")
                    server.send_message(msg)
                    print(f"[邮件调试] 邮件发送成功")

            return {
                'success': True,
                'message': f'邮件发送成功，收件人: {", ".join(to_emails)}',
                'error': ''
            }

        except smtplib.SMTPAuthenticationError as e:
            error_msg = '认证失败：用户名或密码错误'
            if 'qq.com' in smtp_config.get('smtp_server', ''):
                error_msg += '（QQ邮箱需要使用授权码，不是QQ密码）'
            elif '163.com' in smtp_config.get('smtp_server', '') or '126.com' in smtp_config.get('smtp_server', ''):
                error_msg += '（网易邮箱需要使用授权码）'
            print(f"[邮件错误] 认证失败: {str(e)}")
            return {
                'success': False,
                'message': '',
                'error': error_msg
            }
        except smtplib.SMTPConnectError as e:
            print(f"[邮件错误] 连接失败: {str(e)}")
            return {
                'success': False,
                'message': '',
                'error': f'连接失败：无法连接到SMTP服务器 {smtp_server}:{smtp_port}'
            }
        except smtplib.SMTPServerDisconnected as e:
            print(f"[邮件错误] 服务器断开: {str(e)}")
            return {
                'success': False,
                'message': '',
                'error': f'连接断开：服务器意外关闭连接，请检查端口配置（587用TLS，465用SSL）'
            }
        except IndexError as e:
            print(f"[邮件错误] 索引错误: {str(e)}")
            return {
                'success': False,
                'message': '',
                'error': f'邮箱地址格式错误，请检查邮箱地址是否正确'
            }
        except Exception as e:
            import traceback
            print(f"[邮件错误] 未知错误: {str(e)}")
            print(traceback.format_exc())
            return {
                'success': False,
                'message': '',
                'error': f'邮件发送失败: {str(e)}'
            }

    @staticmethod
    def send_task_completion_notification(
        to_emails: List[str],
        task_name: str,
        server_name: str,
        status: str,
        details: str = ''
    ) -> Dict:
        """
        发送任务完成通知

        参数:
            to_emails: 收件人邮箱列表
            task_name: 任务名称
            server_name: 服务器名称
            status: 任务状态 (success/failed/timeout)
            details: 任务详情

        返回格式: {
            'success': bool,
            'message': str,
            'error': str
        }
        """
        # 根据状态选择标题和图标
        status_info = {
            'success': {'emoji': '✅', 'text': '成功完成'},
            'failed': {'emoji': '❌', 'text': '执行失败'},
            'timeout': {'emoji': '⏰', 'text': '执行超时'}
        }

        info = status_info.get(status, {'emoji': 'ℹ️', 'text': '状态未知'})

        subject = f"{info['emoji']} [{server_name}] 任务通知: {task_name}"

        # 构建 HTML 邮件正文
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; border-radius: 5px; }}
                .header.failed {{ background: #f44336; }}
                .header.timeout {{ background: #ff9800; }}
                .content {{ padding: 20px; background: #f9f9f9; margin-top: 20px; border-radius: 5px; }}
                .info {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #666; }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #999; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header {status}">
                    <h2>{info['emoji']} GPU 服务器任务通知</h2>
                </div>
                <div class="content">
                    <div class="info">
                        <span class="label">任务名称:</span> {task_name}
                    </div>
                    <div class="info">
                        <span class="label">服务器:</span> {server_name}
                    </div>
                    <div class="info">
                        <span class="label">状态:</span> {info['text']}
                    </div>
                    {f'<div class="info"><span class="label">详情:</span><br><pre>{details}</pre></div>' if details else ''}
                </div>
                <div class="footer">
                    <p>此邮件由 GPU 服务器管理系统自动发送，请勿回复。</p>
                </div>
            </div>
        </body>
        </html>
        """

        return EmailService.send_email(to_emails, subject, html_body, html=True)


# 全局邮件服务实例
email_service = EmailService()
