module.exports = {
  apps: [{
    name: 'signal',
    script: 'uvx',
    args: 'git+https://github.com/realm520/signal.git',
    cwd: '/home/harry/signal',

    // 环境变量
    env: {
      SIGNAL_CONFIG: '/home/harry/signal/config.yaml'
    },

    // 进程管理
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',

    // 日志配置
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,

    // 崩溃重启配置
    min_uptime: '10s',
    max_restarts: 10,
    restart_delay: 5000,

    // 优雅停止
    kill_timeout: 5000
  }]
};
