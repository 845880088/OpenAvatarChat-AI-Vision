#!/bin/bash

echo "🔍 OpenAvatarChat TURN服务器全面验证脚本"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 验证结果统计
PASS_COUNT=0
FAIL_COUNT=0

# 验证函数
check_pass() {
    echo -e "✅ ${GREEN}[PASS]${NC} $1"
    ((PASS_COUNT++))
}

check_fail() {
    echo -e "❌ ${RED}[FAIL]${NC} $1"
    ((FAIL_COUNT++))
}

check_warn() {
    echo -e "⚠️ ${YELLOW}[WARN]${NC} $1"
}

check_info() {
    echo -e "ℹ️ ${BLUE}[INFO]${NC} $1"
}

echo "🔍 第1步：系统环境检查"
echo "========================"

# 获取IP信息
PRIVATE_IP=$(ip route get 8.8.8.8 | awk '{print $7; exit}')
PUBLIC_IP=$(curl -s --connect-timeout 5 ifconfig.me || curl -s --connect-timeout 5 ipinfo.io/ip || echo "无法获取")

check_info "内网IP: $PRIVATE_IP"
check_info "公网IP: $PUBLIC_IP"

if [[ "$PUBLIC_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    check_pass "公网IP获取成功: $PUBLIC_IP"
else
    check_fail "无法获取公网IP"
fi

echo ""
echo "🔍 第2步：coturn进程检查"
echo "========================"

# 检查coturn进程
COTURN_PROCESS=$(ps aux | grep turnserver | grep -v grep)
if [ -n "$COTURN_PROCESS" ]; then
    check_pass "coturn进程正在运行"
    check_info "进程信息: $COTURN_PROCESS"
    
    # 提取使用的配置文件
    CONFIG_FILE=$(echo "$COTURN_PROCESS" | grep -o '\-c [^ ]*' | awk '{print $2}')
    if [ -n "$CONFIG_FILE" ]; then
        check_pass "使用配置文件: $CONFIG_FILE"
    else
        check_warn "未找到配置文件参数"
    fi
else
    check_fail "coturn进程未运行"
fi

echo ""
echo "🔍 第3步：端口监听检查"
echo "======================"

# 检查3478端口监听
PORT_LISTEN=$(netstat -tulpn | grep :3478)
if [ -n "$PORT_LISTEN" ]; then
    check_pass "3478端口正在监听"
    echo "$PORT_LISTEN" | while read line; do
        check_info "监听详情: $line"
    done
    
    # 检查是否监听0.0.0.0
    if echo "$PORT_LISTEN" | grep "0.0.0.0:3478" > /dev/null; then
        check_pass "正确监听所有接口 (0.0.0.0:3478)"
    else
        check_fail "未监听所有接口，可能只监听内网IP"
    fi
else
    check_fail "3478端口未监听"
fi

echo ""
echo "🔍 第4步：配置文件验证"
echo "======================"

# 检查配置文件
ACTIVE_CONFIG="/etc/turnserver.conf"
if [ -f "$ACTIVE_CONFIG" ]; then
    check_pass "配置文件存在: $ACTIVE_CONFIG"
    
    # 检查关键配置项
    if grep -q "listening-ip=0.0.0.0" "$ACTIVE_CONFIG"; then
        check_pass "listening-ip 配置正确"
    else
        check_fail "listening-ip 未设置为 0.0.0.0"
    fi
    
    if grep -q "external-ip=$PUBLIC_IP" "$ACTIVE_CONFIG"; then
        check_pass "external-ip 配置正确: $PUBLIC_IP"
    else
        check_warn "external-ip 可能不匹配当前公网IP"
    fi
    
    if grep -q "relay-ip=$PRIVATE_IP" "$ACTIVE_CONFIG"; then
        check_pass "relay-ip 配置正确: $PRIVATE_IP"
    else
        check_warn "relay-ip 可能不匹配当前内网IP"
    fi
    
    if grep -q "user=username:password" "$ACTIVE_CONFIG"; then
        check_pass "TURN用户认证配置存在"
    else
        check_fail "TURN用户认证配置缺失"
    fi
    
    echo ""
    check_info "当前配置文件内容:"
    echo "-----------------------------------"
    cat "$ACTIVE_CONFIG" | sed 's/^/    /'
    echo "-----------------------------------"
    
else
    check_fail "配置文件不存在: $ACTIVE_CONFIG"
fi

echo ""
echo "🔍 第5步：网络连接性测试"
echo "========================"

# 测试本地端口连接
if timeout 3 bash -c "</dev/tcp/127.0.0.1/3478" 2>/dev/null; then
    check_pass "本地TCP 3478端口连接成功"
else
    check_fail "本地TCP 3478端口连接失败"
fi

# 测试公网端口连接（从内部）
if timeout 3 bash -c "</dev/tcp/$PUBLIC_IP/3478" 2>/dev/null; then
    check_pass "公网IP TCP 3478端口连接成功"
else
    check_fail "公网IP TCP 3478端口连接失败"
fi

echo ""
echo "🔍 第6步：防火墙状态检查"
echo "========================"

# 检查系统防火墙
if command -v firewall-cmd &> /dev/null; then
    if firewall-cmd --state 2>/dev/null | grep -q "running"; then
        check_info "系统防火墙正在运行"
        
        OPEN_PORTS=$(firewall-cmd --list-ports 2>/dev/null || echo "无法查询")
        check_info "开放端口: $OPEN_PORTS"
        
        if echo "$OPEN_PORTS" | grep -q "3478"; then
            check_pass "防火墙已开放3478端口"
        else
            check_warn "防火墙可能未开放3478端口"
        fi
    else
        check_info "系统防火墙未运行"
    fi
else
    check_info "未安装firewall-cmd，跳过系统防火墙检查"
fi

echo ""
echo "🔍 第7步：WebRTC配置匹配性检查"
echo "=============================="

# 检查本地项目配置文件应该指向的TURN服务器
EXPECTED_TURN_URL="turn:$PUBLIC_IP:3478"
check_info "期望的本地项目TURN配置: $EXPECTED_TURN_URL"
check_info "期望的用户名/密码: username/password"

echo ""
echo "🔍 第8步：coturn日志检查"
echo "======================"

# 检查coturn最近日志
if command -v journalctl &> /dev/null; then
    check_info "coturn最近日志 (最近10行):"
    echo "-----------------------------------"
    journalctl -u coturn --no-pager -n 10 2>/dev/null | sed 's/^/    /' || echo "    无法获取systemd日志"
    echo "-----------------------------------"
fi

# 检查手动启动的日志文件
if [ -f "/var/log/coturn-manual.log" ]; then
    check_info "手动启动日志 (最后10行):"
    echo "-----------------------------------"
    tail -10 /var/log/coturn-manual.log | sed 's/^/    /'
    echo "-----------------------------------"
fi

echo ""
echo "📊 验证结果汇总"
echo "================"
echo -e "✅ ${GREEN}通过项目: $PASS_COUNT${NC}"
echo -e "❌ ${RED}失败项目: $FAIL_COUNT${NC}"

if [ $FAIL_COUNT -eq 0 ]; then
    echo ""
    echo -e "🎉 ${GREEN}所有检查通过！TURN服务器配置完美！${NC}"
    echo ""
    echo "📱 现在可以进行手机测试："
    echo "   URL: https://liao.uunat.com:8282/ui/index.html"
    echo ""
    echo "🔗 本地项目应使用的配置："
    echo "   urls: [\"stun:stun.l.google.com:19302\", \"turn:$PUBLIC_IP:3478\"]"
    echo "   username: \"username\""
    echo "   credential: \"password\""
    
elif [ $FAIL_COUNT -le 2 ]; then
    echo ""
    echo -e "⚠️ ${YELLOW}大部分检查通过，有少量问题需要修复${NC}"
    echo "请查看上面的失败项目并进行修复"
    
else
    echo ""
    echo -e "❌ ${RED}存在多个严重问题，需要重新配置${NC}"
    echo "建议运行修复脚本: sudo bash fix_coturn.sh"
fi

echo ""
echo "🔧 如需修复，可运行："
echo "   sudo bash fix_coturn.sh"
echo ""
echo "🔍 验证完成！"
