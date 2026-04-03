// PM2 Process Manager — Protocol Pulse (Ultron)
// Usage: pm2 start ecosystem.config.js
// Status: pm2 list | pm2 monit
// Logs: pm2 logs [name]
// Save: pm2 save && pm2 startup (persist across reboots)
//
// IMPORTANT: avatar_server is intentionally NOT managed here.
// It is DISABLED until new HeyGen avatar is provisioned.

module.exports = {
  apps: [
    {
      name: 'waitress',
      script: 'python3',
      args: '-m waitress --port=5000 --threads=4 --channel-timeout=300 app:app',
      cwd: '/home/ultron/protocol_pulse/core',
      max_memory_restart: '2G',
      autorestart: true,
      watch: false,
      restart_delay: 3000,
      max_restarts: 10,
      min_uptime: '10s',
      log_file: '/home/ultron/protocol_pulse/logs/waitress_pm2.log',
      error_file: '/home/ultron/protocol_pulse/logs/waitress_pm2_err.log',
      env: {
        PYTHONPATH: '/home/ultron/protocol_pulse'
      }
    },
    {
      name: 'relay',
      script: '/home/ultron/.local/bin/gunicorn',
      args: '--workers 4 --bind 0.0.0.0:8201 --timeout 120 --max-requests 500 --max-requests-jitter 50 ultron_relay:app',
      cwd: '/home/ultron/protocol_pulse',
      autorestart: true,
      watch: false,
      restart_delay: 3000,
      max_restarts: 10,
      min_uptime: '10s',
      log_file: '/home/ultron/protocol_pulse/logs/relay_pm2.log',
      error_file: '/home/ultron/protocol_pulse/logs/relay_pm2_err.log'
    },
    {
      name: 'ollama',
      script: 'ollama',
      args: 'serve',
      autorestart: true,
      watch: false,
      restart_delay: 5000,
      max_restarts: 5,
      min_uptime: '10s',
      max_memory_restart: '25G',
      log_file: '/home/ultron/protocol_pulse/logs/ollama_pm2.log',
      error_file: '/home/ultron/protocol_pulse/logs/ollama_pm2_err.log',
      env: {
        OLLAMA_KEEP_ALIVE: '5m',
        OLLAMA_HOST: '0.0.0.0:11434'
      }
    },
    {
      name: 'social-daemon',
      script: 'python3',
      args: 'services/social_daemon.py',
      cwd: '/home/ultron/protocol_pulse',
      autorestart: true,
      watch: false,
      restart_delay: 5000,
      max_restarts: 10,
      min_uptime: '30s',
      log_file: '/home/ultron/protocol_pulse/logs/social_daemon_pm2.log',
      error_file: '/home/ultron/protocol_pulse/logs/social_daemon_pm2_err.log'
    }
  ]
};
