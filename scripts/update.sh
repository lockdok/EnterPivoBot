#!/bin/bash
# ==============================================================================
# EnterPivoBot safe update and deployment script
# ==============================================================================
set -e

# Detect script directory (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

DB_FILE="$SCRIPT_DIR/bot_data.db"
BACKUP_DIR="$SCRIPT_DIR/backups"

echo "=== [1/5] Резервное копирование базы данных ==="
if [ -f "$DB_FILE" ]; then
    mkdir -p "$BACKUP_DIR"
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$BACKUP_DIR/bot_data_${TIMESTAMP}.db"
    cp "$DB_FILE" "$BACKUP_FILE"
    echo "✅ Бэкап сохранён: $BACKUP_FILE"

    # Keep only 15 latest backups to conserve disk space
    ls -t "$BACKUP_DIR"/bot_data_*.db 2>/dev/null | tail -n +16 | xargs -r rm --
else
    echo "ℹ️ Файл базы данных bot_data.db пока не существует, бэкап пропущен."
fi

echo "=== [2/5] Получение свежего кода из Git ==="
git fetch origin main
git pull origin main

echo "=== [3/5] Обновление зависимостей ==="
if [ -d ".venv" ]; then
    .venv/bin/pip install -r requirements.txt --quiet
elif command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt --quiet
fi

echo "=== [4/5] Перезапуск службы systemd ==="
if systemctl is-active --quiet enterpivobot; then
    sudo systemctl restart enterpivobot
    echo "✅ Сервис enterpivobot перезапущен."
else
    echo "ℹ️ Сервис enterpivobot не запущен или не установлен. Пропускаем перезапуск."
fi

echo "=== [5/5] Проверка статуса ==="
if systemctl is-active --quiet enterpivobot; then
    sudo systemctl status enterpivobot --no-pager -n 5
    echo "🚀 Бот успешно обновлен и работает!"
else
    echo "⚠️ Проверьте запуск бота вручную или через systemctl."
fi

