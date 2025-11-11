@echo off
chcp 65001 >nul
echo ====================================
echo   修复Git中文乱码问题
echo ====================================
echo.

echo [1/3] 设置Git使用UTF-8编码...
git config --global core.quotepath false
git config --global gui.encoding utf-8
git config --global i18n.commit.encoding utf-8
git config --global i18n.logoutputencoding utf-8
echo ✓ Git编码配置完成

echo.
echo [2/3] 修改最近一次提交信息...
git commit --amend -m "feat: 基于OpenAvatarChat扩展，集成AI自动化助手和安全配置" -m "- 新增屏幕共享功能，支持AI实时分析" -m "- 集成Qwen-VL视觉理解模型" -m "- 优化前端界面和用户体验" -m "- 增强安全配置和部署文档"
echo ✓ 提交信息已修正

echo.
echo [3/3] 推送到GitHub（需要确认）...
echo.
echo ⚠️  注意：这将使用 --force 强制推送，会覆盖远程仓库的提交记录
echo.
set /p confirm="确定要推送吗？(输入 y 确认，其他键取消): "
if /i "%confirm%"=="y" (
    git push origin main --force
    echo ✓ 推送完成！
    echo.
    echo ✅ 修复成功！请访问GitHub查看效果
) else (
    echo ℹ️  已取消推送
    echo.
    echo 💡 如果确认修改无误，可以手动运行：
    echo    git push origin main --force
)

echo.
echo ====================================
echo   完成！
echo ====================================
pause

