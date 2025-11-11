#!/bin/bash

echo "🔧 OpenAvatarChat coturn自动修复脚本"
echo "=================================="

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用sudo运行此脚本: sudo bash fix_coturn.sh"
    exit 1
fi

echo "🔍 Step 1: 诊断当前coturn状态..."

# 停止coturn服务
echo "⏹️  停止coturn服务..."
systemctl stop coturn

# 查看当前监听端口
echo "📊 检查3478端口占用情况:"
netstat -tulpn | grep 3478 || echo "✅ 3478端口已释放"

echo ""
echo "🔍 Step 2: 查找coturn配置文件..."

# 查找所有可能的配置文件
echo "🔎 搜索coturn配置文件:"
find /etc -name "*turn*" -type f 2>/dev/null

echo ""
echo "🔍 Step 3: 检查systemd服务配置..."

# 查看服务文件
if [ -f "/etc/systemd/system/coturn.service" ]; then
    echo "📄 找到自定义服务文件: /etc/systemd/system/coturn.service"
    cat /etc/systemd/system/coturn.service
elif [ -f "/lib/systemd/system/coturn.service" ]; then
    echo "📄 找到系统服务文件: /lib/systemd/system/coturn.service"
    cat /lib/systemd/system/coturn.service
else
    echo "❓ 未找到coturn服务文件"
fi

echo ""
echo "🔧 Step 4: 创建正确的配置文件..."

# 获取服务器IP信息
PRIVATE_IP=$(ip route get 8.8.8.8 | awk '{print $7; exit}')
PUBLIC_IP=$(curl -s ifconfig.me || curl -s ipinfo.io/ip)

echo "🌐 检测到内网IP: $PRIVATE_IP"
echo "🌐 检测到公网IP: $PUBLIC_IP"

# 创建正确的配置文件
CONFIG_FILE="/etc/turnserver.conf"
echo "📝 创建配置文件: $CONFIG_FILE"

cat > "$CONFIG_FILE" << EOF
listening-port=3478
listening-ip=0.0.0.0
relay-ip=$PRIVATE_IP
external-ip=$PUBLIC_IP
min-port=49152
max-port=65535
verbose
fingerprint
lt-cred-mech
user=username:password
realm=turn.${PUBLIC_IP//./-}.turnserver
EOF

echo "✅ 配置文件已创建"
echo "📋 配置内容:"
cat "$CONFIG_FILE"

echo ""
echo "🔧 Step 5: 强制使用我们的配置启动coturn..."

# 手动启动coturn并指定配置文件
echo "🚀 启动coturn服务..."
systemctl start coturn

# 等待2秒让服务启动
sleep 2

# 检查服务状态
echo "📊 检查服务状态:"
systemctl status coturn --no-pager -l

echo ""
echo "📊 检查端口监听状态:"
netstat -tulpn | grep 3478

echo ""
echo "🔧 Step 6: 验证配置..."

# 检查是否正确监听0.0.0.0
if netstat -tulpn | grep "0.0.0.0:3478" > /dev/null; then
    echo "✅ 成功！coturn正在监听0.0.0.0:3478"
    echo "🎉 修复完成！现在手机应该能连接了"
else
    echo "⚠️  coturn仍未正确监听，尝试手动启动..."
    
    # 手动启动
    echo "🔧 尝试手动启动coturn..."
    systemctl stop coturn
    sleep 1
    
    echo "📝 手动启动命令:"
    echo "turnserver -c /etc/turnserver.conf -v"
    
    # 后台启动coturn
    nohup turnserver -c /etc/turnserver.conf -v > /var/log/coturn-manual.log 2>&1 &
    
    sleep 3
    
    echo "📊 再次检查端口:"
    netstat -tulpn | grep 3478
    
    if netstat -tulpn | grep "0.0.0.0:3478" > /dev/null; then
        echo "✅ 手动启动成功！"
    else
        echo "❌ 手动启动也失败，查看详细日志:"
        tail -20 /var/log/coturn-manual.log
    fi
fi

echo ""
echo "📋 修复完成！请测试手机连接："
echo "URL: https://liao.uunat.com:8282/ui/index.html"
echo ""
echo "🔍 如果仍有问题，查看coturn日志："
echo "sudo journalctl -u coturn -f"

