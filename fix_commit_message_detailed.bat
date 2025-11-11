@echo off
chcp 65001 >nul
echo ====================================
echo   优化提交信息为详细版本
echo ====================================
echo.

git commit --amend -m "feat: 基于OpenAvatarChat扩展 - 集成AI自动化助手和安全配置" -m "" -m "🎯 核心功能" -m "- 新增屏幕共享功能，支持AI实时分析和控制" -m "- 集成Qwen-VL多模态视觉理解模型" -m "- 支持摄像头画面的AI智能分析和对话" -m "" -m "🎨 界面优化" -m "- 基于Ant Design Vue的现代化控制面板" -m "- 优化WebRTC视频流传输界面" -m "- 改进用户交互体验和响应速度" -m "" -m "📚 文档完善" -m "- 云服务器部署完整指南" -m "- 内网穿透配置教程" -m "- 屏幕共享使用说明" -m "- 项目技术架构文档" -m "" -m "🔐 安全配置" -m "- WebRTC TURN服务器配置和验证" -m "- SSL证书管理和自动续期" -m "- 安全的屏幕共享实现方案" -m "" -m "⚙️ 配置增强" -m "- 新增多种配置模板（glut-VL.yaml等）" -m "- 支持百炼CosyVoice TTS API" -m "- 优化LiteAvatar数字人渲染参数" -m "" -m "📦 项目信息" -m "- 原项目: HumanAIGC-Engineering/OpenAvatarChat" -m "- 开源协议: Apache License 2.0" -m "- 致谢: 感谢OpenAvatarChat团队的优秀开源项目"

echo ✓ 提交信息已优化为详细版本
echo.
echo 推送到GitHub...
git push origin main --force
echo.
echo ✅ 完成！访问 https://github.com/845880088/OpenAvatarChat 查看效果
echo.
pause

