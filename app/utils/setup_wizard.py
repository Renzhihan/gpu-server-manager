"""
首次启动配置向导
帮助用户完成初始化配置
"""
import os
import secrets
import getpass
from pathlib import Path


class SetupWizard:
    """首次启动配置向导"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.env_file = self.project_root / '.env'
        self.config_marker = self.project_root / '.configured'

    def is_configured(self) -> bool:
        """检查是否已完成初始配置"""
        return self.config_marker.exists()

    def mark_configured(self):
        """标记已完成配置"""
        self.config_marker.touch()

    def run(self):
        """运行配置向导"""
        print("\n" + "="*80)
        print("🚀 欢迎使用 GPU Server Manager！")
        print("="*80)
        print("\n检测到这是首次启动，请完成以下配置：\n")

        # 检查.env文件
        if not self.env_file.exists():
            print("📝 步骤 1/4: 创建配置文件")
            self._create_env_file()
        else:
            print("✅ 配置文件已存在: .env")

        # 配置管理员密码
        print("\n🔐 步骤 2/4: 设置管理员密码")
        self._setup_admin_password()

        # 配置SECRET_KEY
        print("\n🔑 步骤 3/4: 生成安全密钥")
        self._setup_secret_key()

        # 配置服务器
        print("\n🖥️  步骤 4/4: 配置服务器")
        self._setup_servers()

        # 完成
        self.mark_configured()
        print("\n" + "="*80)
        print("✅ 配置完成！")
        print("="*80)
        print("\n启动命令:")
        print("  - HTTP模式: python run.py --host 127.0.0.1")
        print("  - HTTPS模式: python run.py --https --host 127.0.0.1")
        print("\n访问地址: http://localhost:5000")
        print("管理员登录: 使用刚才设置的密码")
        print("\n更多信息请查看: README.md 和 SECURITY.md\n")

    def _create_env_file(self):
        """创建.env文件"""
        example_file = self.project_root / '.env.example'
        if example_file.exists():
            import shutil
            shutil.copy(example_file, self.env_file)
            print(f"✅ 已从 .env.example 创建 .env 文件")
        else:
            print("⚠️  .env.example 不存在，请手动创建 .env 文件")

    def _setup_admin_password(self):
        """配置管理员密码"""
        print("\n强密码要求：")
        print("  - 至少16个字符")
        print("  - 包含大小写字母、数字和特殊字符\n")

        while True:
            password = getpass.getpass("请输入管理员密码: ")
            if len(password) < 16:
                print("❌ 密码太短，至少需要16个字符")
                continue

            confirm = getpass.getpass("请再次输入密码确认: ")
            if password != confirm:
                print("❌ 两次密码不一致，请重新输入")
                continue

            # 更新.env文件
            self._update_env('ADMIN_PASSWORD', password)
            print("✅ 管理员密码已设置")
            break

    def _setup_secret_key(self):
        """生成SECRET_KEY"""
        secret_key = secrets.token_hex(32)
        self._update_env('SECRET_KEY', secret_key)
        print(f"✅ 已自动生成 SECRET_KEY: {secret_key[:16]}...（共64位）")

    def _setup_servers(self):
        """配置服务器"""
        servers_file = self.project_root / 'config' / 'servers.yaml'
        example_file = self.project_root / 'config' / 'servers.yaml.example'

        if servers_file.exists():
            print("✅ 服务器配置文件已存在: config/servers.yaml")
        elif example_file.exists():
            import shutil
            shutil.copy(example_file, servers_file)
            print("✅ 已从示例文件创建 config/servers.yaml")
            print("   请编辑此文件，填入您的服务器信息")
        else:
            print("⚠️  请手动创建 config/servers.yaml 文件")

    def _update_env(self, key: str, value: str):
        """更新.env文件中的配置项"""
        if not self.env_file.exists():
            return

        lines = []
        updated = False

        with open(self.env_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith(f'{key}='):
                    lines.append(f'{key}={value}\n')
                    updated = True
                else:
                    lines.append(line)

        # 如果没有找到该配置项，追加到末尾
        if not updated:
            lines.append(f'{key}={value}\n')

        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)


def check_and_run_setup():
    """检查并运行首次启动向导"""
    wizard = SetupWizard()

    if not wizard.is_configured():
        try:
            wizard.run()
            return True
        except KeyboardInterrupt:
            print("\n\n⚠️  配置被中断，您可以稍后手动配置")
            print("   或删除 .configured 文件重新运行向导\n")
            return False
        except Exception as e:
            print(f"\n❌ 配置向导运行失败: {e}")
            print("   请手动配置 .env 和 config/servers.yaml 文件\n")
            return False

    return True
